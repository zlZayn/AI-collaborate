import threading

_buffer = []
_lock = threading.Lock()


def phase(tag, msg):
    with _lock:
        _buffer.append(f"  [{tag}] {msg}")


def task_done(name):
    with _lock:
        _buffer.append(f"  {name}  done")


def task_error(name, err):
    with _lock:
        _buffer.append(f"  {name}  ERROR: {err}")


def flush():
    with _lock:
        lines = _buffer[:]
        _buffer.clear()
        return lines
