import sys
import time
import threading
from typing import Optional

THINKING_FRAMES = [
    "NASMI is thinking      ",
    "NASMI is thinking .    ",
    "NASMI is thinking ..   ",
    "NASMI is thinking ...  ",
    "NASMI is thinking .... ",
    "NASMI is thinking .....",
]


class ThinkingLoader:

    def __init__(self, message: str = "NASMI is thinking", interval: float = 0.35):
        self._message  = message
        self._interval = interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _spin(self) -> None:
        frames = [
            f"\r  {self._message}      ",
            f"\r  {self._message} .    ",
            f"\r  {self._message} ..   ",
            f"\r  {self._message} ...  ",
            f"\r  {self._message} .... ",
            f"\r  {self._message} .....",
        ]
        i = 0
        while not self._stop_event.is_set():
            sys.stdout.write(frames[i % len(frames)])
            sys.stdout.flush()
            time.sleep(self._interval)
            i += 1
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
