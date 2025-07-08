def format_size(size_bytes):
    """Formate une taille en octets en une chaîne lisible (KB, MB, GB…)."""
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {units[i]}"
