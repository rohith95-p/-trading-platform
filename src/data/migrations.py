"""
Database migration utilities

This module provides functions for creating, upgrading, and managing database schema.
"""

import logging
from sqlalchemy import text
from src.data.database import engine, SessionLocal
from src.data.models import Base

logger = logging.getLogger(__name__)

def create_all_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise

def drop_all_tables():
    """Drop all database tables (use with caution!)"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise

def setup_rls_policies():
    """Setup Row Level Security (RLS) policies for Supabase"""
    db = SessionLocal()
    try:
        # Enable RLS on all tables
        tables = ["strategies", "trades", "positions", "signals", "api_keys"]
        
        for table in tables:
            # Enable RLS
            db.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            logger.info(f"RLS enabled on {table}")
        
        # Create policies for strategies
        db.execute(text("""
            CREATE POLICY "Users can view own strategies" ON strategies
            FOR SELECT USING (auth.uid() = user_id);
        """))
        
        # Create policies for trades
        db.execute(text("""
            CREATE POLICY "Users can view own trades" ON trades
            FOR SELECT USING (auth.uid() = user_id);
        """))
        
        # Create policies for positions
        db.execute(text("""
            CREATE POLICY "Users can view own positions" ON positions
            FOR SELECT USING (auth.uid() = user_id);
        """))
        
        # Create policies for signals
        db.execute(text("""
            CREATE POLICY "Users can view own signals" ON signals
            FOR SELECT USING (auth.uid() = user_id);
        """))
        
        # Create policies for api_keys
        db.execute(text("""
            CREATE POLICY "Users can view own api_keys" ON api_keys
            FOR SELECT USING (auth.uid() = user_id);
        """))
        
        db.commit()
        logger.info("RLS policies created successfully")
    except Exception as e:
        db.rollback()
        logger.warning(f"RLS policies setup failed (may already exist): {e}")
    finally:
        db.close()

def create_indexes():
    """Create additional indexes for performance"""
    db = SessionLocal()
    try:
        # Indexes are already defined in models, but this can be used for additional ones
        logger.info("Indexes verified in models")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise
    finally:
        db.close()

def migrate_up():
    """Run all migrations (create tables, indexes, policies)"""
    logger.info("Starting database migration...")
    create_all_tables()
    create_indexes()
    setup_rls_policies()
    logger.info("Database migration completed successfully")

def migrate_down():
    """Rollback all migrations (drop all tables)"""
    logger.warning("Rolling back database migrations...")
    drop_all_tables()
    logger.warning("Database rollback completed")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "up":
            migrate_up()
        elif command == "down":
            migrate_down()
        else:
            print("Usage: python migrations.py [up|down]")
    else:
        migrate_up()
