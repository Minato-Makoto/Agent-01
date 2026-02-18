from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


class LocalServerManager:
    """Lifecycle manager for local llama-server process."""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None

    @property
    def process(self) -> Optional[subprocess.Popen]:
        return self._process

    def start(
        self,
        *,
        server_exe: str,
        model_path: str,
        host: str,
        port: int,
        n_ctx: int,
        n_gpu_layers: int,
        n_threads: int,
        base_url: str,
        health_path: str,
        health_timeout_s: int,
        health_poll_interval_s: float,
        boot_timeout_s: int,
    ) -> bool:
        if not server_exe or not os.path.exists(server_exe):
            logger.error("[LLM] llama-server.exe not found: %s", server_exe)
            return False
        if not model_path or not os.path.exists(model_path):
            logger.error("[LLM] Model file not found: %s", model_path)
            return False

        cmd = [
            server_exe,
            "-m",
            model_path,
            "-c",
            str(n_ctx),
            "-ngl",
            str(n_gpu_layers),
            "--host",
            host,
            "--port",
            str(port),
        ]
        if n_threads > 0:
            cmd.extend(["-t", str(n_threads)])

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except Exception:
            logger.exception("[LLM] Failed to start server process.")
            return False

        if not self._wait_for_health(
            base_url=base_url,
            health_path=health_path,
            timeout_s=boot_timeout_s,
            health_timeout_s=health_timeout_s,
            poll_interval_s=health_poll_interval_s,
        ):
            logger.error("[LLM] Server failed health check during boot.")
            self.stop()
            return False
        return True

    def _wait_for_health(
        self,
        *,
        base_url: str,
        health_path: str,
        timeout_s: int,
        health_timeout_s: int,
        poll_interval_s: float,
    ) -> bool:
        start = time.time()
        while time.time() - start < timeout_s:
            if self._process and self._process.poll() is not None:
                stderr = ""
                if self._process.stderr is not None:
                    stderr = self._process.stderr.read().decode("utf-8", errors="replace")
                logger.error("[LLM] Server crashed during boot: %s", stderr[:500])
                return False

            try:
                req = urllib.request.Request(f"{base_url}{health_path}")
                with urllib.request.urlopen(req, timeout=health_timeout_s) as resp:
                    data = json.loads(resp.read())
                if str(data.get("status", "")).lower() == "ok":
                    return True
            except (urllib.error.URLError, ConnectionError, OSError, json.JSONDecodeError):
                pass
            time.sleep(poll_interval_s)
        return False

    def stop(self) -> None:
        if not self._process:
            return
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        except (OSError, ValueError):
            pass
        finally:
            self._process = None

