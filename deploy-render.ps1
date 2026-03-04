# Trinity Quick Deploy to Render.com
# This script guides you through Render.com deployment

Write-Host "🚀 Trinity UI - Render.com Deployment Guide" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

Write-Host "Render.com offers FREE hosting with HTTPS!" -ForegroundColor Green
Write-Host "Perfect for testing Trinity UI with microphone on mobile.`n"

Write-Host "📋 Steps:" -ForegroundColor Yellow
Write-Host "1. Create GitHub repository (public or private)"
Write-Host "2. Push this folder to GitHub"
Write-Host "3. Connect to Render.com"
Write-Host "4. Auto-deploy`n"

$choice = Read-Host "Do you have a GitHub repository? (y/n)"

if ($choice -eq 'y') {
    $repoUrl = Read-Host "Enter your GitHub repository URL"
    
    Write-Host "`n✅ Great! Now:" -ForegroundColor Green
    Write-Host "1. Open: https://render.com" -ForegroundColor Cyan
    Write-Host "2. Sign in with GitHub" -ForegroundColor Cyan
    Write-Host "3. Click 'New +' → 'Web Service'" -ForegroundColor Cyan
    Write-Host "4. Connect your repo: $repoUrl" -ForegroundColor Yellow
    Write-Host "5. Render auto-detects Docker + render.yaml" -ForegroundColor Cyan
    Write-Host "6. Click 'Create Web Service'" -ForegroundColor Cyan
    Write-Host "`n⏱️ Deployment takes ~5 minutes" -ForegroundColor Yellow
    Write-Host "📱 You'll get HTTPS URL: https://trinity-ui-xxxx.onrender.com" -ForegroundColor Green
    
} else {
    Write-Host "`n📦 First, let's create a GitHub repository:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://github.com/new" -ForegroundColor Cyan
    Write-Host "2. Repository name: trinity-ui" -ForegroundColor Cyan
    Write-Host "3. Make it Public or Private (both work)" -ForegroundColor Cyan
    Write-Host "4. Don't add README/gitignore (we have them)" -ForegroundColor Cyan
    Write-Host "5. Click 'Create repository'`n" -ForegroundColor Cyan
    
    $createRepo = Read-Host "Press Enter when done, or 'skip' to do manually"
    
    if ($createRepo -ne 'skip') {
        $gitUrl = Read-Host "Enter your new repository URL (https://github.com/username/trinity-ui)"
        
        Write-Host "`n🔧 Initializing Git..." -ForegroundColor Cyan
        
        # Initialize git if not already
        if (-not (Test-Path .git)) {
            git init
            Write-Host "✅ Git initialized" -ForegroundColor Green
        }
        
        # Create .gitignore
        $gitignoreContent = @"
.venv/
.venv-1/
.venv-trinity/
__pycache__/
*.pyc
*.log
.env
*.egg-info/
.tunnel-url.log
"@
        $gitignoreContent | Out-File -FilePath ".gitignore" -Encoding utf8
        
        Write-Host "Git ignore created" -ForegroundColor Green
        
        # Add files
        git add .
        git commit -m "Trinity UI - Initial deployment"
        git branch -M main
        git remote add origin $gitUrl
        git push -u origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`nCode pushed to GitHub!" -ForegroundColor Green
            Write-Host "`nNow deploy to Render.com:" -ForegroundColor Yellow
            Write-Host "1. Open: https://render.com" -ForegroundColor Cyan
            Write-Host "2. Sign in with GitHub" -ForegroundColor Cyan
            Write-Host "3. Click 'New +' → 'Web Service'" -ForegroundColor Cyan
            Write-Host "4. Connect: $gitUrl" -ForegroundColor Yellow
            Write-Host "5. Click 'Create Web Service'" -ForegroundColor Cyan
        } else {
            Write-Host "`nGit push failed - you may need to:" -ForegroundColor Yellow
            Write-Host "- Configure Git credentials (git config user.name / user.email)"
            Write-Host "- Or push manually: git push -u origin main"
        }
    }
}

Write-Host "`nAfter deployment:" -ForegroundColor Green
Write-Host "Open HTTPS URL on your phone" -ForegroundColor Cyan
Write-Host "Test microphone - it will work!" -ForegroundColor Cyan
Write-Host "No more errors" -ForegroundColor Green
