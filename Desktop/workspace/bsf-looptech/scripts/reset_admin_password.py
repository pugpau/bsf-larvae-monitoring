#!/usr/bin/env python3
"""
Reset admin user password for BSF-LoopTech system.
"""

import asyncio
import sys
import os
from getpass import getpass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import AsyncSession
from src.database.postgresql import AsyncSessionLocal, init_database
from src.auth.service import UserManagementService
from src.auth.security import get_password_hash
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def reset_admin_password():
    """Reset the admin user password."""
    print("\n=== BSF-LoopTech Admin Password Reset ===\n")
    
    # Default password for quick reset
    default_password = "Admin123456!"
    
    # Ask if user wants to use default or custom password
    use_default = input(f"Use default password '{default_password}'? (y/n): ").strip().lower()
    
    if use_default == 'y':
        password = default_password
    else:
        # Get custom password
        while True:
            password = getpass("Enter new password (min 8 characters): ")
            if len(password) < 8:
                print("Password must be at least 8 characters long.")
                continue
            password_confirm = getpass("Confirm password: ")
            if password != password_confirm:
                print("Passwords do not match. Please try again.")
                continue
            break
    
    print("\nResetting admin password...")
    
    try:
        # Initialize database if needed
        await init_database()
        
        async with AsyncSessionLocal() as session:
            # Direct SQL update for the admin user
            from sqlalchemy import text
            
            # Hash the password
            hashed_password = get_password_hash(password)
            
            # Update the admin user's password
            result = await session.execute(
                text("""
                    UPDATE users 
                    SET hashed_password = :password,
                        updated_at = NOW(),
                        password_changed_at = NOW()
                    WHERE username = 'admin' OR email = 'admin@example.com'
                """),
                {"password": hashed_password}
            )
            
            await session.commit()
            
            if result.rowcount > 0:
                print(f"\n✅ Password reset successfully!")
                print(f"   Username: admin")
                print(f"   Email: admin@example.com")
                print(f"   New Password: {password if use_default == 'y' else '[your custom password]'}")
                print(f"\nYou can now login with these credentials.")
                return True
            else:
                print("❌ Admin user not found. Creating new admin user...")
                
                # If admin doesn't exist, create it
                from src.auth.models import UserRole
                from src.auth.schemas import UserCreate
                
                user_service = UserManagementService(session)
                
                user_data = UserCreate(
                    username="admin",
                    email="admin@example.com",
                    password=password,
                    full_name="Administrator",
                    role=UserRole.ADMIN,
                    is_active=True
                )
                
                user = await user_service.create_user(user_data)
                await session.commit()
                
                if user:
                    print(f"\n✅ Admin user created successfully!")
                    print(f"   Username: admin")
                    print(f"   Email: admin@example.com")
                    print(f"   Password: {password if use_default == 'y' else '[your custom password]'}")
                    print(f"\nYou can now login with these credentials.")
                    return True
                else:
                    print("Failed to create admin user.")
                    return False
                
    except Exception as e:
        logger.error(f"Error resetting admin password: {e}")
        print(f"Error: {e}")
        return False


def main():
    """Main entry point."""
    asyncio.run(reset_admin_password())


if __name__ == "__main__":
    main()