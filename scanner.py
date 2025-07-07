import os

def get_folder_size(path):
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            try:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
            except Exception:
                continue
    return total_size
