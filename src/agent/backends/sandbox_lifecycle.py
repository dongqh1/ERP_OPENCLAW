"""Share one OpenSandbox backend across graph creations in this project."""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_sandbox_id_file = _PROJECT_ROOT / ".opensandbox_id"
_shared_backend: Any = None
_backend_lock = threading.Lock()


def _setup_sandbox(config, *, sandbox_id: str | None, image: str | None):
    """Import the sandbox factory lazily so lifecycle logic stays easy to test."""
    from agent.backends.sandbox_setup import setup_sandbox

    return setup_sandbox(config, sandbox_id=sandbox_id, image=image)


def _read_sandbox_id() -> str | None:
    try:
        sandbox_id = _sandbox_id_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RuntimeError(f"无法读取 sandbox ID 文件 {_sandbox_id_file}: {exc}") from exc
    return sandbox_id or None


def _persist_sandbox_id(sandbox_id: str) -> None:
    _sandbox_id_file.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix=f"{_sandbox_id_file.name}.",
        suffix=".tmp",
        dir=_sandbox_id_file.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(sandbox_id)
        os.replace(temporary_path, _sandbox_id_file)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def get_shared_sandbox_backend(config, sandbox_id: str | None = None, image: str | None = None):
    """Return the project's shared sandbox backend, creating it only once.

    The sandbox ID is persisted so a process restart or development reload can
    reconnect to the same container. The lock also prevents concurrent graph
    creation from starting multiple containers in one process.
    """
    global _shared_backend

    with _backend_lock:
        if _shared_backend is not None:
            current_id = getattr(_shared_backend, "id", None)
            if sandbox_id and current_id and sandbox_id != current_id:
                raise ValueError(
                    f"This process is already using {current_id}; cannot switch to {sandbox_id}"
                )
            return _shared_backend

        requested_id = sandbox_id or _read_sandbox_id()
        backend = _setup_sandbox(config, sandbox_id=requested_id, image=image)
        _shared_backend = backend

        created_id = getattr(backend, "id", None)
        if created_id:
            try:
                _persist_sandbox_id(created_id)
            except OSError as exc:
                # Keep the process-level cache even if local persistence fails.
                print(f"[WARNING] 无法保存 sandbox ID，服务重启后可能重新创建沙箱: {exc}")

        return backend


def is_missing_sandbox_error(error: Exception) -> bool:
    """Return whether OpenSandbox explicitly reported a removed sandbox."""
    try:
        from opensandbox.exceptions import SandboxApiException
    except ImportError:
        return False

    return isinstance(error, SandboxApiException) and error.status_code in {404, 410}


def connect_or_create_sandbox(sandbox_id, *, connect_existing, create_new):
    """Reuse an existing sandbox and create a replacement only if it is gone."""
    if not sandbox_id:
        return create_new()

    try:
        return connect_existing(sandbox_id)
    except Exception as exc:
        if not is_missing_sandbox_error(exc):
            raise
        return create_new()
