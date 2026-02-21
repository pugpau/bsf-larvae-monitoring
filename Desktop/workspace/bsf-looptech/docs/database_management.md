# Database Management Guide

## Overview
This project uses Alembic for database migrations with SQLAlchemy ORM. The database supports both PostgreSQL (production) and SQLite (development/testing).

## Current Status
- **Current Migration**: `bff9c7856e8b` - Initial migration with all tables
- **Database File**: `bsf_system.db` (SQLite)
- **Tables Created**: 14 core tables including users, sensors, substrates, alerts, and audit logs

## Database Management Script

Use the `scripts/manage_db.py` utility for all database operations:

```bash
# Initialize/upgrade database to latest version
python scripts/manage_db.py init

# Create a new migration
python scripts/manage_db.py create "Migration description"

# Upgrade to latest version
python scripts/manage_db.py upgrade

# Downgrade to previous version
python scripts/manage_db.py downgrade -1

# Show current migration version
python scripts/manage_db.py current

# Show migration history
python scripts/manage_db.py history
```

## Database Schema

### Core Tables Created:

1. **Users & Authentication**
   - `users` - User accounts with roles and permissions
   - `user_sessions` - Active user sessions
   - `login_attempts` - Security audit log
   - `api_keys` - API key management
   - `role_permissions` - Role-based access control
   - `user_farms` - User-farm associations

2. **Sensor Management**
   - `sensor_devices` - IoT sensor device registry
   - `substrate_batches` - BSF substrate batch tracking
   - `substrate_types` - Substrate type definitions
   - `substrate_batch_components` - Batch composition

3. **Monitoring & Alerts**
   - `alert_rules` - Threshold-based alert configuration
   - `anomaly_rules` - ML-based anomaly detection rules
   - `anomaly_detections` - Detected anomalies log

## Migration Files

Migration files are stored in `alembic/versions/` with the naming convention:
- `{revision_id}_{description}.py`

Current migration: `bff9c7856e8b_initial_migration_create_all_tables.py`

## Configuration

### Database URLs
- **SQLite**: `sqlite+aiosqlite:///./bsf_system.db`
- **PostgreSQL**: `postgresql+asyncpg://user:pass@localhost:5432/bsf_system`

### Environment Variables
Set `DATABASE_URL` in `.env` file:
```bash
DATABASE_URL=sqlite+aiosqlite:///./bsf_system.db
```

## Common Operations

### Creating New Migrations
1. Modify models in `src/` directory
2. Run: `python scripts/manage_db.py create "Description of changes"`
3. Review generated migration in `alembic/versions/`
4. Apply migration: `python scripts/manage_db.py upgrade`

### Database Reset (Development)
```bash
# Remove database file
rm bsf_system.db

# Recreate from migrations
python scripts/manage_db.py init
```

### Switching Databases
1. Update `DATABASE_URL` in `.env`
2. Install appropriate database driver:
   - SQLite: `pip install aiosqlite`
   - PostgreSQL: `pip install asyncpg`
3. Run migrations: `python scripts/manage_db.py init`

## Troubleshooting

### Common Issues

1. **"No module named 'aiosqlite'"**
   ```bash
   source venv/bin/activate
   pip install aiosqlite
   ```

2. **PostgreSQL connection errors**
   - Check if PostgreSQL service is running
   - Verify connection string in `.env`
   - Temporarily switch to SQLite for development

3. **Migration conflicts**
   ```bash
   # View current state
   python scripts/manage_db.py current
   python scripts/manage_db.py history
   
   # Resolve conflicts manually or reset database
   ```

## Best Practices

1. **Always backup production data** before applying migrations
2. **Test migrations** on development database first
3. **Review auto-generated migrations** before applying
4. **Use descriptive migration messages**
5. **Keep model changes atomic** - one logical change per migration

## Files Modified/Created

- `alembic.ini` - Alembic configuration
- `alembic/env.py` - Migration environment setup
- `alembic/versions/bff9c7856e8b_*.py` - Initial migration
- `scripts/manage_db.py` - Database management utility
- `bsf_system.db` - SQLite database file