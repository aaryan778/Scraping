# Database Migrations with Alembic

This directory contains database migration scripts for the Job Scraping System.

## Setup

1. Install Alembic (already in requirements.txt):
   ```bash
   pip install alembic
   ```

2. Set your DATABASE_URL environment variable:
   ```bash
   export DATABASE_URL=postgresql://jobscraper:changeme123@localhost:5432/jobs_db
   ```

## Common Commands

### Apply all migrations (upgrade to latest):
```bash
alembic upgrade head
```

### Rollback one migration:
```bash
alembic downgrade -1
```

### Rollback to specific version:
```bash
alembic downgrade 001_add_created_at
```

### View current migration version:
```bash
alembic current
```

### View migration history:
```bash
alembic history
```

### Create a new migration (auto-generate):
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Create a new empty migration:
```bash
alembic revision -m "Description of changes"
```

## Migration Files

- `001_add_created_at_field.py` - Adds created_at column to jobs table with index

## Best Practices

1. **Always review auto-generated migrations** before applying them
2. **Test migrations on development database first**
3. **Create backups** before running migrations in production
4. **Write both upgrade() and downgrade()** functions
5. **Keep migrations small and focused** on one change at a time

## Troubleshooting

### Migration fails with "column already exists"
This means the column was added manually. You can:
1. Remove the column manually: `ALTER TABLE jobs DROP COLUMN created_at;`
2. Or skip this migration: `alembic stamp 001_add_created_at`

### Can't connect to database
Check your DATABASE_URL in `.env` file or environment variables.

### Migration version conflicts
Run `alembic current` to see current version, then upgrade or downgrade as needed.
