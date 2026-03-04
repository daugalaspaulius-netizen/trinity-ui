#!/usr/bin/env pwsh
# Build Trinity Chat as Windows Executable (.exe)
# Paulius Daugalas - 2026-02-26

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Trinity Chat - EXE Builder" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# 1. Check if icon exists, generate if needed
if (-not (Test-Path "trinity_chat.ico")) {
    Write-Host "[1/5] Generating icon..." -ForegroundColor Yellow
    & .\create-icon.ps1
    if (-not (Test-Path "trinity_chat.ico")) {
        Write-Host "ERROR: Could not generate icon" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[1/5] Icon found: trinity_chat.ico" -ForegroundColor Green
}

# 2. Check PyInstaller
Write-Host "[2/5] Checking PyInstaller..." -ForegroundColor Yellow
$pyinstallerCheck = python -c "import PyInstaller" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not install PyInstaller" -ForegroundColor Red
        exit 1
    }
    Write-Host "PyInstaller installed successfully" -ForegroundColor Green
} else {
    Write-Host "PyInstaller is ready" -ForegroundColor Green
}

# 3. Clean previous builds
Write-Host "[3/5] Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "trinity_chat_desktop.spec") { Remove-Item -Force "trinity_chat_desktop.spec" }
Write-Host "Build directories cleaned" -ForegroundColor Green

# 4. Build executable
Write-Host "[4/5] Building Trinity Chat.exe..." -ForegroundColor Yellow
Write-Host "This may take 1-2 minutes...`n" -ForegroundColor DarkGray

$buildArgs = @(
    "-F",                                    # One file
    "--windowed",                            # No console window
    "--name=TrinityChat",                    # Executable name
    "--icon=trinity_chat.ico",              # Icon file
    "--add-data=trinity_chat.ico;.",        # Include icon in bundle
    "trinity_chat_desktop.py"               # Source file
)

python -m PyInstaller @buildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: Build failed" -ForegroundColor Red
    exit 1
}

# 5. Verify and present result
Write-Host "`n[5/5] Verifying build..." -ForegroundColor Yellow

if (Test-Path "dist\TrinityChat.exe") {
    $exePath = (Resolve-Path "dist\TrinityChat.exe").Path
    $exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
    
    Write-Host "`n============================================" -ForegroundColor Green
    Write-Host "  BUILD SUCCESS!" -ForegroundColor Green
    Write-Host "============================================`n" -ForegroundColor Green
    
    Write-Host "Executable created:" -ForegroundColor Cyan
    Write-Host "  Location: $exePath" -ForegroundColor White
    Write-Host "  Size: $exeSize MB" -ForegroundColor White
    Write-Host "  Icon: Applied (trinity_chat.ico)" -ForegroundColor White
    
    Write-Host "`nTo run Trinity Chat:" -ForegroundColor Yellow
    Write-Host "  1. Double-click: dist\TrinityChat.exe" -ForegroundColor White
    Write-Host "  2. Or move it anywhere you want" -ForegroundColor White
    
    Write-Host "`nOpening folder..." -ForegroundColor DarkGray
    Start-Process explorer.exe -ArgumentList "/select,`"$exePath`""
    
} else {
    Write-Host "`nERROR: Executable not found in dist\" -ForegroundColor Red
    exit 1
}

Write-Host ""
