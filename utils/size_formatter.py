def format_size(size_bytes):
    for unit in ['octets', 'Ko', 'Mo', 'Go', 'To']:
        if size_bytes < 1024:
            return f"{round(size_bytes, 2)} {unit}"
        size_bytes /= 1024
    return f"{round(size_bytes, 2)} Po"
