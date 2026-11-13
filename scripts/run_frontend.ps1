# Uses installed project dependencies; works even when npm is not on PATH.
$ErrorActionPreference = 'Stop'
$frontendRoot = Join-Path $PSScriptRoot '..\frontend'
Push-Location $frontendRoot
try {
    & node '.\node_modules\vite\bin\vite.js' --host localhost --port 5173
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
