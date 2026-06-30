#Requires -Version 7
# Template: Authenticated Session Workflow
# Purpose: Login once, save state, reuse for subsequent runs
# Usage: ./authenticated-session.ps1 <login-url> [state-file]
#
# RECOMMENDED: Use the auth vault instead of this template:
#   "<pass>" | agent-browser auth save myapp --url <login-url> --username <user> --password-stdin
#   agent-browser auth login myapp
# The auth vault stores credentials securely and the LLM never sees passwords.
#
# Environment variables:
#   APP_USERNAME - Login username/email
#   APP_PASSWORD - Login password
#
# Two modes:
#   1. Discovery mode (default): Shows form structure so you can identify refs
#   2. Login mode: Performs actual login after you update the refs
#
# Setup steps:
#   1. Run once to see form structure (discovery mode)
#   2. Update refs in LOGIN FLOW section below
#   3. Set $env:APP_USERNAME and $env:APP_PASSWORD
#   4. Delete the DISCOVERY section

[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [string]$LoginUrl,

    [Parameter(Position = 1)]
    [string]$StateFile = './auth-state.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# Check agent-browser (a native command) via $LASTEXITCODE instead of having a
# non-zero exit terminate the script — mirrors the bash explicit-check pattern.
$PSNativeCommandUseErrorActionPreference = $false

Write-Host "Authentication workflow: $LoginUrl"

# ================================================================
# SAVED STATE: Skip login if valid saved state exists
# ================================================================
if (Test-Path $StateFile) {
    Write-Host "Loading saved state from $StateFile..."
    agent-browser --state $StateFile open $LoginUrl 2>$null
    if ($LASTEXITCODE -eq 0) {
        agent-browser wait --load networkidle

        $currentUrl = agent-browser get url
        if ($currentUrl -notlike '*login*' -and $currentUrl -notlike '*signin*') {
            Write-Host 'Session restored successfully'
            agent-browser snapshot -i
            exit 0
        }
        Write-Host 'Session expired, performing fresh login...'
        agent-browser close 2>$null
    }
    else {
        Write-Host 'Failed to load state, re-authenticating...'
    }
    Remove-Item -Force -ErrorAction SilentlyContinue $StateFile
}

# ================================================================
# DISCOVERY MODE: Shows form structure (delete after setup)
# ================================================================
Write-Host 'Opening login page...'
agent-browser open $LoginUrl
agent-browser wait --load networkidle

Write-Host ''
Write-Host 'Login form structure:'
Write-Host '---'
agent-browser snapshot -i
Write-Host '---'
Write-Host ''
Write-Host 'Next steps:'
Write-Host '  1. Note the refs: username=@e?, password=@e?, submit=@e?'
Write-Host '  2. Update the LOGIN FLOW section below with your refs'
Write-Host "  3. Set: `$env:APP_USERNAME='...'; `$env:APP_PASSWORD='...'"
Write-Host '  4. Delete this DISCOVERY MODE section'
Write-Host ''
agent-browser close
exit 0

# ================================================================
# LOGIN FLOW: Uncomment and customize after discovery
# ================================================================
# if (-not $env:APP_USERNAME) { throw 'Set APP_USERNAME environment variable' }
# if (-not $env:APP_PASSWORD) { throw 'Set APP_PASSWORD environment variable' }
#
# agent-browser open $LoginUrl
# agent-browser wait --load networkidle
# agent-browser snapshot -i
#
# # Fill credentials (update refs to match your form)
# agent-browser fill @e1 $env:APP_USERNAME
# agent-browser fill @e2 $env:APP_PASSWORD
# agent-browser click @e3
# agent-browser wait --load networkidle
#
# # Verify login succeeded
# $finalUrl = agent-browser get url
# if ($finalUrl -like '*login*' -or $finalUrl -like '*signin*') {
#     Write-Host 'Login failed - still on login page'
#     agent-browser screenshot (Join-Path $env:TEMP 'login-failed.png')
#     agent-browser close
#     exit 1
# }
#
# # Save state for future runs
# Write-Host "Saving state to $StateFile"
# agent-browser state save $StateFile
# Write-Host 'Login successful'
# agent-browser snapshot -i
