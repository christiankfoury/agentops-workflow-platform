"""Cooperative abort for server-owned executors; callbacks must be quick and idempotent."""

from threading import Event, Lock

from src.services.graph_expressions import ExecutionError


class AbortSignal:
    def __init__(self):
        self.event = Event()
        self.lock = Lock()
        self.callbacks = []

    def on_abort(self, callback):
        with self.lock:
            immediate = self.event.is_set()
            if not immediate:
                self.callbacks.append(callback)
        if immediate:
            self._invoke(callback)

        def unregister():
            with self.lock:
                if callback in self.callbacks:
                    self.callbacks.remove(callback)

        return unregister

    @staticmethod
    def _invoke(callback):
        try:
            callback()
        except Exception:
            # Logical cancellation remains durable even when physical abort is unsupported/fails.
            pass

    def abort(self):
        with self.lock:
            if self.event.is_set():
                return
            self.event.set()
            callbacks, self.callbacks = self.callbacks, []
        for callback in callbacks:
            self._invoke(callback)

    def raise_if_aborted(self):
        if self.event.is_set():
            raise ExecutionError("execution_aborted", "Execution ownership ended or was cancelled")
