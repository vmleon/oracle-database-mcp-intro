# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Demo project for Oracle Database MCP servers showcasing dual database setup:
- **Local**: Oracle Database FREE container via Podman
- **Cloud**: Oracle Autonomous AI Database 26ai (ADB-S) on OCI

Both databases share identical HR schema (jobs, departments, employees) deployed via Liquibase.

## Common Commands

```bash
# Setup (first time)
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Local database
./manage.py local setup    # Start Podman container + deploy HR schema
./manage.py local clean    # Stop/remove container

# Cloud database (optional)
./manage.py cloud setup    # Interactive OCI config -> terraform.tfvars
cd deploy/terraform && terraform init && terraform apply && cd ../..
./manage.py cloud deploy   # Extract wallet + run Liquibase

# MCP connections
./manage.py mcp setup      # Create SQLcl saved connections (hr_local, hr_cloud)

# Test database connections (use -name flag for saved connections)
sql -name hr_local         # Connect to local database
sql -name hr_cloud         # Connect to cloud database

# Run Liquibase manually
cd database/liquibase && liquibase --password=$LOCAL_DB_PASSWORD update
```

## Architecture

```
manage.py                  # Single orchestration script (~400 lines)
├── local_setup()         # Podman container lifecycle + Liquibase
├── cloud_setup()         # Interactive OCI config via questionary
├── cloud_deploy()        # Wallet extraction + Liquibase
└── mcp_setup()           # SQLcl saved connections

database/
├── liquibase/            # Schema definitions
│   ├── liquibase.properties          # Local DB config
│   ├── liquibase.cloud.properties.j2 # Cloud template (Jinja2)
│   └── changelog/001-hr-schema.yaml  # Tables + sample data
└── scripts/local_pdb_grant.sql       # PDB privileges

deploy/terraform/         # ADB-S infrastructure
├── adb.tf               # Autonomous Database resource (23ai)
├── wallet.tf            # Downloads wallet to database/wallet/
└── terraform.tfvars.j2  # Template for cloud setup
```

## Key Details

- Credentials stored in `.env` (gitignored): `LOCAL_DB_PASSWORD`, `CLOUD_DB_PASSWORD`, `CLOUD_TNS_ALIAS`
- Container name: `odb_hr_mcp`, image: `container-registry.oracle.com/database/free:latest`
- Local connection: `pdbadmin@localhost:1521/FREEPDB1`
- Cloud connection uses wallet in `database/wallet/`
- SQLcl MCP server permissions configured in `.claude/settings.local.json`

## Prerequisites

- Podman (local DB)
- SQLcl 25.2+ (MCP server)
- Liquibase
- Java 17 or 21
- Terraform + OCI CLI (cloud only)

## Git Commits

- Do not include Co-Authored-By lines or any Claude references in commit messages
- Keep commit messages concise and focused on the change
