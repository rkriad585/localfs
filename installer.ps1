#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Installer / Uninstaller for localfs
.DESCRIPTION
    Install:  irm https://raw.githubusercontent.com/rkriad585/localfs/main/installer.ps1 | iex
    Uninstall: Invoke-RestMethod -Uri "https://raw.githubusercontent.com/rkriad585/localfs/main/installer.ps1" | Invoke-Expression -ArgumentList "--selfuninstall"
#>

#Requires -Version 5.1

# ─── Config ────────────────────────────────────────────────────────────────
$Script:ProjectName = "localfs"
$Script:GitHubUser   = "rkriad585"
$Script:InstallDir   = Join-Path $HOME ".$($Script:ProjectName)"
$Script:ConfigDir    = Join-Path $HOME "AppData" "Local" $Script:ProjectName
$Script:BinDir       = Join-Path $HOME ".local" "bin"
$Script:RepoUrl      = "https://github.com/$($Script:GitHubUser)/$($Script:ProjectName).git"
$Script:VersionUrl   = "https://raw.githubusercontent.com/$($Script:GitHubUser)/$($Script:ProjectName)/main/.version"

# ─── Helpers ───────────────────────────────────────────────────────────────
function Write-Info  { Write-Host "[INFO]  $($args[0])" -ForegroundColor Blue }
function Write-Ok    { Write-Host "[OK]    $($args[0])" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $($args[0])" -ForegroundColor Yellow }
function Write-Err   { Write-Host "[ERR]   $($args[0])" -ForegroundColor Red }

function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop >$null; return $true }
    catch { return $false }
}

function Add-PathToUserEnv {
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($current -split ";" -contains $Script:BinDir) {
        return
    }
    $newPath = if ($current) { "$current;$($Script:BinDir)" } else { $Script:BinDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Ok "Added $($Script:BinDir) to User PATH"
}

function Remove-PathFromUserEnv {
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $current) { return }
    $parts = $current -split ";" | Where-Object { $_ -ne $Script:BinDir -and $_ -ne "" }
    $newPath = $parts -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Ok "Removed $($Script:BinDir) from User PATH"
}

function Get-BinDir {
    $pythonUserBase = python -m site --user-base 2>$null
    if ($pythonUserBase) {
        $scripts = Join-Path $pythonUserBase "Scripts"
        if (Test-Path $scripts) { return $scripts }
    }
    $localAppData = Join-Path $env:LOCALAPPDATA "Programs" "Python"
    if (Test-Path $localAppData) {
        $pythons = Get-ChildItem $localAppData -Directory | Sort-Object Name -Descending
        if ($pythons) {
            $scripts = Join-Path $pythons[0].FullName "Scripts"
            if (Test-Path $scripts) { return $scripts }
        }
    }
    return $Script:BinDir
}

function Detect-Pip {
    if (Test-Command "pip3") { return "pip3" }
    if (Test-Command "pip")  { return "pip" }
    Write-Err "pip not found. Install Python 3 and try again."
    exit 1
}

# ─── Install ───────────────────────────────────────────────────────────────
function Install-Project {
    Write-Host ""
    Write-Host "==> Installing $($Script:ProjectName)..." -ForegroundColor White
    Write-Host ""

    # 1. Prerequisites
    if (-not (Test-Command "git") -and -not (Test-Command "curl") -and -not (Test-Command "wget")) {
        Write-Err "Need git, curl, or wget to download $($Script:ProjectName)."
        exit 1
    }

    # 2. Download / clone
    if (Test-Path $Script:InstallDir) {
        $gitDir = Join-Path $Script:InstallDir ".git"
        if (Test-Command "git" -and (Test-Path $gitDir)) {
            Write-Info "Updating existing installation..."
            Push-Location $Script:InstallDir
            git pull --ff-only
            Pop-Location
        } else {
            Write-Warn "Not a git repo; re-cloning..."
            Remove-Item -Recurse -Force $Script:InstallDir -ErrorAction SilentlyContinue
            git clone $Script:RepoUrl $Script:InstallDir
        }
    } else {
        if (Test-Command "git") {
            Write-Info "Cloning $($Script:RepoUrl) → $($Script:InstallDir)"
            git clone --depth 1 $Script:RepoUrl $Script:InstallDir
        } else {
            Write-Info "Downloading archive..."
            $tarball = "$($Script:RepoUrl)/archive/refs/heads/main.tar.gz"
            $tmpDir = Join-Path $env:TEMP "$([System.IO.Path]::GetRandomFileName())"
            New-Item -ItemType Directory -Path $tmpDir -Force >$null
            $archive = Join-Path $tmpDir "main.tar.gz"
            if (Test-Command "curl") {
                curl -fsSL -o $archive $tarball
            } else {
                wget -q -O $archive $tarball
            }
            tar -xzf $archive -C $tmpDir
            $extracted = Join-Path $tmpDir "$($Script:ProjectName)-main"
            Move-Item $extracted $Script:InstallDir
            Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
        }
    }

    # 3. Install Python package
    $pip = Detect-Pip
    Write-Info "Installing via $pip install -e ."
    & $pip install --user -e $Script:InstallDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "pip install failed"
        exit 1
    }
    Write-Ok "$($Script:ProjectName) installed successfully"

    # 4. Ensure scripts bin dir is on PATH
    $scriptsBin = Get-BinDir
    if (Test-Command $Script:ProjectName) {
        Write-Ok "$($Script:ProjectName) command is already accessible"
    } else {
        Add-PathToUserEnv
        Write-Warn "Restart your terminal or run: `$env:Path = [Environment]::GetEnvironmentVariable('Path','User')"
    }

    # 5. Success banner
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "  $($Script:ProjectName) installed successfully!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Config directory: $($Script:ConfigDir)" -ForegroundColor White
    Write-Host "  Install location: $($Script:InstallDir)" -ForegroundColor White
    Write-Host ""
    Write-Host "  Run the command:" -ForegroundColor Yellow
    Write-Host "    $($Script:ProjectName)" -ForegroundColor White
    Write-Host ""
}

# ─── Uninstall ─────────────────────────────────────────────────────────────
function Uninstall-Project {
    Write-Host ""
    Write-Host "==> Uninstalling $($Script:ProjectName)..." -ForegroundColor White
    Write-Host ""

    # 1. pip uninstall
    $pip = Detect-Pip
    $installed = & $pip list --format=columns 2>$null | Select-String -Pattern "^$($Script:ProjectName)\b" -SimpleMatch
    if ($installed) {
        Write-Info "Removing Python package..."
        & $pip uninstall -y $Script:ProjectName
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Python package removed"
        }
    } else {
        Write-Info "$($Script:ProjectName) Python package not found — skipping"
    }

    # 2. Remove install directory
    if (Test-Path $Script:InstallDir) {
        Remove-Item -Recurse -Force $Script:InstallDir
        Write-Ok "Removed $($Script:InstallDir)"
    } else {
        Write-Info "Install directory not found — skipping"
    }

    # 3. Remove config directory
    if (Test-Path $Script:ConfigDir) {
        Remove-Item -Recurse -Force $Script:ConfigDir
        Write-Ok "Removed config directory $($Script:ConfigDir)"
    } else {
        Write-Info "Config directory not found — skipping"
    }

    # 4. Remove PATH entries
    Remove-PathFromUserEnv

    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "  $($Script:ProjectName) uninstalled." -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Tip: Restart your terminal to refresh PATH." -ForegroundColor Yellow
    Write-Host ""
}

# ─── Main ──────────────────────────────────────────────────────────────────
$ArgsList = @($args)
if ($ArgsList -contains "--selfuninstall") {
    Uninstall-Project
} else {
    Install-Project
}
