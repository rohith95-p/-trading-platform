#!/bin/bash
# Database Migration Script
# This script applies database migrations in order

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Database Migration Tool${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL environment variable is not set${NC}"
    echo "Please set DATABASE_URL to your PostgreSQL connection string"
    echo "Example: export DATABASE_URL='postgresql://user:password@localhost:5432/dbname'"
    exit 1
fi

echo -e "${GREEN}✓ DATABASE_URL is set${NC}"
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MIGRATIONS_DIR="$SCRIPT_DIR"

# Check if migrations directory exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}Error: Migrations directory not found: $MIGRATIONS_DIR${NC}"
    exit 1
fi

# Create migrations tracking table if it doesn't exist
echo -e "${YELLOW}Creating migrations tracking table...${NC}"
psql "$DATABASE_URL" -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
  id SERIAL PRIMARY KEY,
  version TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  applied_at TIMESTAMP DEFAULT NOW()
);
" || {
    echo -e "${RED}Error: Failed to create migrations tracking table${NC}"
    exit 1
}
echo -e "${GREEN}✓ Migrations tracking table ready${NC}"
echo ""

# Get list of applied migrations
APPLIED_MIGRATIONS=$(psql "$DATABASE_URL" -t -c "SELECT version FROM schema_migrations ORDER BY version;")

# Get list of migration files
MIGRATION_FILES=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort)

if [ -z "$MIGRATION_FILES" ]; then
    echo -e "${YELLOW}No migration files found in $MIGRATIONS_DIR${NC}"
    exit 0
fi

# Apply each migration
MIGRATIONS_APPLIED=0
for MIGRATION_FILE in $MIGRATION_FILES; do
    MIGRATION_NAME=$(basename "$MIGRATION_FILE" .sql)
    MIGRATION_VERSION=$(echo "$MIGRATION_NAME" | cut -d'_' -f1)
    
    # Check if migration has already been applied
    if echo "$APPLIED_MIGRATIONS" | grep -q "$MIGRATION_VERSION"; then
        echo -e "${YELLOW}⊘ Skipping $MIGRATION_NAME (already applied)${NC}"
        continue
    fi
    
    echo -e "${YELLOW}→ Applying migration: $MIGRATION_NAME${NC}"
    
    # Apply the migration
    if psql "$DATABASE_URL" -f "$MIGRATION_FILE"; then
        # Record the migration
        psql "$DATABASE_URL" -c "
        INSERT INTO schema_migrations (version, name)
        VALUES ('$MIGRATION_VERSION', '$MIGRATION_NAME');
        " || {
            echo -e "${RED}Error: Failed to record migration $MIGRATION_NAME${NC}"
            exit 1
        }
        echo -e "${GREEN}✓ Migration $MIGRATION_NAME applied successfully${NC}"
        MIGRATIONS_APPLIED=$((MIGRATIONS_APPLIED + 1))
    else
        echo -e "${RED}Error: Failed to apply migration $MIGRATION_NAME${NC}"
        exit 1
    fi
    echo ""
done

echo -e "${GREEN}========================================${NC}"
if [ $MIGRATIONS_APPLIED -eq 0 ]; then
    echo -e "${GREEN}All migrations are up to date!${NC}"
else
    echo -e "${GREEN}Successfully applied $MIGRATIONS_APPLIED migration(s)${NC}"
fi
echo -e "${GREEN}========================================${NC}"
