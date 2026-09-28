import importlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from opensandbox.exceptions import SandboxApiException, SandboxInternalException


@pytest.fixture
def lifecycle(monkeypatch, tmp_path):
    module = importlib.import_module("agent.backends.sandbox_lifecycle")
    monkeypatch.setattr(module, "_shared_backend", None)
    monkeypatch.setattr(module, "_sandbox_id_file", tmp_path / ".opensandbox_id")
    return module


def test_reuses_backend_and_persists_id(lifecycle, monkeypatch):
    backend = SimpleNamespace(id="sandbox-123")
    calls = []

    def setup(config, *, sandbox_id, image):
        calls.append((config, sandbox_id, image))
        return backend

    monkeypatch.setattr(lifecycle, "_setup_sandbox", setup)

    first = lifecycle.get_shared_sandbox_backend("config")
    second = lifecycle.get_shared_sandbox_backend("config")

    assert first is backend
    assert second is backend
    assert calls == [("config", None, None)]
    assert lifecycle._sandbox_id_file.read_text(encoding="utf-8") == "sandbox-123"


def test_connects_to_persisted_id_after_process_cache_is_cleared(lifecycle, monkeypatch):
    lifecycle._sandbox_id_file.write_text("sandbox-existing\n", encoding="utf-8")
    backend = SimpleNamespace(id="sandbox-existing")
    calls = []

    def setup(config, *, sandbox_id, image):
        calls.append(sandbox_id)
        return backend

    monkeypatch.setattr(lifecycle, "_setup_sandbox", setup)

    result = lifecycle.get_shared_sandbox_backend("config")

    assert result is backend
    assert calls == ["sandbox-existing"]


def test_rejects_a_different_explicit_sandbox_id(lifecycle, monkeypatch):
    backend = SimpleNamespace(id="sandbox-123")
    monkeypatch.setattr(lifecycle, "_setup_sandbox", lambda *args, **kwargs: backend)

    lifecycle.get_shared_sandbox_backend("config")

    with pytest.raises(ValueError, match="already using sandbox-123"):
        lifecycle.get_shared_sandbox_backend("config", sandbox_id="sandbox-other")


def test_concurrent_initialization_creates_only_one_backend(lifecycle, monkeypatch):
    backend = SimpleNamespace(id="sandbox-shared")
    calls = []
    entered = threading.Event()
    release = threading.Event()
    call_lock = threading.Lock()

    def setup(config, *, sandbox_id, image):
        with call_lock:
            calls.append(sandbox_id)
        entered.set()
        assert release.wait(timeout=5)
        return backend

    monkeypatch.setattr(lifecycle, "_setup_sandbox", setup)

    def get_backend():
        return lifecycle.get_shared_sandbox_backend("config")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(get_backend) for _ in range(8)]
        assert entered.wait(timeout=2)
        time.sleep(0.05)
        release.set()
        results = [future.result(timeout=5) for future in futures]

    assert results == [backend] * 8
    assert calls == [None]


def test_failed_initialization_does_not_write_or_cache_id(lifecycle, monkeypatch):
    def setup(config, *, sandbox_id, image):
        raise RuntimeError("sandbox service unavailable")

    monkeypatch.setattr(lifecycle, "_setup_sandbox", setup)

    with pytest.raises(RuntimeError, match="sandbox service unavailable"):
        lifecycle.get_shared_sandbox_backend("config")

    assert lifecycle._shared_backend is None
    assert not lifecycle._sandbox_id_file.exists()


def test_only_missing_or_expired_sandbox_errors_allow_replacement(lifecycle):
    missing = SandboxApiException("sandbox removed", status_code=404)
    expired = SandboxApiException("sandbox expired", status_code=410)
    unavailable = SandboxApiException("service unavailable", status_code=503)
    internal = SandboxInternalException("connection timeout")

    assert lifecycle.is_missing_sandbox_error(missing)
    assert lifecycle.is_missing_sandbox_error(expired)
    assert not lifecycle.is_missing_sandbox_error(unavailable)
    assert not lifecycle.is_missing_sandbox_error(internal)


def test_connects_existing_sandbox_without_creating_another(lifecycle):
    backend = SimpleNamespace(id="sandbox-existing")
    created = []

    result = lifecycle.connect_or_create_sandbox(
        "sandbox-existing",
        connect_existing=lambda sandbox_id: backend,
        create_new=lambda: created.append(True),
    )

    assert result is backend
    assert created == []


def test_recreates_only_when_saved_sandbox_was_removed(lifecycle):
    backend = SimpleNamespace(id="sandbox-new")
    created = []

    def connect_existing(sandbox_id):
        raise SandboxApiException("sandbox removed", status_code=404)

    def create_new():
        created.append(True)
        return backend

    result = lifecycle.connect_or_create_sandbox(
        "sandbox-removed",
        connect_existing=connect_existing,
        create_new=create_new,
    )

    assert result is backend
    assert created == [True]


def test_does_not_create_duplicate_on_transient_connect_error(lifecycle):
    created = []

    def connect_existing(sandbox_id):
        raise SandboxApiException("service unavailable", status_code=503)

    with pytest.raises(SandboxApiException):
        lifecycle.connect_or_create_sandbox(
            "sandbox-existing",
            connect_existing=connect_existing,
            create_new=lambda: created.append(True),
        )

    assert created == []
