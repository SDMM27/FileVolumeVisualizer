import os
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
