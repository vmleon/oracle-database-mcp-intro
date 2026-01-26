-- Grants for pdbadmin user in local Oracle FREE container
-- Run this as SYS in FREEPDB1

-- Grant necessary privileges for Liquibase
GRANT CREATE SESSION TO pdbadmin;
GRANT CREATE TABLE TO pdbadmin;
GRANT CREATE SEQUENCE TO pdbadmin;
GRANT CREATE VIEW TO pdbadmin;
GRANT UNLIMITED TABLESPACE TO pdbadmin;

-- Verify grants
SELECT * FROM dba_sys_privs WHERE grantee = 'PDBADMIN';
