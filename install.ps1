#Requires -Version 5.1
<#
.SYNOPSIS
    Install agent-skills by creating symlinks from ~/.claude/ into this repo.
.DESCRIPTION
    Creates directory symlinks for skills, commands, and agents, per-file
    symlinks for hooks, and file symlinks for statusline and keybindings.
    Backs up any existing non-symlink targets before replacing them.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoDir = $PSScriptRoot
$ClaudeDir = Join-Path $env:USERPROFILE '.claude'

if (-not (Test-Path $ClaudeDir -PathType Container)) {
    Write-Error "$ClaudeDir does not exist. Install Claude Code first."
    return
}

$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupDir = Join-Path $ClaudeDir "backups\agent-skills-$Timestamp"
$MadeBackup = $false

function Backup-Target {
    param([string]$Target)

    if (-not (Test-Path $Target)) { return }

    # Already a symlink — remove it, no backup needed
    $item = Get-Item $Target -Force -ErrorAction SilentlyContinue
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        $item.Delete()
        return
    }

    if (-not $script:MadeBackup) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        $script:MadeBackup = $true
    }
    $name = Split-Path $Target -Leaf
    $dest = Join-Path $BackupDir $name
    Write-Host "  Backing up $Target -> $dest"
    Move-Item -Path $Target -Destination $dest -Force
}

function Link-Dir {
    param([string]$Src, [string]$Dest)

    # Check if already correctly linked
    $item = Get-Item $Dest -Force -ErrorAction SilentlyContinue
    if ($item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        $current = $item.Target
        if ($current -eq $Src) {
            Write-Host "  [ok] $Dest -> $Src (already linked)"
            return
        }
    }

    Backup-Target $Dest
    New-Item -ItemType SymbolicLink -Path $Dest -Target $Src -Force | Out-Null
    Write-Host "  [linked] $Dest -> $Src"
}

function Link-File {
    param([string]$Src, [string]$Dest)

    if (-not (Test-Path $Src -PathType Leaf)) {
        Write-Host "  [skip] $Src does not exist"
        return
    }

    $item = Get-Item $Dest -Force -ErrorAction SilentlyContinue
    if ($item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        $current = $item.Target
        if ($current -eq $Src) {
            Write-Host "  [ok] $Dest -> $Src (already linked)"
            return
        }
    }

    Backup-Target $Dest
    New-Item -ItemType SymbolicLink -Path $Dest -Target $Src -Force | Out-Null
    Write-Host "  [linked] $Dest -> $Src"
}

Write-Host "Installing agent-skills from $RepoDir"
Write-Host ""

# Symlink directories
Link-Dir (Join-Path $RepoDir 'skills')   (Join-Path $ClaudeDir 'skills')
Link-Dir (Join-Path $RepoDir 'commands') (Join-Path $ClaudeDir 'commands')
Link-Dir (Join-Path $RepoDir 'agents')   (Join-Path $ClaudeDir 'agents')

# Hooks: per-file symlinks (not directory) because settings.json hooks must
# resolve at all times — a directory swap would break hooks mid-session.
$HooksDir = Join-Path $ClaudeDir 'hooks'
if (-not (Test-Path $HooksDir)) {
    New-Item -ItemType Directory -Path $HooksDir -Force | Out-Null
}
foreach ($hook in Get-ChildItem (Join-Path $RepoDir 'hooks') -Filter '*.py') {
    Link-File $hook.FullName (Join-Path $HooksDir $hook.Name)
}

# Symlink individual files
Link-File (Join-Path $RepoDir 'config\statusline.py')    (Join-Path $ClaudeDir 'statusline-command.py')
Link-File (Join-Path $RepoDir 'config\keybindings.json') (Join-Path $ClaudeDir 'keybindings.json')

# Copy settings.json.example if settings.json doesn't exist
$SettingsPath = Join-Path $ClaudeDir 'settings.json'
if (-not (Test-Path $SettingsPath)) {
    Copy-Item (Join-Path $RepoDir 'config\settings.json.example') $SettingsPath
    Write-Host "  [created] $SettingsPath from template"
} else {
    Write-Host "  [skip] $SettingsPath already exists"
}

# Install Python agent packages (any agents/<name>/pyproject.toml)
$AgentsDir = Join-Path $RepoDir 'agents'
foreach ($toml in Get-ChildItem $AgentsDir -Recurse -Filter 'pyproject.toml' -Depth 1) {
    $agentDir = $toml.DirectoryName
    $agentName = Split-Path $agentDir -Leaf
    Write-Host "  [install] $agentName"
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv pip install --system -e $agentDir
    } else {
        Write-Host "    uv not found - falling back to pip"
        pip install -e $agentDir
    }
}

Write-Host ""
Write-Host "Done."
if ($MadeBackup) {
    Write-Host "Backups saved to: $BackupDir"
}
