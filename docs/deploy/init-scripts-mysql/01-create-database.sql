-- MySQL/MariaDB initialization script for IntentVerse
-- This script sets up the database with recommended settings and optimizations

-- Ensure we're using the correct database
USE intentverse;

-- Set session variables for optimal performance
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO';
SET SESSION character_set_client = utf8mb4;
SET SESSION character_set_connection = utf8mb4;
SET SESSION character_set_results = utf8mb4;
SET SESSION collation_connection = utf8mb4_unicode_ci;

-- Create a comment to document the setup
ALTER DATABASE intentverse 
  CHARACTER SET = utf8mb4 
  COLLATE = utf8mb4_unicode_ci 
  COMMENT = 'IntentVerse application database - MySQL/MariaDB backend';

-- Grant additional privileges to the intentverse user
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, CREATE TEMPORARY TABLES, LOCK TABLES 
ON intentverse.* TO 'intentverse_user'@'%';

-- Flush privileges to ensure changes take effect
FLUSH PRIVILEGES;

-- Create some useful views for monitoring (optional)
-- These will be created after tables are set up by the application

-- Log the initialization
SELECT 'IntentVerse MySQL/MariaDB database initialized successfully' AS status;