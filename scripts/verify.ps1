param(
    [string]$PythonExe
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$env:PYTHON_DOTENV_DISABLED = "1"

if ($PythonExe -and -not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

Write-Host "[1/4] Running Python regression tests..."
$pythonTestArgs = @("-m", "pytest", "-q")
if ($PythonExe) { & $PythonExe @pythonTestArgs }
else { uv run --group dev @pythonTestArgs }
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/4] Compiling Python sources..."
$pythonCompileArgs = @("-m", "compileall", "-q", "src", "tests")
if ($PythonExe) { & $PythonExe @pythonCompileArgs }
else { uv run --group dev python @pythonCompileArgs }
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location (Join-Path $projectRoot "frontend")
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies..."
        npm ci
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "[3/4] Running frontend regression tests..."
    npm test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[4/4] Building frontend..."
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

Write-Host "Verification completed successfully."
