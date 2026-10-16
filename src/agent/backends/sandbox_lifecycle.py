"""Share isolated OpenSandbox backends across graph creations per domain."""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Keep the existing car sandbox ID file for backward compatibility. PC gets a
# separate container and ID file so its execution filesystem cannot inherit car
# procurement files or skills.
_sandbox_id_file = _PROJECT_ROOT / ".opensandbox_id"
_pc_sandbox_id_file = _PROJECT_ROOT / ".opensandbox_pc_id"
_shared_backend: Any = None
_pc_shared_backend: Any = None
_backend_lock = threading.Lock()


def _setup_sandbox(
    config,
    *,
    sandbox_id: str | None,
    image: str | None,
    skill_scopes: set[str] | None = None,
):
    """Import the sandbox factory lazily so lifecycle logic stays easy to test."""
    from agent.backends.sandbox_setup import setup_sandbox

    setup_kwargs = {"sandbox_id": sandbox_id, "image": image}
    if skill_scopes is not None:
        setup_kwargs["skill_scopes"] = skill_scopes
    return setup_sandbox(config, **setup_kwargs)


def _read_sandbox_id(path: Path | None = None) -> str | None:
    path = path or _sandbox_id_file
    try:
        sandbox_id = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RuntimeError(f"无法读取 sandbox ID 文件 {path}: {exc}") from exc
    return sandbox_id or None


def _persist_sandbox_id(sandbox_id: str, path: Path | None = None) -> None:
    path = path or _sandbox_id_file
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix=f"{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(sandbox_id)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def get_shared_sandbox_backend(
    config,
    sandbox_id: str | None = None,
    image: str | None = None,
    *,
    domain: str = "car",
    skill_scopes: set[str] | None = None,
):
    """Return a process-shared sandbox backend for one procurement domain.

    Car retains the original .opensandbox_id. PC uses .opensandbox_pc_id and
    its own process cache. Optional skill scopes limit initial skill seeding.
    """
    global _shared_backend, _pc_shared_backend

    if domain not in {"car", "pc"}:
        raise ValueError(f"不支持的沙箱领域：{domain}")

    with _backend_lock:
        backend = _shared_backend if domain == "car" else _pc_shared_backend
        id_file = _sandbox_id_file if domain == "car" else _pc_sandbox_id_file

        if backend is not None:
            current_id = getattr(backend, "id", None)
            if sandbox_id and current_id and sandbox_id != current_id:
                raise ValueError(
                    f"This process is already using {current_id}; cannot switch to {sandbox_id}"
                )
            return backend

        requested_id = sandbox_id or _read_sandbox_id(id_file)
        setup_kwargs = {
            "sandbox_id": requested_id,
            "image": image,
        }
        if skill_scopes is not None:
            setup_kwargs["skill_scopes"] = skill_scopes
        backend = _setup_sandbox(config, **setup_kwargs)
        if domain == "car":
            _shared_backend = backend
        else:
            _pc_shared_backend = backend

        created_id = getattr(backend, "id", None)
        if created_id:
            try:
                _persist_sandbox_id(created_id, id_file)
            except OSError as exc:
                # Keep the process-level cache even if local persistence fails.
                print(
                    f"[WARNING] 无法保存 {domain} sandbox ID，"
                    f"服务重启后可能重新创建沙箱: {exc}"
                )

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
