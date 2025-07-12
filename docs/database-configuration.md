# Database Configuration

IntentVerse supports multiple database engines through a flexible abstraction layer. This document covers configuration options and setup instructions for each supported database type.

## Overview

- **Default:** SQLite (zero configuration)
- **v1.1.0:** SQLite with configuration framework
- **v1.2.0:** PostgreSQL and MySQL support

## Environment Variables

All database configuration is handled through environment variables:

| Variable | Default | Description | Version |
|----------|---------|-------------|---------|
| `INTENTVERSE_DB_TYPE` | `sqlite` | Database engine type (`sqlite`, `postgresql`, `mysql`) | v1.1.0+ |
| `INTENTVERSE_DB_URL` | - | Complete database connection URL (overrides individual params) | v1.1.0+ |
| `INTENTVERSE_DB_HOST` | - | Database server hostname | v1.1.0+ |
| `INTENTVERSE_DB_PORT` | - | Database server port | v1.1.0+ |
| `INTENTVERSE_DB_NAME` | - | Database name | v1.1.0+ |
| `INTENTVERSE_DB_USER` | - | Database username | v1.1.0+ |
| `INTENTVERSE_DB_PASSWORD` | - | Database password | v1.1.0+ |
| `INTENTVERSE_DB_SSL_MODE` | - | SSL connection mode | v1.1.0+ |

## SQLite Configuration

### Default Behavior (v1.0.0+)
SQLite is the default database engine and requires no configuration. IntentVerse will automatically create `intentverse.db` in the working directory.

```bash
# No environment variables needed - SQLite works out of the box
./start-local-dev.sh
```

### Custom SQLite Path (v1.1.0+)
You can specify a custom SQLite database file location:

```bash
export INTENTVERSE_DB_TYPE=sqlite
export INTENTVERSE_DB_URL="sqlite:///path/to/your/database.db"
```

### In-Memory SQLite (Testing)
For testing or temporary usage:

```bash
export INTENTVERSE_DB_TYPE=sqlite
export INTENTVERSE_DB_URL="sqlite:///:memory:"
```

## PostgreSQL Configuration (v1.2.0+)

> **Note:** PostgreSQL support is planned for v1.2.0. The configuration examples below are for future reference and will not work in v1.1.0.

### Prerequisites
- PostgreSQL 12+ server
- Database and user created
- Network connectivity to PostgreSQL server

### Connection URL Method
```bash
export INTENTVERSE_DB_TYPE=postgresql
export INTENTVERSE_DB_URL="postgresql://username:password@hostname:5432/database_name"
```

### Individual Parameters Method
```bash
export INTENTVERSE_DB_TYPE=postgresql
export INTENTVERSE_DB_HOST=localhost
export INTENTVERSE_DB_PORT=5432
export INTENTVERSE_DB_NAME=intentverse
export INTENTVERSE_DB_USER=intentverse_user
export INTENTVERSE_DB_PASSWORD=secure_password
export INTENTVERSE_DB_SSL_MODE=require
```

### SSL Configuration
For secure connections:

```bash
export INTENTVERSE_DB_SSL_MODE=require    # Require SSL
export INTENTVERSE_DB_SSL_MODE=prefer     # Prefer SSL but allow non-SSL
export INTENTVERSE_DB_SSL_MODE=disable    # Disable SSL
```

### Cloud PostgreSQL Examples

#### AWS RDS
```bash
export INTENTVERSE_DB_TYPE=postgresql
export INTENTVERSE_DB_URL="postgresql://username:password@mydb.cluster-xyz.us-east-1.rds.amazonaws.com:5432/intentverse"
export INTENTVERSE_DB_SSL_MODE=require
```

#### Google Cloud SQL
```bash
export INTENTVERSE_DB_TYPE=postgresql
export INTENTVERSE_DB_URL="postgresql://username:password@google-cloud-sql-ip:5432/intentverse"
export INTENTVERSE_DB_SSL_MODE=require
```

#### Azure Database for PostgreSQL
```bash
export INTENTVERSE_DB_TYPE=postgresql
export INTENTVERSE_DB_URL="postgresql://username@servername:password@servername.postgres.database.azure.com:5432/intentverse"
export INTENTVERSE_DB_SSL_MODE=require
```

## MySQL Configuration (v1.2.0+)

> **Note:** MySQL support is planned for v1.2.0. The configuration examples below are for future reference and will not work in v1.1.0.

### Prerequisites
- MySQL 8.0+ or MariaDB 10.5+ server
- Database and user created
- Network connectivity to MySQL server

### Connection URL Method
```bash
export INTENTVERSE_DB_TYPE=mysql
export INTENTVERSE_DB_URL="mysql://username:password@hostname:3306/database_name"
```

### Individual Parameters Method
```bash
export INTENTVERSE_DB_TYPE=mysql
export INTENTVERSE_DB_HOST=localhost
export INTENTVERSE_DB_PORT=3306
export INTENTVERSE_DB_NAME=intentverse
export INTENTVERSE_DB_USER=intentverse_user
export INTENTVERSE_DB_PASSWORD=secure_password
```

### Cloud MySQL Examples

#### AWS RDS MySQL
```bash
export INTENTVERSE_DB_TYPE=mysql
export INTENTVERSE_DB_URL="mysql://username:password@mydb.cluster-xyz.us-east-1.rds.amazonaws.com:3306/intentverse"
```

#### Google Cloud SQL MySQL
```bash
export INTENTVERSE_DB_TYPE=mysql
export INTENTVERSE_DB_URL="mysql://username:password@google-cloud-sql-ip:3306/intentverse"
```

## Database Setup Instructions

### PostgreSQL Setup (v1.2.0+)

1. **Create Database and User:**
```sql
CREATE DATABASE intentverse;
CREATE USER intentverse_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE intentverse TO intentverse_user;
```

2. **Set Environment Variables:**
```bash
export INTENTVERSE_DB_TYPE=postgresql
export INTENTVERSE_DB_HOST=localhost
export INTENTVERSE_DB_PORT=5432
export INTENTVERSE_DB_NAME=intentverse
export INTENTVERSE_DB_USER=intentverse_user
export INTENTVERSE_DB_PASSWORD=secure_password
```

3. **Start IntentVerse:**
```bash
./start-local-dev.sh
```

### MySQL Setup (v1.2.0+)

1. **Create Database and User:**
```sql
CREATE DATABASE intentverse;
CREATE USER 'intentverse_user'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON intentverse.* TO 'intentverse_user'@'%';
FLUSH PRIVILEGES;
```

2. **Set Environment Variables:**
```bash
export INTENTVERSE_DB_TYPE=mysql
export INTENTVERSE_DB_HOST=localhost
export INTENTVERSE_DB_PORT=3306
export INTENTVERSE_DB_NAME=intentverse
export INTENTVERSE_DB_USER=intentverse_user
export INTENTVERSE_DB_PASSWORD=secure_password
```

3. **Start IntentVerse:**
```bash
./start-local-dev.sh
```

## Migration and Data Management (v1.2.0+)

### Automatic Migrations
IntentVerse will automatically handle database schema migrations when starting up with a new database engine.

### Manual Migration Commands
For advanced users, manual migration commands will be available:

```bash
# Check migration status
python -m app.database.migrate status

# Run pending migrations
python -m app.database.migrate upgrade

# Rollback last migration
python -m app.database.migrate downgrade
```

## Troubleshooting

### Common Issues

#### Connection Refused
- Verify database server is running
- Check hostname and port
- Verify firewall settings

#### Authentication Failed
- Verify username and password
- Check user permissions
- Ensure user can connect from IntentVerse host

#### SSL/TLS Issues
- Verify SSL configuration
- Check certificate validity
- Try disabling SSL for testing

### Debugging

Enable debug logging for database operations:

```bash
export INTENTVERSE_LOG_LEVEL=DEBUG
```

Check database connection:

```bash
# Test database connectivity
python -c "
from app.config import Config
from app.database import initialize_database
config = Config.get_database_config()
db = initialize_database(config)
print('Database connection successful!')
"
```

## Performance Considerations

### SQLite
- Best for: Development, testing, small deployments
- Limitations: Single writer, no network access
- Performance: Excellent for read-heavy workloads

### PostgreSQL (v1.2.0+)
- Best for: Production deployments, high concurrency
- Features: Full ACID compliance, advanced indexing
- Performance: Excellent for complex queries

### MySQL (v1.2.0+)
- Best for: Web applications, high-traffic sites
- Features: High performance, proven scalability
- Performance: Excellent for simple queries, high throughput

## Security Best Practices

1. **Use Strong Passwords:** Generate random, complex passwords
2. **Enable SSL:** Always use SSL in production
3. **Limit Network Access:** Use firewalls and VPNs
4. **Regular Backups:** Implement automated backup strategies
5. **Monitor Access:** Log and monitor database connections
6. **Keep Updated:** Regularly update database software

## Version Compatibility

| IntentVerse Version | SQLite | PostgreSQL | MySQL |
|-------------------|--------|------------|-------|
| v1.0.0 | ✅ | ❌ | ❌ |
| v1.1.0 | ✅ | 🚧 (Config only) | 🚧 (Config only) |
| v1.2.0 | ✅ | ✅ | ✅ |

Legend:
- ✅ Fully supported
- 🚧 Configuration framework only (not functional)
- ❌ Not supported