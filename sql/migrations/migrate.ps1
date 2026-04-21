# Database Migration Script (PowerShell)
# This script applies database migrations in order

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Database Migration Tool" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if DATABASE_URL is set
if (-not $env:DATABASE_URL) {
    Write-Host "Error: DATABASE_URL environment variable is not set" -ForegroundColor Red
    Write-Host "Please set DATABASE_URL to your PostgreSQL connection string"
    Write-Host "Example: `$env:DATABASE_URL='postgresql://user:password@localhost:5432/dbname'"
    exit 1
}

Write-Host "✓ DATABASE_URL is set" -ForegroundColor Green
Write-Host ""

# Get the directory of this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MigrationsDir = $ScriptDir

# Check if migrations directory exists
if (-not (Test-Path $MigrationsDir)) {
    Write-Host "Error: Migrations directory not found: $MigrationsDir" -ForegroundColor Red
    exit 1
}

# Create migrations tracking table if it doesn't exist
Write-Host "Creating migrations tracking table..." -ForegroundColor Yellow
$createTableQuery = @"
CREATE TABLE IF NOT EXISTS schema_migrations (
  id SERIAL PRIMARY KEY,
  version TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  applied_at TIMESTAMP DEFAULT NOW()
);
"@

try {
    psql $env:DATABASE_URL -c $createTableQuery | Out-Null
    Write-Host "✓ Migrations tracking table ready" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "Error: Failed to create migrations tracking table" -ForegroundColor Red
    exit 1
}

# Get list of applied migrations
$appliedMigrations = psql $env:DATABASE_URL -t -c "SELECT version FROM schema_migrations ORDER BY version;"

# Get list of migration files
$migrationFiles = Get-ChildItem -Path $MigrationsDir -Filter "*.sql" | Sort-Object Name

if ($migrationFiles.Count -eq 0) {
    Write-Host "No migration files found in $MigrationsDir" -ForegroundColor Yellow
    exit 0
}

# Apply each migration
$migrationsApplied = 0
foreach ($migrationFile in $migrationFiles) {
    $migrationName = $migrationFile.BaseName
    $migrationVersion = $migrationName.Split('_')[0]
    
    # Check if migration has already been applied
    if ($appliedMigrations -match $migrationVersion) {
        Write-Host "⊘ Skipping $migrationName (already applied)" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "→ Applying migration: $migrationName" -ForegroundColor Yellow
    
    # Apply the migration
    try {
        psql $env:DATABASE_URL -f $migrationFile.FullName | Out-Null
        
        # Record the migration
        $recordQuery = "INSERT INTO schema_migrations (version, name) VALUES ('$migrationVersion', '$migrationName');"
        psql $env:DATABASE_URL -c $recordQuery | Out-Null
        
        Write-Host "✓ Migration $migrationName applied successfully" -ForegroundColor Green
        $migrationsApplied++
    } catch {
        Write-Host "Error: Failed to apply migration $migrationName" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Green
if ($migrationsApplied -eq 0) {
    Write-Host "All migrations are up to date!" -ForegroundColor Green
} else {
    Write-Host "Successfully applied $migrationsApplied migration(s)" -ForegroundColor Green
}
Write-Host "========================================" -ForegroundColor Green
