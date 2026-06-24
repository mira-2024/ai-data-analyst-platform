# DataFlow AI - Push to GitHub
# Run from the project root. Sign in to GitHub when the browser popup appears.

$ErrorActionPreference = "Stop"
$repo = "https://github.com/mira-2024/ai-data-analyst-platform.git"

Write-Host "[1/6] Cleaning up any broken .git folder..." -ForegroundColor Cyan
if (Test-Path ".git") { Remove-Item -Recurse -Force ".git" }

Write-Host "[2/6] Initialising git repository..." -ForegroundColor Cyan
git init
git branch -M main

Write-Host "[3/6] Configuring identity..." -ForegroundColor Cyan
git config user.name "mira-2024"
git config user.email "naimmiraaa@gmail.com"

Write-Host "[4/6] Staging all files..." -ForegroundColor Cyan
git add .

Write-Host "[5/6] Creating initial commit..." -ForegroundColor Cyan
git commit -m "feat: initial commit - Multi-Agent AI Data Analyst Platform"

Write-Host "[6/6] Pushing to GitHub..." -ForegroundColor Cyan
git remote add origin $repo
git push -u origin main

Write-Host ""
Write-Host "Done! Visit: $repo" -ForegroundColor Green
