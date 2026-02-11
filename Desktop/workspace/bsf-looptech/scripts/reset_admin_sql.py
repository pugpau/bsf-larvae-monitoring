#!/usr/bin/env python3
"""
Direct SQL password reset using passlib (which should be installed).
"""

from passlib.context import CryptContext

# Create password context (same as used by FastAPI)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash the password
password = "Admin123456!"
hashed = pwd_context.hash(password)

print(f"""
-- SQL to reset admin password
UPDATE users 
SET hashed_password = '{hashed}',
    updated_at = NOW(),
    password_changed_at = NOW(),
    is_active = true,
    is_verified = true
WHERE username = 'admin' OR email = 'admin@example.com';

-- Verify the update
SELECT id, username, email, role, is_active FROM users WHERE username = 'admin';
""")