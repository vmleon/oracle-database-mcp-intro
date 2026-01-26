#!/usr/bin/env python3
"""Oracle Database MCP Demo - Management Script"""

import argparse
import configparser
import os
import secrets
import shutil
import string
import subprocess
import sys
import time
import zipfile
from pathlib import Path

try:
    import questionary
    from jinja2 import Template
    from dotenv import load_dotenv, set_key
except ImportError:
    print("Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.resolve()
ENV_FILE = BASE_DIR / ".env"
WALLET_DIR = BASE_DIR / "database" / "wallet"
LIQUIBASE_DIR = BASE_DIR / "database" / "liquibase"
TERRAFORM_DIR = BASE_DIR / "deploy" / "terraform"

CONTAINER_NAME = "odb_hr_mcp"
CONTAINER_IMAGE = "container-registry.oracle.com/database/free:latest"
LOCAL_PORT = 1521


def check_command(cmd: str) -> bool:
    """Check if a command exists."""
    return shutil.which(cmd) is not None


def run(cmd: list[str], check: bool = True, capture: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Run a command."""
    print(f"  > {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, **kwargs)


def generate_password(length: int = 16) -> str:
    """Generate a secure password."""
    chars = string.ascii_letters + string.digits + "#_"
    while True:
        pwd = ''.join(secrets.choice(chars) for _ in range(length))
        if (any(c.isupper() for c in pwd) and
            any(c.islower() for c in pwd) and
            any(c.isdigit() for c in pwd) and
            any(c in "#_" for c in pwd)):
            return pwd


def load_env():
    """Load environment variables from .env file."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)


def save_env(key: str, value: str):
    """Save a key to .env file."""
    if not ENV_FILE.exists():
        ENV_FILE.touch()
    set_key(str(ENV_FILE), key, value)


def get_env(key: str, default: str = None) -> str:
    """Get environment variable."""
    load_env()
    return os.getenv(key, default)


# =============================================================================
# LOCAL DATABASE COMMANDS
# =============================================================================

def local_setup():
    """Set up local Oracle FREE container and deploy schema."""
    print("\n=== Local Database Setup ===\n")

    # Check prerequisites
    for cmd in ["podman", "liquibase"]:
        if not check_command(cmd):
            print(f"Error: {cmd} not found. Please install it first.")
            sys.exit(1)

    # Generate password if not exists
    password = get_env("LOCAL_DB_PASSWORD")
    if not password:
        password = generate_password()
        save_env("LOCAL_DB_PASSWORD", password)
        print(f"Generated database password (saved to .env)")

    # Check if container exists
    result = run(["podman", "ps", "-a", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
                 capture=True, check=False)

    if CONTAINER_NAME in result.stdout:
        print(f"Container {CONTAINER_NAME} already exists. Starting if stopped...")
        run(["podman", "start", CONTAINER_NAME], check=False)
    else:
        print(f"Creating container {CONTAINER_NAME}...")
        run([
            "podman", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{LOCAL_PORT}:1521",
            "-e", f"ORACLE_PWD={password}",
            CONTAINER_IMAGE
        ])

    # Wait for database to be ready by checking logs
    print("\nWaiting for database to be ready (this may take a few minutes)...")
    max_attempts = 60
    for i in range(max_attempts):
        result = run(
            ["podman", "logs", CONTAINER_NAME],
            capture=True, check=False
        )
        if "DATABASE IS READY TO USE" in result.stdout:
            print("Database is ready!")
            break
        time.sleep(5)
        print(f"  Waiting... ({i+1}/{max_attempts})")
    else:
        print("Timeout waiting for database. Check container logs with: podman logs " + CONTAINER_NAME)
        sys.exit(1)

    # Run grants
    print("\nRunning PDB grants...")
    grant_sql = (BASE_DIR / "database" / "scripts" / "local_pdb_grant.sql").read_text()
    run(
        ["podman", "exec", "-i", CONTAINER_NAME, "sqlplus", "-s", "sys/"+password+"@FREEPDB1 as sysdba"],
        input=grant_sql,
        capture=True
    )

    # Run Liquibase
    print("\nRunning Liquibase migration...")
    os.chdir(LIQUIBASE_DIR)
    run(["liquibase", f"--password={password}", "update"])
    os.chdir(BASE_DIR)

    print("\n=== Local setup complete! ===")
    print(f"Connection: localhost:{LOCAL_PORT}/FREEPDB1")
    print(f"User: pdbadmin / Password in .env")


def local_clean():
    """Stop and remove local container."""
    print("\n=== Cleaning Local Database ===\n")

    if not check_command("podman"):
        print("Error: podman not found")
        sys.exit(1)

    run(["podman", "stop", CONTAINER_NAME], check=False)
    run(["podman", "rm", CONTAINER_NAME], check=False)

    # Remove password from .env
    if ENV_FILE.exists():
        save_env("LOCAL_DB_PASSWORD", "")

    print("\nLocal database cleaned up.")


# =============================================================================
# CLOUD DATABASE COMMANDS
# =============================================================================

def get_oci_profiles():
    """Get list of available OCI profiles from ~/.oci/config."""
    config_path = Path.home() / ".oci" / "config"
    if not config_path.exists():
        return ["DEFAULT"]

    config = configparser.ConfigParser()
    config.read(config_path)

    profiles = config.sections()
    # ConfigParser doesn't include DEFAULT by default, check manually
    if config.defaults():
        profiles.insert(0, "DEFAULT")

    return profiles if profiles else ["DEFAULT"]


def read_oci_config(profile="DEFAULT"):
    """Read OCI config for specified profile."""
    config_path = Path.home() / ".oci" / "config"
    if not config_path.exists():
        return {}

    config = configparser.ConfigParser()
    config.read(config_path)

    if profile == "DEFAULT":
        return dict(config.defaults())
    elif profile in config:
        return dict(config[profile])
    return {}


def select_compartment(config_file_profile: str, tenancy_ocid: str) -> str:
    """Interactive compartment selection."""
    import oci
    try:
        config = oci.config.from_file(profile_name=config_file_profile)
        identity_client = oci.identity.IdentityClient(config)

        compartments = []

        # Add root compartment (tenancy)
        tenancy = identity_client.get_tenancy(tenancy_ocid).data
        compartments.append({
            "name": f"{tenancy.name} (root)",
            "id": tenancy.id
        })

        # Add child compartments
        list_response = identity_client.list_compartments(
            compartment_id=tenancy_ocid,
            compartment_id_in_subtree=True,
            lifecycle_state="ACTIVE"
        )

        for comp in list_response.data:
            compartments.append({
                "name": comp.name,
                "id": comp.id
            })

        if compartments:
            choices = [c["name"] for c in compartments]
            selected = questionary.select("Select Compartment:", choices=choices).ask()
            return next(c["id"] for c in compartments if c["name"] == selected)
        else:
            return questionary.text("Compartment OCID:").ask()

    except Exception as e:
        print(f"Error listing compartments: {e}")
        return questionary.text("Compartment OCID:").ask()


def select_region(config_file_profile: str, current_region: str) -> str:
    """Interactive region selection."""
    import oci
    try:
        config = oci.config.from_file(profile_name=config_file_profile)
        identity_client = oci.identity.IdentityClient(config)
        regions_response = identity_client.list_regions()

        regions = []
        for region in regions_response.data:
            regions.append({
                "name": region.name,
                "display": f"{region.name} ({region.key})"
            })

        regions.sort(key=lambda x: x["name"])

        if regions:
            choices = [r["display"] for r in regions]
            default = next(
                (r["display"] for r in regions if r["name"] == current_region),
                choices[0]
            )
            selected = questionary.select(
                "Select Region:",
                choices=choices,
                default=default
            ).ask()
            return next(r["name"] for r in regions if r["display"] == selected)
        else:
            return questionary.text("Region:", default=current_region).ask()

    except Exception as e:
        print(f"Error listing regions: {e}")
        return questionary.text("Region:", default=current_region).ask()


def cloud_setup():
    """Interactive setup for OCI configuration."""
    print("\n=== Cloud Database Setup ===\n")

    # Check prerequisites
    if not check_command("terraform"):
        print("Error: terraform not found. Please install it first.")
        sys.exit(1)

    config_path = Path.home() / ".oci" / "config"
    if not config_path.exists():
        print("Error: OCI configuration not found at ~/.oci/config")
        print("Run: oci setup config")
        sys.exit(1)

    try:
        import oci
    except ImportError:
        print("Error: oci package not found. Run: pip install oci")
        sys.exit(1)

    # Select OCI profile
    profiles = get_oci_profiles()
    config_file_profile = questionary.select(
        "Select OCI Profile:",
        choices=profiles,
        default="DEFAULT" if "DEFAULT" in profiles else profiles[0]
    ).ask()

    # Read config for selected profile
    oci_config = read_oci_config(config_file_profile)
    tenancy_ocid = oci_config.get("tenancy")
    if not tenancy_ocid:
        print(f"Error: No tenancy OCID found in profile '{config_file_profile}'")
        sys.exit(1)

    print(f"Using tenancy: {tenancy_ocid[:40]}...")

    # Interactive compartment selection
    compartment_ocid = select_compartment(config_file_profile, tenancy_ocid)

    # Interactive region selection
    current_region = oci_config.get("region", "us-ashburn-1")
    region = select_region(config_file_profile, current_region)

    # ECPU count
    ecpu = questionary.text("ECPU count:", default="2").ask()

    # Generate terraform.tfvars
    template = Template((TERRAFORM_DIR / "terraform.tfvars.j2").read_text())
    tfvars = template.render(
        tenancy_ocid=tenancy_ocid,
        compartment_ocid=compartment_ocid,
        region=region,
        config_file_profile=config_file_profile,
        ecpu_count=ecpu
    )

    tfvars_path = TERRAFORM_DIR / "terraform.tfvars"
    tfvars_path.write_text(tfvars)

    print(f"\nGenerated {tfvars_path}")
    print("\nNext steps:")
    print("  cd deploy/terraform")
    print("  terraform init")
    print("  terraform plan -out=tfplan")
    print("  terraform apply tfplan")
    print("  cd ../..")
    print("  ./manage.py cloud deploy")


def cloud_deploy():
    """Extract wallet and run Liquibase for cloud database."""
    print("\n=== Cloud Database Deploy ===\n")

    wallet_zip = WALLET_DIR / "wallet.zip"
    if not wallet_zip.exists():
        print("Error: wallet.zip not found. Run terraform apply first.")
        sys.exit(1)

    # Extract wallet
    print("Extracting wallet...")
    with zipfile.ZipFile(wallet_zip, 'r') as z:
        z.extractall(WALLET_DIR)

    # Get terraform outputs
    os.chdir(TERRAFORM_DIR)
    result = run(["terraform", "output", "-raw", "admin_password"], capture=True)
    admin_password = result.stdout.strip()

    result = run(["terraform", "output", "-raw", "tns_alias_low"], capture=True)
    tns_alias = result.stdout.strip()

    result = run(["terraform", "output", "-raw", "wallet_password"], capture=True)
    wallet_password = result.stdout.strip()
    os.chdir(BASE_DIR)

    # Save cloud credentials to .env
    save_env("CLOUD_DB_PASSWORD", admin_password)
    save_env("CLOUD_TNS_ALIAS", tns_alias)
    save_env("CLOUD_WALLET_PASSWORD", wallet_password)

    # Configure wallet to use JKS instead of SSO (required for Liquibase/JDBC)
    print("Configuring wallet for JKS...")
    ojdbc_props = WALLET_DIR / "ojdbc.properties"
    ojdbc_content = f"""# JKS configuration for Liquibase/JDBC
javax.net.ssl.trustStore=${{TNS_ADMIN}}/truststore.jks
javax.net.ssl.trustStorePassword={wallet_password}
javax.net.ssl.keyStore=${{TNS_ADMIN}}/keystore.jks
javax.net.ssl.keyStorePassword={wallet_password}
"""
    ojdbc_props.write_text(ojdbc_content)

    # Generate cloud liquibase properties
    template = Template((LIQUIBASE_DIR / "liquibase.cloud.properties.j2").read_text())
    props = template.render(
        tns_alias=tns_alias,
        wallet_dir=str(WALLET_DIR),
        admin_password=admin_password
    )

    cloud_props = LIQUIBASE_DIR / "liquibase.cloud.properties"
    cloud_props.write_text(props)

    # Run Liquibase
    print("\nRunning Liquibase migration...")
    os.chdir(LIQUIBASE_DIR)
    run(["liquibase", f"--defaults-file=liquibase.cloud.properties", "update"])
    os.chdir(BASE_DIR)

    print("\n=== Cloud deploy complete! ===")
    print(f"TNS Alias: {tns_alias}")
    print("Password saved to .env")


def cloud_clean():
    """Clean up generated cloud files."""
    print("\n=== Cleaning Cloud Files ===\n")

    # Remove wallet directory contents
    if WALLET_DIR.exists():
        shutil.rmtree(WALLET_DIR)
        print("Removed wallet directory")

    # Remove generated liquibase properties
    cloud_props = LIQUIBASE_DIR / "liquibase.cloud.properties"
    if cloud_props.exists():
        cloud_props.unlink()
        print("Removed liquibase.cloud.properties")

    # Remove terraform tfvars
    tfvars = TERRAFORM_DIR / "terraform.tfvars"
    if tfvars.exists():
        tfvars.unlink()
        print("Removed terraform.tfvars")

    print("\nCloud files cleaned up.")
    print("Note: To destroy cloud resources, run: cd deploy/terraform && terraform destroy")


# =============================================================================
# MCP CONFIGURATION
# =============================================================================

def mcp_setup():
    """Configure SQLcl saved connections for MCP."""
    import tempfile

    print("\n=== MCP Setup ===\n")

    if not check_command("sql"):
        print("Error: sqlcl (sql) not found. Please install it first.")
        sys.exit(1)

    load_env()

    # Local connection
    local_password = os.getenv("LOCAL_DB_PASSWORD")
    if local_password:
        print("Creating local connection: hr_local")
        conn_str = f"pdbadmin/{local_password}@localhost:{LOCAL_PORT}/FREEPDB1"

        # Create temp SQL file (delete existing first, then create)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("connmgr delete -conn hr_local\n")
            f.write(f"conn -save hr_local -savepwd {conn_str}\n")
            f.write("exit\n")
            temp_file = f.name

        try:
            subprocess.run(["sql", "/nolog", f"@{temp_file}"], check=False)
        finally:
            os.unlink(temp_file)
    else:
        print("Skipping local connection (no password in .env)")

    # Cloud connection
    cloud_password = os.getenv("CLOUD_DB_PASSWORD")
    cloud_tns = os.getenv("CLOUD_TNS_ALIAS")
    if cloud_password and cloud_tns:
        print("Creating cloud connection: hr_cloud")
        wallet_opt = f"?TNS_ADMIN={WALLET_DIR}"
        conn_str = f"ADMIN/{cloud_password}@{cloud_tns}{wallet_opt}"

        # Create temp SQL file (delete existing first, then create)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("connmgr delete -conn hr_cloud\n")
            f.write(f"conn -save hr_cloud -savepwd {conn_str}\n")
            f.write("exit\n")
            temp_file = f.name

        try:
            subprocess.run(["sql", "/nolog", f"@{temp_file}"], check=False)
        finally:
            os.unlink(temp_file)
    else:
        print("Skipping cloud connection (no credentials in .env)")

    print("\n=== MCP setup complete! ===")
    print("Test connections with: sql -name hr_local or sql -name hr_cloud")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Oracle Database MCP Demo Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Local commands
    local_parser = subparsers.add_parser("local", help="Local database commands")
    local_sub = local_parser.add_subparsers(dest="action", required=True)
    local_sub.add_parser("setup", help="Set up local Oracle FREE container")
    local_sub.add_parser("clean", help="Stop and remove local container")

    # Cloud commands
    cloud_parser = subparsers.add_parser("cloud", help="Cloud database commands")
    cloud_sub = cloud_parser.add_subparsers(dest="action", required=True)
    cloud_sub.add_parser("setup", help="Interactive OCI configuration")
    cloud_sub.add_parser("deploy", help="Extract wallet and run Liquibase")
    cloud_sub.add_parser("clean", help="Remove generated files")

    # MCP commands
    mcp_parser = subparsers.add_parser("mcp", help="MCP configuration")
    mcp_sub = mcp_parser.add_subparsers(dest="action", required=True)
    mcp_sub.add_parser("setup", help="Configure SQLcl saved connections")

    args = parser.parse_args()

    if args.command == "local":
        if args.action == "setup":
            local_setup()
        elif args.action == "clean":
            local_clean()
    elif args.command == "cloud":
        if args.action == "setup":
            cloud_setup()
        elif args.action == "deploy":
            cloud_deploy()
        elif args.action == "clean":
            cloud_clean()
    elif args.command == "mcp":
        if args.action == "setup":
            mcp_setup()


if __name__ == "__main__":
    main()
