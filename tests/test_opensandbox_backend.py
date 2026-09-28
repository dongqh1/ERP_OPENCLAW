from datetime import timedelta
from types import SimpleNamespace

from agent.backends.custom_opensandbox import OpenSandboxBackend


class FakeSandboxFiles:
    def __init__(self, content=b"file bytes"):
        self.content = content
        self.read_paths = []

    def read_bytes(self, path):
        self.read_paths.append(path)
        return self.content


class FakeSandboxCommands:
    def __init__(self):
        self.calls = []

    def run(self, command, *, opts):
        self.calls.append((command, opts))
        return SimpleNamespace(
            exit_code=0,
            logs=SimpleNamespace(stdout=[SimpleNamespace(text="ok")], stderr=[]),
        )


def test_execute_passes_configured_timeout_to_opensandbox():
    commands = FakeSandboxCommands()
    backend = OpenSandboxBackend(
        sandbox=SimpleNamespace(id="sandbox-test", commands=commands)
    )

    result = backend.execute("echo ok", timeout=17)

    command, opts = commands.calls[0]
    assert command.startswith(f'export PATH="{backend.SANDBOX_PATH}:$PATH" && echo ok')
    assert opts.timeout == timedelta(seconds=17)
    assert result.output == "ok"
    assert result.exit_code == 0


def test_download_files_reads_binary_content_and_rejects_relative_paths():
    files = FakeSandboxFiles(b"\x00\xffbinary")
    backend = OpenSandboxBackend(
        sandbox=SimpleNamespace(id="sandbox-test", files=files)
    )

    results = backend.download_files(["/data/report.bin", "relative.txt"])

    assert files.read_paths == ["/data/report.bin"]
    assert results[0].content == b"\x00\xffbinary"
    assert results[0].error is None
    assert results[1].content is None
    assert results[1].error == "invalid_path"
