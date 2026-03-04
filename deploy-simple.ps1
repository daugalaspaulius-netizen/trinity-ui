# Trinity Deployment Script
Write-Host "Trinity Deployment to Render.com" -ForegroundColor Cyan

# Check if git is initialized
if (-not (Test-Path .git)) {
    git init
    Write-Host "Git initialized" -ForegroundColor Green
}

# Create .gitignore
$ignore = ".venv/`n.venv-1/`n.venv-trinity/`n__pycache__/`n*.pyc`n*.log`n.env`n*.egg-info/"
$ignore | Out-File -FilePath ".gitignore" -Encoding utf8

# Add files
git add .

# Configure git if needed
$username = git config user.name
if ([string]::IsNullOrWhiteSpace($username)) {
    git config user.name "Trinity User"
    git config user.email "trinity@example.com"
}

# Commit
git commit -m "Trinity UI deployment"

# Show next steps
Write-Host "`n=== NEXT STEPS ===" -ForegroundColor Yellow
Write-Host "1. Create GitHub repo: https://github.com/new" -ForegroundColor Cyan
Write-Host "   Name it: trinity-ui" -ForegroundColor Cyan
Write-Host "2. Copy the commands GitHub shows you" -ForegroundColor Cyan
Write-Host "3. Or run these:" -ForegroundColor Cyan
Write-Host "   git remote add origin https://github.com/YOUR-USERNAME/trinity-ui.git" -ForegroundColor White
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host "`n4. Then go to: https://render.com" -ForegroundColor Cyan
Write-Host "5. Sign in with GitHub" -ForegroundColor Cyan
Write-Host "6. Click New + > Web Service" -ForegroundColor Cyan
Write-Host "7. Connect your trinity-ui repo" -ForegroundColor Cyan
Write-Host "8. Click Create Web Service" -ForegroundColor Cyan
Write-Host "`nYou will get: https://trinity-ui-XXXX.onrender.com" -ForegroundColor Green
Write-Host "This link works FOREVER on computer AND phone!" -ForegroundColor Green
