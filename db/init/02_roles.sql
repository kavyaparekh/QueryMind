-- Create the read-only role used for all user-facing query execution.
-- This role can only SELECT; it cannot INSERT, UPDATE, DELETE, or DDL.
--
-- Password is intentionally hardcoded for local dev.  In production,
-- rotate via a secrets manager and set READONLY_DATABASE_URL accordingly.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'querymind_ro') THEN
        CREATE ROLE querymind_ro WITH LOGIN PASSWORD 'querymind_ro_pass';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE querymind TO querymind_ro;
GRANT USAGE ON SCHEMA public TO querymind_ro;

-- Auto-grant SELECT on any table the querymind user creates in the future.
-- This covers Chinook tables created by the seed script (db/seed.py).
ALTER DEFAULT PRIVILEGES FOR ROLE querymind IN SCHEMA public
    GRANT SELECT ON TABLES TO querymind_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE querymind IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO querymind_ro;
