import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from concurrent.futures import ThreadPoolExecutor
import threading

executor = ThreadPoolExecutor(max_workers=4)
lock = threading.Lock()

def get_size(path):
    """Calcule la taille totale d’un fichier ou dossier (récursif)."""
    total_size = 0
    try:
        if os.path.isfile(path):
            total_size += os.path.getsize(path)
        else:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except Exception:
                        continue
    except Exception:
        pass
    return total_size

def scan_directory(path, progress_callback=None):
    """Scan synchrone lancé dans un thread séparé."""
    results = []
    try:
        entries = os.scandir(path)
        total = len([e for e in entries if not e.name.startswith('.')])
        scanned = 0

        # Resscanner car le premier a été consommé
        entries = os.scandir(path)

        for entry in entries:
            if entry.name.startswith('.'):
                continue
            try:
                entry_path = os.path.join(path, entry.name)
                size = get_size(entry_path)
                results.append({
                    'name': entry.name,
                    'path': entry_path,
                    'size': size
                })
            except Exception:
                continue

            scanned += 1
            progress = int((scanned / total) * 100) if total > 0 else 100
            if progress_callback:
                with lock:
                    progress_callback(progress)

    except Exception as e:
        print(f"[scan_directory] Error: {e}")
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
                    size = entry.stat().st_size if entry.is_file() else 0
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

        except Exception as e:
            print(f"[scan error] {current_path} => {e}")

        self.result[current_path] = children
        self.progress.emit(min(100, self.total_scanned // 10))
