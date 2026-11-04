import httpx
import threading
from .config import AuditConfig


class AuditClient:
    def __init__(self, config: AuditConfig):
        self.config = config
        self._http = httpx.Client(timeout=config.timeout)

    def log(self, **kwargs):
        if not self.config.enabled:
            return
        # Fire-and-forget — never blocks the calling application
        t = threading.Thread(target=self._send, kwargs=kwargs, daemon=True)
        t.start()

    def _send(self, **kwargs):
        try:
            self._http.post(
                f"{self.config.server_url}/api/v1/log",
                json=kwargs,
                timeout=self.config.timeout,
            )
        except Exception:
            pass  # Silently drop — logging must never crash the app

    def close(self):
        self._http.close()
