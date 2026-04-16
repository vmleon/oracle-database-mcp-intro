-- Grants for pdbadmin user in local Oracle FREE container
-- Run this as SYS in FREEPDB1

-- Privileges for Liquibase
GRANT CREATE SESSION TO pdbadmin;
GRANT CREATE TABLE TO pdbadmin;
GRANT CREATE SEQUENCE TO pdbadmin;
GRANT CREATE VIEW TO pdbadmin;
GRANT UNLIMITED TABLESPACE TO pdbadmin;

-- Read-only data dictionary access for DBA / audit demos
-- (v$session, v$sql, user_tables stats, etc.)
GRANT SELECT_CATALOG_ROLE TO pdbadmin;

-- Verify grants
SELECT * FROM dba_sys_privs WHERE grantee = 'PDBADMIN';
SELECT * FROM dba_role_privs WHERE grantee = 'PDBADMIN';
