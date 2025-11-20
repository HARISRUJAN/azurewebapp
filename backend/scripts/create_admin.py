"""Create admin user with better error handling"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import init_db, User, SessionLocal
from app.core.security import get_password_hash, verify_password

def create_admin():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("[INFO] Admin user already exists")
            # Test password
            if verify_password("admin123", admin.hashed_password):
                print("[OK] Password verification works!")
                return True
            else:
                print("[WARNING] Password doesn't match. Updating password...")
                admin.hashed_password = get_password_hash("admin123")
                db.commit()
                print("[OK] Password updated!")
                return True
        
        # Create default admin
        print("[INFO] Creating admin user...")
        password_hash = get_password_hash("admin123")
        print(f"[INFO] Password hash generated (length: {len(password_hash)})")
        
        admin = User(
            username="admin",
            email="admin@aigov.org",
            hashed_password=password_hash,
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        
        # Verify it was created
        admin_check = db.query(User).filter(User.username == "admin").first()
        if admin_check and verify_password("admin123", admin_check.hashed_password):
            print("[OK] Admin user created successfully!")
            print("  Username: admin")
            print("  Password: admin123")
            return True
        else:
            print("[ERROR] Admin user creation failed verification")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Creating/verifying admin user...")
    success = create_admin()
    if success:
        print("\n[SUCCESS] Admin user is ready!")
    else:
        print("\n[FAILED] Could not create admin user")
        sys.exit(1)

