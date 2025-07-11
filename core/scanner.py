import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from concurrent.futures import ThreadPoolExecutor
import threading
import getpass

executor = ThreadPoolExecutor(max_workers=4)
lock = threading.Lock()

IGNORED_FOLDERS = {
    "C:\\Windows",
    "C:\\Users\\Default",
    "C:\\Users\\All Users",
    "C:\\Users\\Public",
    "C:\\$Recycle.Bin",
    "C:\\System Volume Information",
    "C:\\Recovery",
    "C:\\PerfLogs",
    "C:\\Users\\%USERNAME%\\AppData",  # à adapter dynamiquement
}

def get_size(path):
    """Calcule la taille totale d’un fichier ou dossier (récursif)."""
    total_size = 0
    try:
        if os.path.isfile(path):
            total_size += os.path.getsize(path)
        else:  # <-- Ajout du log
            for dirpath, dirnames, filenames in os.walk(path, onerror=lambda e: None):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except PermissionError:
                        continue
                    except Exception:
                        continue
    except PermissionError:
        pass
    except Exception:
        pass
    return total_size

def get_ignored_folders():
    username = getpass.getuser()
    ignored = set(IGNORED_FOLDERS)
    ignored.add(f"C:\\Users\\{username}\\AppData")
    return ignored

def scan_directory(path, progress_callback=None):
    ignored_folders = get_ignored_folders()
    results = []
    try:
        if os.path.abspath(path) in ignored_folders:
            return []
        entries = os.scandir(path)
        for entry in entries:
            entry_path = os.path.join(path, entry.name)
            # Ignore les dossiers de la liste noire
            if entry.is_dir(follow_symlinks=False) and os.path.abspath(entry_path) in ignored_folders:
                continue
            if entry.name.startswith('.'):
                continue
            try:
                size = get_size(entry_path)
                results.append({
                    'name': entry.name,
                    'path': entry_path,
                    'size': size,
                    'is_dir': entry.is_dir(follow_symlinks=False)
                })

            except PermissionError:
                continue
            except Exception as e:
                continue
    except PermissionError:
        pass
    except Exception as e:
        return []
    return results

class DirectoryScanner(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)  # ✅ résultat structuré

    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.queue = [base_path]
        self.result = {}  # ✅ dict: dossier -> liste enfants
        self.total_scanned = 0

    def start(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_next)
        self.timer.start(10)

    def process_next(self):
        if not self.queue:
            self.timer.stop()
            self.finished.emit(self.result)
            return

        current_path = self.queue.pop(0)
        children = []

        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    path = entry.path
                    if entry.is_file():
                        size = entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        size = get_size(path)  # Calcule la taille totale du dossier ici !
                    else:
                        size = 0
                    item = {
                        'name': entry.name,
                        'path': path,
                        'size': size,
                        'is_dir': entry.is_dir(follow_symlinks=False)
                    }
                    children.append(item)

                    if item['is_dir']:
                        self.queue.append(path)

                    self.total_scanned += 1

        except PermissionError:
            print(f"Permission denied: {current_path}")  # Log pour les permissions
        except Exception as e:
            print(f"Error on {current_path}: {e}")

        self.result[current_path] = children
        progress = min(100, self.total_scanned // 10)
        self.progress.emit(progress)

        # Si on atteint 100% mais la queue n'est pas vide, forcer l'affichage
        if progress >= 100 and self.queue:
            self.timer.stop()
            self.finished.emit(self.result)
