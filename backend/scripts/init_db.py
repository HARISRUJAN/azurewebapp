"""Initialize database with default admin user"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import init_db, User, SessionLocal
from app.core.security import get_password_hash

def create_default_admin():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("Admin user already exists")
            return
        
        # Create default admin
        admin = User(
            username="admin",
            email="admin@aigov.org",
            hashed_password=get_password_hash("admin123"),  # Change in production!
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("Default admin user created:")
        print("  Username: admin")
        print("  Password: admin123")
        print("  ⚠️  Please change the password in production!")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Creating default admin user...")
    create_default_admin()
    print("Done!")

