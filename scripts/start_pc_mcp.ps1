$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$srcPath = Join-Path $repoRoot 'src'
$existingPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($existingPythonPath) { "$srcPath;$existingPythonPath" } else { $srcPath }
$venvPython = Join-Path $repoRoot '.venv/Scripts/python.exe'
if (Test-Path $venvPython) {
    & $venvPython -m pc_mcp_server.server_main
}
else {
    python -m pc_mcp_server.server_main
}
