import importlib.util
from pathlib import Path

import dotenv


def test_web_config_loads_project_dotenv_before_reading_mongodb_uri(monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "src" / "api_view" / "web_config.py"
    calls = []

    def fake_load_dotenv(dotenv_path, *, override):
        calls.append((Path(dotenv_path), override))
        monkeypatch.setenv("MONGODB_URI", "mongodb://configured-from-env-file")
        return True

    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", fake_load_dotenv)
    spec = importlib.util.spec_from_file_location("web_config_under_test", config_path)
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert module.MONGODB_URI == "mongodb://configured-from-env-file"
    assert calls == [(project_root / ".env", True)]
