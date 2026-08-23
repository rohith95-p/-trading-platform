# Verify Railway Deployment Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verifying Railway Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Get Railway URL
Write-Host "[1/4] Getting Railway URL..." -ForegroundColor Yellow
try {
    # Try to get domain from railway.json
    if (Test-Path "railway.json") {
        $railwayConfig = Get-Content "railway.json" | ConvertFrom-Json
        Write-Host "âœ… Railway project found" -ForegroundColor Green
    }
    
    # Get the URL from Railway CLI
    Write-Host "Run this command to get your URL:" -ForegroundColor Yellow
    Write-Host "  railway domain" -ForegroundColor White
    Write-Host ""
    Write-Host "Or open Railway dashboard:" -ForegroundColor Yellow
    Write-Host "  railway open" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "âš ï¸  Could not auto-detect URL" -ForegroundColor Yellow
}

# Step 2: Check logs
Write-Host "[2/4] Checking deployment logs..." -ForegroundColor Yellow
Write-Host "Run this to see logs:" -ForegroundColor Yellow
Write-Host "  railway logs --tail 50" -ForegroundColor White
Write-Host ""

# Step 3: Check status
Write-Host "[3/4] Checking service status..." -ForegroundColor Yellow
Write-Host "Run this to check status:" -ForegroundColor Yellow
Write-Host "  railway status" -ForegroundColor White
Write-Host ""

# Step 4: Test health endpoint
Write-Host "[4/4] Testing health endpoint..." -ForegroundColor Yellow
Write-Host "Once you have your URL, test with:" -ForegroundColor Yellow
Write-Host '  $url = "https://your-app.up.railway.app"' -ForegroundColor White
Write-Host '  curl "$url/health"' -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Manual Verification Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Get your Railway URL:" -ForegroundColor White
Write-Host "   railway domain" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Wait 1-2 minutes for service to start" -ForegroundColor White
Write-Host ""
Write-Host "3. Test health endpoint:" -ForegroundColor White
Write-Host '   curl "https://your-url.up.railway.app/health"' -ForegroundColor Gray
Write-Host ""
Write-Host "4. Expected response:" -ForegroundColor White
Write-Host '   {"status": "healthy", "version": "1.0.0"}' -ForegroundColor Gray
Write-Host ""
Write-Host "5. Check API docs in browser:" -ForegroundColor White
Write-Host "   https://your-url.up.railway.app/docs" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Troubleshooting" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If health check fails:" -ForegroundColor Yellow
Write-Host "  1. Check logs: railway logs" -ForegroundColor Gray
Write-Host "  2. Check status: railway status" -ForegroundColor Gray
Write-Host "  3. Verify variables: railway variables" -ForegroundColor Gray
Write-Host "  4. Open dashboard: railway open" -ForegroundColor Gray
Write-Host ""
