# AWS EC2 Setup Script - Ultra Core Trading Bot
# Run this on your Windows Server 2022 EC2 instance

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Ultra Core - AWS EC2 Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Install Chocolatey (Windows Package Manager)
Write-Host "[1/6] Installing Chocolatey..." -ForegroundColor Yellow
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "  Chocolatey installed!" -ForegroundColor Green
} else {
    Write-Host "  Chocolatey already installed" -ForegroundColor Green
}

# 2. Install Git
Write-Host "[2/6] Installing Git..." -ForegroundColor Yellow
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    choco install git -y
    refreshenv
    Write-Host "  Git installed!" -ForegroundColor Green
} else {
    Write-Host "  Git already installed" -ForegroundColor Green
}

# 3. Install Python
Write-Host "[3/6] Installing Python 3.11..." -ForegroundColor Yellow
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    choco install python311 -y
    refreshenv
    Write-Host "  Python installed!" -ForegroundColor Green
} else {
    Write-Host "  Python already installed" -ForegroundColor Green
}

# 4. Clone Repository from GitHub
Write-Host "[4/6] Cloning Ultra Core from GitHub..." -ForegroundColor Yellow

$repoPath = "$env:USERPROFILE\ultra_core"

if (Test-Path $repoPath) {
    Write-Host "  Repository already exists. Pulling latest changes..." -ForegroundColor Yellow
    cd $repoPath
    git pull origin main
} else {
    Write-Host "  Cloning repository..." -ForegroundColor Yellow
    # Replace with your actual GitHub repo URL
    git clone https://github.com/YOUR_USERNAME/ultra_core.git $repoPath
    cd $repoPath
}

Write-Host "  Repository ready!" -ForegroundColor Green

# 5. Install Python Dependencies
Write-Host "[5/6] Installing Python dependencies..." -ForegroundColor Yellow
cd $repoPath
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "  Dependencies installed!" -ForegroundColor Green

# 6. Install MT5 Terminal
Write-Host "[6/6] Installing MetaTrader 5..." -ForegroundColor Yellow
$mt5Installer = "$env:TEMP\mt5setup.exe"

if (!(Test-Path "C:\Program Files\MetaTrader 5\terminal64.exe")) {
    Write-Host "  Downloading MT5..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe" -OutFile $mt5Installer
    
    Write-Host "  Installing MT5 (silent)..." -ForegroundColor Yellow
    Start-Process -FilePath $mt5Installer -ArgumentList "/auto" -Wait
    
    Remove-Item $mt5Installer -Force
    Write-Host "  MT5 installed!" -ForegroundColor Green
} else {
    Write-Host "  MT5 already installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open MetaTrader 5 and login to your Exness account" -ForegroundColor White
Write-Host "2. Copy your .env.local file to: $repoPath" -ForegroundColor White
Write-Host "3. Start the bot: python -m src.main_loop" -ForegroundColor White
Write-Host ""
Write-Host "Repository location: $repoPath" -ForegroundColor Cyan
