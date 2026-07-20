param(
  [switch]$PublishPages,
  [switch]$PushReport,
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$PagesWorktree = "C:\dev\mom-index-pages"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location -LiteralPath $RepoRoot

$logDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logDir "daily-$stamp.log"

function Write-Log {
  param([string]$Message)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  $line | Tee-Object -FilePath $logFile -Append
}

Write-Log "Starting Mom Index daily pipeline"
Write-Log "RepoRoot: $RepoRoot"

$userOpenRouterKey = [Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY", "User")
if (-not $env:OPENROUTER_API_KEY -and $userOpenRouterKey) {
  $env:OPENROUTER_API_KEY = $userOpenRouterKey
}
if (-not $env:OPENROUTER_API_KEY) {
  Write-Log "OPENROUTER_API_KEY is missing; LLM-only classifier cannot run"
  exit 1
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:MOM_INDEX_CLASSIFIER = "semantic"
$env:MOM_INDEX_SEMANTIC_PROVIDER = "openrouter"
$env:MOM_INDEX_SEMANTIC_MODEL = "openrouter/free"
$env:MOM_INDEX_LLM_ONLY = "1"

Write-Log "Classifier mode: semantic/openrouter LLM-only"

python pipeline.py 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) {
  Write-Log "Pipeline failed with exit code $LASTEXITCODE; skipping publish"
  exit $LASTEXITCODE
}

Write-Log "Pipeline completed"

python scripts/generate_issue_template.py 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) {
  Write-Log "Issue template generation failed with exit code $LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Log "Issue template generated"

if ($PushReport) {
  Write-Log "Preparing safe daily report commit for marcko"
  $reportPaths = @(
    ".github/ISSUE_TEMPLATE.md",
    "data/dashboard_data.json",
    "data/history.json",
    "frontend/data/dashboard_data.json",
    "frontend/data/history.json"
  )

  git add -- $reportPaths 2>&1 | Tee-Object -FilePath $logFile -Append

  git diff --cached --quiet
  $reportDiffExit = $LASTEXITCODE
  if ($reportDiffExit -eq 0) {
    Write-Log "No safe report changes to push"
    git reset -- $reportPaths 2>&1 | Tee-Object -FilePath $logFile -Append
  } else {
    $date = Get-Date -Format "yyyy-MM-dd"
    git commit -m "Update daily mom index report $date" 2>&1 | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -ne 0) {
      Write-Log "Report commit failed with exit code $LASTEXITCODE"
      exit $LASTEXITCODE
    }

    git push marcko HEAD 2>&1 | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -ne 0) {
      Write-Log "Report push failed with exit code $LASTEXITCODE"
      exit $LASTEXITCODE
    }
    Write-Log "Pushed safe daily report changes to marcko"
  }
}

if (-not $PublishPages) {
  Write-Log "PublishPages not set; leaving results local only"
  exit 0
}

Write-Log "Preparing GitHub Pages payload"

$tmpPublic = Join-Path $RepoRoot ".tmp-public-data"
New-Item -ItemType Directory -Force -Path $tmpPublic | Out-Null

Copy-Item -LiteralPath (Join-Path $RepoRoot "data\dashboard_data.json") -Destination (Join-Path $tmpPublic "dashboard_data.json") -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "data\history.json") -Destination (Join-Path $tmpPublic "history.json") -Force

if (-not (Test-Path -LiteralPath $PagesWorktree)) {
  Write-Log "Creating gh-pages worktree at $PagesWorktree"
  git fetch marcko gh-pages:gh-pages 2>&1 | Tee-Object -FilePath $logFile -Append
  if ($LASTEXITCODE -ne 0) {
    Write-Log "Pages fetch failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
  }
  git worktree add $PagesWorktree gh-pages 2>&1 | Tee-Object -FilePath $logFile -Append
  if ($LASTEXITCODE -ne 0) {
    Write-Log "Pages worktree creation failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
  }
}

New-Item -ItemType Directory -Force -Path (Join-Path $PagesWorktree "data") | Out-Null
Copy-Item -LiteralPath (Join-Path $tmpPublic "dashboard_data.json") -Destination (Join-Path $PagesWorktree "data\dashboard_data.json") -Force
Copy-Item -LiteralPath (Join-Path $tmpPublic "history.json") -Destination (Join-Path $PagesWorktree "data\history.json") -Force

Push-Location -LiteralPath $PagesWorktree
try {
  git status --short 2>&1 | Tee-Object -FilePath $logFile -Append
  git add data/dashboard_data.json data/history.json

  git diff --cached --quiet
  $diffExit = $LASTEXITCODE
  if ($diffExit -eq 0) {
    Write-Log "No public Pages data changes to publish"
    git reset 2>&1 | Tee-Object -FilePath $logFile -Append
  } else {
    $date = Get-Date -Format "yyyy-MM-dd"
    git commit -m "Update daily dashboard data $date" 2>&1 | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -ne 0) {
      Write-Log "Pages commit failed with exit code $LASTEXITCODE"
      exit $LASTEXITCODE
    }
    git push marcko gh-pages 2>&1 | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -ne 0) {
      Write-Log "Pages push failed with exit code $LASTEXITCODE"
      exit $LASTEXITCODE
    }
    Write-Log "Published dashboard data to gh-pages"
  }
} finally {
  Pop-Location
}

Write-Log "Daily run finished"
exit 0
