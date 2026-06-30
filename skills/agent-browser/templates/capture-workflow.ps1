#Requires -Version 7
# Template: Content Capture Workflow
# Purpose: Extract content from web pages (text, screenshots, PDF)
# Usage: ./capture-workflow.ps1 <url> [output-dir]
#
# Outputs:
#   - page-full.png: Full page screenshot
#   - page-structure.txt: Page element structure with refs
#   - page-text.txt: All text content
#   - page.pdf: PDF version
#
# Optional: Load auth state for protected pages

[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [string]$TargetUrl,

    [Parameter(Position = 1)]
    [string]$OutputDir = '.'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "Capturing: $TargetUrl"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Optional: Load authentication state
# if (Test-Path './auth-state.json') {
#     Write-Host 'Loading authentication state...'
#     agent-browser state load './auth-state.json'
# }

# Navigate to target
agent-browser open $TargetUrl
agent-browser wait --load networkidle

# Get metadata
$title = agent-browser get title
$url = agent-browser get url
Write-Host "Title: $title"
Write-Host "URL: $url"

# Capture full page screenshot
agent-browser screenshot --full (Join-Path $OutputDir 'page-full.png')
Write-Host "Saved: $(Join-Path $OutputDir 'page-full.png')"

# Get page structure with refs
agent-browser snapshot -i > (Join-Path $OutputDir 'page-structure.txt')
Write-Host "Saved: $(Join-Path $OutputDir 'page-structure.txt')"

# Extract all text content
agent-browser get text body > (Join-Path $OutputDir 'page-text.txt')
Write-Host "Saved: $(Join-Path $OutputDir 'page-text.txt')"

# Save as PDF
agent-browser pdf (Join-Path $OutputDir 'page.pdf')
Write-Host "Saved: $(Join-Path $OutputDir 'page.pdf')"

# Optional: Extract specific elements using refs from structure
# agent-browser get text @e5 > (Join-Path $OutputDir 'main-content.txt')

# Optional: Handle infinite scroll pages
# foreach ($i in 1..5) {
#     agent-browser scroll down 1000
#     agent-browser wait 1000
# }
# agent-browser screenshot --full (Join-Path $OutputDir 'page-scrolled.png')

# Cleanup
agent-browser close

Write-Host ''
Write-Host 'Capture complete:'
Get-ChildItem $OutputDir
