#!/usr/bin/env pwsh
param(
    [string]$Command = "help"
)

$Project = "localfs"

function Write-Info  { Write-Host "[INFO]  $($args[0])" -ForegroundColor Blue }
function Write-Ok    { Write-Host "[OK]    $($args[0])" -ForegroundColor Green }
function Write-Err   { Write-Host "[ERR]   $($args[0])" -ForegroundColor Red; exit 1 }

function Invoke-Cmd {
    Write-Info $args
    & $args
    if ($LASTEXITCODE -ne 0) { Write-Err "Command failed: $args" }
}

function Build {
    Invoke-Cmd python -m build --wheel --sdist .
    Write-Ok "Build complete — see dist/"
}

function Install {
    Invoke-Cmd pip install --user -e .
    Write-Ok "Installed in editable mode"
}

function Test-All {
    Invoke-Cmd python -m pytest tests/ -v --tb=short
}

function Lint {
    Invoke-Cmd python -m ruff check .
}

function Format {
    Invoke-Cmd python -m ruff format .
}

function Clean {
    Remove-Item -Recurse -Force build, dist, *.egg-info, __pycache__, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory -Name __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue
    Write-Ok "Cleaned build artifacts"
}

function Run {
    Invoke-Cmd python main.py $args
}

function Docker-Build {
    Invoke-Cmd docker build -t $Project .
}

switch ($Command) {
    "build"       { Build }
    "install"     { Install }
    "test"        { Test-All }
    "lint"        { Lint }
    "format"      { Format }
    "clean"       { Clean }
    "run"         { Run }
    "docker"      { Docker-Build }
    default {
        @"
Usage: $($MyInvocation.MyCommand.Path) <command>

Commands:
  build       Build wheel and sdist
  install     Install package in editable mode
  test        Run test suite
  lint        Run ruff linter
  format      Run ruff formatter
  clean       Remove build artifacts
  run         Start localfs server
  docker      Build Docker image
  help        Show this help
"@
    }
}
