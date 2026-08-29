[CmdletBinding()]
param(
    [string]$ClaudeHome = (Join-Path $HOME ".claude"),
    [string]$CodexHome = (Join-Path $HOME ".codex"),
    [string]$ClawdHome = (Join-Path $HOME "clawd"),
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot

function Copy-Tree([string]$Source, [string]$Destination) {
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Path (Join-Path $Source "*") -Destination $Destination -Recurse -Force
}

Write-Host "Installing Claude ↔ Codex bridge..."

Copy-Tree (Join-Path $RepoRoot "skills\claude-tool-index-bridge") `
    (Join-Path $CodexHome "skills\claude-tool-index-bridge")
Copy-Tree (Join-Path $RepoRoot "claude-skills\indexar-proyecto") `
    (Join-Path $ClaudeHome "skills\indexar-proyecto")
Copy-Tree (Join-Path $RepoRoot "claude-skills\recuperar-proyecto") `
    (Join-Path $ClaudeHome "skills\recuperar-proyecto")

$ProjectsIndex = Join-Path $ClawdHome "projects-index"
$Tools = Join-Path $ClawdHome "tools"
New-Item -ItemType Directory -Force -Path $ProjectsIndex, $Tools | Out-Null
Copy-Item (Join-Path $RepoRoot "project-memory\pidx.py") (Join-Path $ProjectsIndex "pidx.py") -Force
Copy-Item (Join-Path $RepoRoot "scripts\build_tool_index.py") (Join-Path $Tools "build_tool_index.py") -Force

if (-not (Test-Path (Join-Path $ProjectsIndex "index.json"))) {
    '{"projects": []}' | Set-Content -Encoding UTF8 (Join-Path $ProjectsIndex "index.json")
}

[Environment]::SetEnvironmentVariable("CLAUDE_HOME", $ClaudeHome, "User")
[Environment]::SetEnvironmentVariable("CODEX_HOME", $CodexHome, "User")
[Environment]::SetEnvironmentVariable("CLAWD_HOME", $ClawdHome, "User")
[Environment]::SetEnvironmentVariable("PIDX_HOME", $ProjectsIndex, "User")

$env:CLAUDE_HOME = $ClaudeHome
$env:CODEX_HOME = $CodexHome
$env:CLAWD_HOME = $ClawdHome
$env:PIDX_HOME = $ProjectsIndex

if (-not $SkipBuild) {
    python (Join-Path $Tools "build_tool_index.py") build
}

Write-Host "Installed. Restart Claude Code and Codex, then run:"
Write-Host "  python `"$CodexHome\skills\claude-tool-index-bridge\scripts\lookup.py`" /recuperar-proyecto"
