$pathsToRemove = @(
    "frontend",
    "src/exchanges",
    "src/drl",
    "src/simulation",
    "src/borrowed",
    "src/auth",
    "src/api/auth.py",
    "src/api/trading.py",
    "src/api/webhooks.py",
    "docker-compose.yml",
    "package.json",
    "package-lock.json",
    "start-server.js"
)

foreach ($path in $pathsToRemove) {
    if (Test-Path -Path $path) {
        Write-Host "Removing $path..."
        Remove-Item -Path $path -Recurse -Force
    } else {
        Write-Host "$path not found, skipping."
    }
}
Write-Host "Cleanup complete."
