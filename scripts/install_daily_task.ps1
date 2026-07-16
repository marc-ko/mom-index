param(
  [string]$TaskName = "MomIndexDaily",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$Time = "08:00",
  [switch]$PublishPages,
  [switch]$PushReport
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $RepoRoot "scripts\run_daily.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Missing runner script: $runner"
}

$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
if ($PublishPages) {
  $arguments += " -PublishPages"
}
if ($PushReport) {
  $arguments += " -PushReport"
}

$taskRun = "powershell.exe $arguments"

schtasks /Create /TN $TaskName /SC DAILY /ST $Time /TR $taskRun /F | Out-Host

Write-Host "Installed scheduled task '$TaskName' for $Time local Windows time."
Write-Host "Runner: $runner"
if ($PublishPages) {
  Write-Host "Publish mode: sanitized GitHub Pages data only; raw scraped JSON is not published."
} else {
  Write-Host "Publish mode: off; results stay local."
}
if ($PushReport) {
  Write-Host "Report mode: safe daily report files are pushed to marcko, triggering the issue workflow."
} else {
  Write-Host "Report mode: off; daily issue template is generated locally only."
}
