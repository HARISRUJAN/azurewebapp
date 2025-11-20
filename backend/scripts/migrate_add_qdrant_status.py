"""Migration script to add qdrant_status column to scraping_origins table"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import engine
from sqlalchemy import text

def migrate_add_qdrant_status():
    """Add qdrant_status column to scraping_origins table if it doesn't exist"""
    print("Starting migration: Adding qdrant_status column to scraping_origins table...")
    
    try:
        with engine.begin() as conn:
            # Check if column already exists
            if 'sqlite' in str(engine.url):
                # SQLite: Check if column exists by querying table info
                result = conn.execute(text("PRAGMA table_info(scraping_origins)"))
                columns = [row[1] for row in result]
                
                if 'qdrant_status' in columns:
                    print("[OK] Column 'qdrant_status' already exists. Migration not needed.")
                    return
                
                # SQLite: Add column
                conn.execute(text("ALTER TABLE scraping_origins ADD COLUMN qdrant_status TEXT"))
                print("[OK] Successfully added 'qdrant_status' column to scraping_origins table (SQLite)")
            else:
                # PostgreSQL/Other: Check if column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='scraping_origins' AND column_name='qdrant_status'
                """))
                
                if result.fetchone():
                    print("[OK] Column 'qdrant_status' already exists. Migration not needed.")
                    return
                
                # PostgreSQL: Add column
                conn.execute(text("ALTER TABLE scraping_origins ADD COLUMN qdrant_status VARCHAR"))
                print("[OK] Successfully added 'qdrant_status' column to scraping_origins table (PostgreSQL)")
            
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        print("If the column already exists, this is safe to ignore.")
        raise

if __name__ == "__main__":
    migrate_add_qdrant_status()

