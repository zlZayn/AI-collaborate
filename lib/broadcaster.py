import queue
import threading


class Broadcaster:
    def __init__(self):
        self._subscribers = []
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def emit(self, event, data):
        with self._lock:
            targets = list(self._subscribers)
        for q in targets:
            try:
                q.put_nowait({"event": event, "data": data})
            except queue.Full:
                pass
