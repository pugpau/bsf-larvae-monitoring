#!/usr/bin/env python3
"""
Create initial admin user for BSF-LoopTech system.
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
from src.auth.models import UserRole
from src.auth.schemas import UserCreate
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def create_admin_user():
    """Create an admin user interactively."""
    print("\n=== BSF-LoopTech Admin User Creation ===\n")
    
    # Get user input
    username = input("Enter admin username (default: admin): ").strip() or "admin"
    email = input("Enter admin email (default: admin@bsf-looptech.local): ").strip() or "admin@bsf-looptech.local"
    
    # Get password
    while True:
        password = getpass("Enter password (min 8 characters): ")
        if len(password) < 8:
            print("Password must be at least 8 characters long.")
            continue
        password_confirm = getpass("Confirm password: ")
        if password != password_confirm:
            print("Passwords do not match. Please try again.")
            continue
        break
    
    print("\nCreating admin user...")
    
    try:
        # Initialize database if needed
        await init_database()
        
        # Create user
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.database.postgresql import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            user_service = UserManagementService(session)
            
            # Check if user already exists
            existing_user = await user_service.user_repo.get_user_by_username(username)
            if existing_user:
                print(f"Error: User '{username}' already exists.")
                return False
            
            # Create new admin user
            user_data = UserCreate(
                username=username,
                email=email,
                password=password,
                full_name=f"Admin User",
                role=UserRole.ADMIN,
                is_active=True
            )
            
            user = await user_service.create_user(user_data)
            await session.commit()
            
            if user:
                print(f"\n✅ Admin user created successfully!")
                print(f"   Username: {username}")
                print(f"   Email: {email}")
                print(f"   Role: ADMIN")
                print(f"\nYou can now login with these credentials.")
                return True
            else:
                print("Failed to create user.")
                return False
                
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        print(f"Error: {e}")
        return False


async def create_default_users():
    """Create default test users for development.

    WARNING: Uses hardcoded passwords for development convenience only.
    Never run in production — use create_admin_user() for real deployments.
    """
    # Safety guard: refuse to run unless --dev-only flag is present
    if "--dev-only" not in sys.argv:
        print("ERROR: create_default_users requires --dev-only flag.")
        print("Usage: python scripts/create_admin_user.py --default --dev-only")
        print("This command is for development environments only.")
        return False

    print("\n=== Creating Default Test Users (DEVELOPMENT ONLY) ===\n")

    default_users = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "Admin123456!",
            "full_name": "Admin User",
            "role": UserRole.ADMIN
        },
        {
            "username": "operator",
            "email": "operator@example.com",
            "password": "Operator123!",
            "full_name": "Operator User",
            "role": UserRole.OPERATOR
        },
        {
            "username": "viewer",
            "email": "viewer@example.com",
            "password": "Viewer123!",
            "full_name": "Viewer User",
            "role": UserRole.VIEWER
        }
    ]
    
    try:
        # Initialize database if needed
        await init_database()
        
        async with AsyncSessionLocal() as session:
            user_service = UserManagementService(session)
            
            for user_data_dict in default_users:
                # Check if user already exists
                existing_user = await user_service.user_repo.get_user_by_username(user_data_dict["username"])
                if existing_user:
                    print(f"⚠️  User '{user_data_dict['username']}' already exists, skipping...")
                    continue
                
                # Create user
                user_data = UserCreate(**user_data_dict, is_active=True)
                user = await user_service.create_user(user_data)
                
                if user:
                    print(f"✅ Created user: {user_data_dict['username']} (Role: {user_data_dict['role']})")
                else:
                    print(f"❌ Failed to create user: {user_data_dict['username']}")
            
            await session.commit()
            print("\n=== Default Users Created ===")
            print("\nDefault login credentials:")
            print("  Admin:    admin / Admin123456!")
            print("  Operator: operator / Operator123!")
            print("  Viewer:   viewer / Viewer123!")
            print("\n⚠️  WARNING: Change these passwords in production!")
            
    except Exception as e:
        logger.error(f"Error creating default users: {e}")
        print(f"Error: {e}")
        return False
    
    return True


def main():
    """Main entry point."""
    if "--default" in sys.argv:
        # Create default users for development (requires --dev-only flag)
        asyncio.run(create_default_users())
    else:
        # Interactive admin user creation
        asyncio.run(create_admin_user())


if __name__ == "__main__":
    main()