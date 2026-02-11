#!/usr/bin/env python3
"""
Simple script to reset admin password directly via SQL.
"""

import asyncio
import sys
import os
import hashlib
import secrets
from typing import Optional

# Add bcrypt for password hashing
import bcrypt

async def reset_admin_password():
    """Reset admin password using direct SQL."""
    
    # Default credentials
    username = "admin"
    email = "admin@example.com"
    password = "Admin123456!"
    
    print(f"\n=== Resetting password for admin user ===")
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"New Password: {password}")
    
    # Hash the password using bcrypt
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    # Connect to database directly
    import asyncpg
    
    try:
        # Create connection
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='bsf_user',
            password='bsf_password',
            database='bsf_system'
        )
        
        # Check if admin exists
        existing = await conn.fetchrow(
            "SELECT id, username, email FROM users WHERE username = $1 OR email = $2",
            username, email
        )
        
        if existing:
            # Update existing admin
            await conn.execute(
                """
                UPDATE users 
                SET hashed_password = $1,
                    updated_at = NOW(),
                    password_changed_at = NOW(),
                    is_active = true,
                    is_verified = true,
                    role = 'admin'
                WHERE username = $2 OR email = $3
                """,
                hashed_password, username, email
            )
            print(f"✅ Password updated for existing admin user (ID: {existing['id']})")
        else:
            # Create new admin
            import uuid
            user_id = str(uuid.uuid4())
            
            await conn.execute(
                """
                INSERT INTO users (
                    id, username, email, hashed_password, full_name,
                    is_active, is_verified, is_superuser, role,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    true, true, false, 'admin',
                    NOW(), NOW()
                )
                """,
                user_id, username, email, hashed_password, "Administrator"
            )
            print(f"✅ Created new admin user (ID: {user_id})")
        
        # Close connection
        await conn.close()
        
        print("\n✅ Admin password reset successfully!")
        print("\nYou can now login with:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(reset_admin_password())