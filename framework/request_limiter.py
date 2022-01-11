import threading
import time


class RequestLimiter:
    def __init__(self, request_interval):
        self._lock = threading.RLock()
        self._request_interval = request_interval
        self.requests = 0
        self._next_request_time = time.time()

    def delay_access(self, register=True, count=1):
        with self._lock:
            # 0 means no restrictions
            if self._request_interval == 0:
                return
            request_delay = time.time() > self._next_request_time
            if request_delay:
                time.sleep(request_delay)
            if register:
                self.register_request(count)

    def register_request(self, count=1):
        with self._lock:
            self._next_request_time = max(time.time(), self._next_request_time) + count * self._request_interval
