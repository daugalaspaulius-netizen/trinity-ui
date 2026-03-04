# Auto-deploy Trinity to HTTPS
# VIENAS SCRIPTAS - VIENA NUORODA

Write-Host "=== TRINITY AUTO-DEPLOY ===" -ForegroundColor Green

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Check gh auth status
$authStatus = gh auth status 2>&1
if ($authStatus -like "*not logged*" -or $authStatus -like "*not authenticated*") {
    Write-Host "GitHub authentication needed (ONE TIME ONLY)" -ForegroundColor Yellow
    Write-Host "Browser will open - just click AUTHORIZE" -ForegroundColor Cyan
    
    # Auto-answer the prompts
    "HTTPS" | gh auth login --web --git-protocol https
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Auth failed. Run this when you stop driving:" -ForegroundColor Red
        Write-Host "gh auth login --web" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "GitHub authenticated OK" -ForegroundColor Green

# Create repo
Write-Host "Creating GitHub repo..." -ForegroundColor Cyan
git branch -M main

$repoName = "trinity-ui-$(Get-Date -Format 'MMdd-HHmm')"
gh repo create $repoName --public --source=. --remote=origin --push

if ($LASTEXITCODE -ne 0) {
    Write-Host "Repo creation failed" -ForegroundColor Red
    exit 1
}

Write-Host "Code pushed to GitHub" -ForegroundColor Green

# Get repo URL
$repoUrl = gh repo view --json url -q .url

Write-Host "`n=== FINAL STEP ===" -ForegroundColor Yellow
Write-Host "1. Open: https://dashboard.render.com/" -ForegroundColor Cyan
Write-Host "2. Sign in with GitHub (2 clicks)" -ForegroundColor Cyan
Write-Host "3. Click 'New +' -> 'Web Service'" -ForegroundColor Cyan
Write-Host "4. Select: $repoName" -ForegroundColor White
Write-Host "5. Click 'Create Web Service' (Render auto-detects settings)" -ForegroundColor Cyan
Write-Host "`nWait 5 min, you get: https://trinity-ui-xxxxx.onrender.com" -ForegroundColor Green
Write-Host "PERMANENT LINK - works on phone and computer FOREVER" -ForegroundColor Green

# Alternative: Direct deploy via Render CLI
Write-Host "`nOR install Render CLI for fully automated deploy:" -ForegroundColor Yellow
Write-Host "npm install -g render-cli" -ForegroundColor White
Write-Host "render login" -ForegroundColor White
Write-Host "render deploy" -ForegroundColor White
