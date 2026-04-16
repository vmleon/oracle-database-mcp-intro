#!/usr/bin/env python3
"""Oracle Database MCP Demo - Management Script"""

import configparser
import json
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

try:
    import click
    from dotenv import load_dotenv, set_key
    from InquirerPy import inquirer
    from jinja2 import Template
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)

console = Console()

BASE_DIR = Path(__file__).parent.resolve()
ENV_FILE = BASE_DIR / ".env"
WALLET_DIR = BASE_DIR / "database" / "wallet"
LIQUIBASE_DIR = BASE_DIR / "database" / "liquibase"
TERRAFORM_DIR = BASE_DIR / "deploy" / "terraform"

CONTAINER_NAME = "odb_hr_mcp"
CONTAINER_IMAGE = "container-registry.oracle.com/database/free:latest"
LOCAL_PORT = 1521


# =============================================================================
# HELPERS
# =============================================================================

def check_command(cmd: str) -> bool:
    """Check if a command exists."""
    return shutil.which(cmd) is not None


def run(cmd: list[str], check: bool = True, capture: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Run a command."""
    console.print(f"  > {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, **kwargs)


def _check_version(cmd: str, args: list[str], name: str, min_major: int) -> bool:
    """Check that a command is installed and meets minimum major version."""
    try:
        result = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        match = re.search(r"(\d+)\.\d+", output)
        if not match:
            console.print(f"[red]Error:[/red] Could not parse {name} version from: {output.strip()}")
            return False
        major = int(match.group(1))
        if major < min_major:
            console.print(f"[red]Error:[/red] {name} {major} found, need {min_major}+")
            return False
        console.print(f"  {name} {match.group(0)} [green]OK[/green]")
        return True
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] {name} not found. Install {name} {min_major}+ and try again.")
        return False


def _check_java() -> bool:
    return _check_version("java", ["--version"], "Java", 17)


def generate_password(length: int = 20) -> str:
    """Generate Oracle-compliant password (starts with letter, 2+ specials, 2+ digits)."""
    letters = string.ascii_letters
    digits = string.digits
    specials = "#_"

    password = [secrets.choice(letters)]
    password.append(secrets.choice(specials))
    password.append(secrets.choice(specials))
    password.append(secrets.choice(digits))
    password.append(secrets.choice(digits))

    alphabet = letters + digits + specials
    for _ in range(length - 5):
        password.append(secrets.choice(alphabet))

    tail = password[1:]
    secrets.SystemRandom().shuffle(tail)
    password[1:] = tail
    return "".join(password)


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
    console.print("\n[bold]Local Database Setup[/bold]\n")

    for cmd in ["podman", "liquibase"]:
        if not check_command(cmd):
            console.print(f"[red]Error:[/red] {cmd} not found. Please install it first.")
            sys.exit(1)

    if not _check_java():
        sys.exit(1)

    password = get_env("LOCAL_DB_PASSWORD")
    if not password:
        password = generate_password()
        save_env("LOCAL_DB_PASSWORD", password)
        console.print("Generated database password (saved to .env)")

    result = run(["podman", "ps", "-a", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
                 capture=True, check=False)

    if CONTAINER_NAME in result.stdout:
        console.print(f"Container {CONTAINER_NAME} already exists. Starting if stopped...")
        run(["podman", "start", CONTAINER_NAME], check=False)
    else:
        console.print(f"Creating container {CONTAINER_NAME}...")
        run([
            "podman", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{LOCAL_PORT}:1521",
            "-e", f"ORACLE_PWD={password}",
            CONTAINER_IMAGE
        ])

    console.print("\nWaiting for database to be ready (this may take a few minutes)...")
    max_attempts = 60
    for i in range(max_attempts):
        result = run(
            ["podman", "logs", CONTAINER_NAME],
            capture=True, check=False
        )
        if "DATABASE IS READY TO USE" in result.stdout:
            console.print("[green]Database is ready![/green]")
            break
        time.sleep(5)
        console.print(f"  Waiting... ({i+1}/{max_attempts})")
    else:
        console.print(f"[red]Timeout waiting for database.[/red] Check: podman logs {CONTAINER_NAME}")
        sys.exit(1)

    console.print("\nRunning PDB grants...")
    grant_sql = (BASE_DIR / "database" / "scripts" / "local_pdb_grant.sql").read_text()
    run(
        ["podman", "exec", "-i", CONTAINER_NAME, "sqlplus", "-s", "sys/"+password+"@FREEPDB1 as sysdba"],
        input=grant_sql,
        capture=True
    )

    console.print("\nRunning Liquibase migration...")
    os.chdir(LIQUIBASE_DIR)
    run(["liquibase", f"--password={password}", "update"])
    os.chdir(BASE_DIR)

    console.print("\n[bold green]Local setup complete![/bold green]")
    console.print(f"Connection: localhost:{LOCAL_PORT}/FREEPDB1")
    console.print("User: pdbadmin / Password in .env")


def local_clean():
    """Stop and remove local container."""
    console.print("\n[bold]Cleaning Local Database[/bold]\n")

    if not check_command("podman"):
        console.print("[red]Error:[/red] podman not found")
        sys.exit(1)

    run(["podman", "stop", CONTAINER_NAME], check=False)
    run(["podman", "rm", CONTAINER_NAME], check=False)

    if ENV_FILE.exists():
        save_env("LOCAL_DB_PASSWORD", "")

    console.print("\n[green]Local database cleaned up.[/green]")


# =============================================================================
# CLOUD DATABASE COMMANDS
# =============================================================================

def _read_oci_config():
    """Return (profile list, ConfigParser) from ~/.oci/config."""
    config_path = Path.home() / ".oci" / "config"
    if not config_path.exists():
        return ["DEFAULT"], None

    config = configparser.ConfigParser()
    config.read(config_path)

    profiles = list(config.sections())
    if config.defaults():
        profiles.insert(0, "DEFAULT")
    return profiles or ["DEFAULT"], config


def _get_profile_config(parser, profile: str) -> dict:
    """Return dict of settings for a profile."""
    if parser is None:
        return {}
    if profile == "DEFAULT":
        return dict(parser.defaults())
    if profile in parser:
        return dict(parser[profile])
    return {}


def _list_regions(oci_config: dict):
    """List regions the tenancy is subscribed to; mark the home region."""
    import oci  # lazy import
    try:
        identity_client = oci.identity.IdentityClient(oci_config)
        tenancy_id = oci_config["tenancy"]

        tenancy = identity_client.get_tenancy(tenancy_id).data
        home_key = tenancy.home_region_key

        subs = identity_client.list_region_subscriptions(tenancy_id).data
        regions = [
            {"name": sub.region_name, "is_home": sub.region_key == home_key}
            for sub in subs
        ]
        regions.sort(key=lambda r: (not r["is_home"], r["name"]))
        return regions
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not fetch regions: {e}")
        return None


def _list_compartments(oci_config: dict):
    """List all accessible ACTIVE compartments across pages, root first."""
    import oci  # lazy import
    try:
        identity_client = oci.identity.IdentityClient(oci_config)
        tenancy_id = oci_config["tenancy"]

        tenancy = identity_client.get_compartment(tenancy_id).data
        compartments = [{"name": f"{tenancy.name} (root)", "id": tenancy_id}]

        response = oci.pagination.list_call_get_all_results(
            identity_client.list_compartments,
            compartment_id=tenancy_id,
            compartment_id_in_subtree=True,
            access_level="ACCESSIBLE",
        )
        for comp in response.data:
            if comp.lifecycle_state == "ACTIVE":
                compartments.append({"name": comp.name, "id": comp.id})
        return compartments
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not fetch compartments: {e}")
        return None


def cloud_setup():
    """Interactive setup for OCI configuration."""
    console.print("\n[bold]Cloud Database Setup[/bold]\n")

    if not check_command("terraform"):
        console.print("[red]Error:[/red] terraform not found. Please install it first.")
        sys.exit(1)

    if not (Path.home() / ".oci" / "config").exists():
        console.print("[red]Error:[/red] OCI configuration not found at ~/.oci/config")
        console.print("Run: oci setup config")
        sys.exit(1)

    try:
        import oci  # noqa: F401
    except ImportError:
        console.print("[red]Error:[/red] oci package not found. Run: pip install oci")
        sys.exit(1)

    profiles, parser = _read_oci_config()
    profile = inquirer.select(
        message="OCI profile:",
        choices=profiles,
        default=profiles[0],
    ).execute()

    profile_config = _get_profile_config(parser, profile)
    tenancy_ocid = profile_config.get("tenancy")
    if not tenancy_ocid:
        console.print(f"[red]Error:[/red] No tenancy OCID in profile '{profile}'")
        sys.exit(1)

    sdk_config = {
        "user": profile_config.get("user"),
        "fingerprint": profile_config.get("fingerprint"),
        "key_file": profile_config.get("key_file"),
        "tenancy": tenancy_ocid,
        "region": profile_config.get("region", "us-ashburn-1"),
    }

    # Region selection (subscribed only, home region first)
    console.print("\nFetching subscribed regions...")
    regions = _list_regions(sdk_config)
    if regions:
        choices = [
            f"{r['name']} (home)" if r["is_home"] else r["name"]
            for r in regions
        ]
        selected = inquirer.select(
            message="Region:",
            choices=choices,
            default=choices[0],
        ).execute()
        region = selected.replace(" (home)", "")
    else:
        region = inquirer.text(message="Region:", default=sdk_config["region"]).execute()
    sdk_config["region"] = region

    # Compartment selection (fuzzy, paginated, accessible only)
    console.print("\nFetching compartments...")
    compartments = _list_compartments(sdk_config)
    if compartments:
        choices = [c["name"] for c in compartments]
        comp_map = {c["name"]: c["id"] for c in compartments}
        selected = inquirer.fuzzy(
            message="Compartment (type to search):",
            choices=choices,
        ).execute()
        compartment_ocid = comp_map[selected]
    else:
        compartment_ocid = inquirer.text(message="Compartment OCID:").execute()

    ecpu = inquirer.text(message="ECPU count:", default="2").execute()

    console.print()
    console.print(Panel(
        f"Profile:      {profile}\n"
        f"Tenancy:      {tenancy_ocid}\n"
        f"Region:       {region}\n"
        f"Compartment:  {compartment_ocid}\n"
        f"ECPU count:   {ecpu}",
        title="Configuration Summary",
    ))

    if not inquirer.confirm(message="Save configuration?", default=True).execute():
        console.print("[yellow]Setup cancelled.[/yellow]")
        sys.exit(0)

    template = Template((TERRAFORM_DIR / "terraform.tfvars.j2").read_text())
    tfvars = template.render(
        tenancy_ocid=tenancy_ocid,
        compartment_ocid=compartment_ocid,
        region=region,
        config_file_profile=profile,
        ecpu_count=ecpu,
    )

    tfvars_path = TERRAFORM_DIR / "terraform.tfvars"
    tfvars_path.write_text(tfvars)

    console.print(f"\n[green]Generated[/green] {tfvars_path}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  cd deploy/terraform")
    console.print("  terraform init")
    console.print("  terraform plan -out=tfplan")
    console.print("  terraform apply tfplan")
    console.print("  cd ../..")
    console.print("  ./manage.py cloud deploy")


def cloud_deploy():
    """Extract wallet and run Liquibase for cloud database."""
    console.print("\n[bold]Cloud Database Deploy[/bold]\n")

    if not _check_java():
        sys.exit(1)

    wallet_zip = WALLET_DIR / "wallet.zip"
    if not wallet_zip.exists():
        console.print("[red]Error:[/red] wallet.zip not found. Run terraform apply first.")
        sys.exit(1)

    console.print("Extracting wallet...")
    with zipfile.ZipFile(wallet_zip, 'r') as z:
        z.extractall(WALLET_DIR)

    os.chdir(TERRAFORM_DIR)
    admin_password = run(["terraform", "output", "-raw", "admin_password"], capture=True).stdout.strip()
    tns_alias = run(["terraform", "output", "-raw", "tns_alias_low"], capture=True).stdout.strip()
    wallet_password = run(["terraform", "output", "-raw", "wallet_password"], capture=True).stdout.strip()
    os.chdir(BASE_DIR)

    save_env("CLOUD_DB_PASSWORD", admin_password)
    save_env("CLOUD_TNS_ALIAS", tns_alias)
    save_env("CLOUD_WALLET_PASSWORD", wallet_password)

    console.print("Configuring wallet for JKS...")
    ojdbc_props = WALLET_DIR / "ojdbc.properties"
    ojdbc_content = f"""# JKS configuration for Liquibase/JDBC
javax.net.ssl.trustStore=${{TNS_ADMIN}}/truststore.jks
javax.net.ssl.trustStorePassword={wallet_password}
javax.net.ssl.keyStore=${{TNS_ADMIN}}/keystore.jks
javax.net.ssl.keyStorePassword={wallet_password}
"""
    ojdbc_props.write_text(ojdbc_content)

    template = Template((LIQUIBASE_DIR / "liquibase.cloud.properties.j2").read_text())
    props = template.render(
        tns_alias=tns_alias,
        wallet_dir=str(WALLET_DIR),
        admin_password=admin_password,
    )

    cloud_props = LIQUIBASE_DIR / "liquibase.cloud.properties"
    cloud_props.write_text(props)

    console.print("\nRunning Liquibase migration...")
    os.chdir(LIQUIBASE_DIR)
    run(["liquibase", "--defaults-file=liquibase.cloud.properties", "update"])
    os.chdir(BASE_DIR)

    console.print("\n[bold green]Cloud deploy complete![/bold green]")
    console.print(f"TNS Alias: {tns_alias}")
    console.print("Password saved to .env")


def cloud_clean():
    """Clean up generated cloud files. Refuses if terraform state has resources."""
    console.print("\n[bold]Cleaning Cloud Files[/bold]\n")

    tf_state = TERRAFORM_DIR / "terraform.tfstate"
    if tf_state.exists():
        try:
            state = json.loads(tf_state.read_text())
            has_resources = len(state.get("resources", [])) > 0
        except (json.JSONDecodeError, KeyError):
            has_resources = True

        if has_resources:
            console.print("[yellow]Terraform state has active resources.[/yellow]")
            console.print("Destroy infrastructure first:\n")
            console.print("  cd deploy/terraform")
            console.print("  terraform destroy\n")
            console.print("Then re-run: [bold]./manage.py cloud clean[/bold]")
            return

    if WALLET_DIR.exists():
        shutil.rmtree(WALLET_DIR)
        console.print("Removed wallet directory")

    cloud_props = LIQUIBASE_DIR / "liquibase.cloud.properties"
    if cloud_props.exists():
        cloud_props.unlink()
        console.print("Removed liquibase.cloud.properties")

    tfvars = TERRAFORM_DIR / "terraform.tfvars"
    if tfvars.exists():
        tfvars.unlink()
        console.print("Removed terraform.tfvars")

    console.print("\n[green]Cloud files cleaned up.[/green]")


# =============================================================================
# MCP CONFIGURATION
# =============================================================================

def mcp_setup():
    """Configure SQLcl saved connections for MCP."""
    console.print("\n[bold]MCP Setup[/bold]\n")

    if not check_command("sql"):
        console.print("[red]Error:[/red] sqlcl (sql) not found. Please install it first.")
        sys.exit(1)

    load_env()

    local_password = os.getenv("LOCAL_DB_PASSWORD")
    if local_password:
        console.print("Creating local connection: hr_local")
        conn_str = f"pdbadmin/{local_password}@localhost:{LOCAL_PORT}/FREEPDB1"
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
        console.print("[yellow]Skipping local connection[/yellow] (no password in .env)")

    cloud_password = os.getenv("CLOUD_DB_PASSWORD")
    cloud_tns = os.getenv("CLOUD_TNS_ALIAS")
    if cloud_password and cloud_tns:
        console.print("Creating cloud connection: hr_cloud")
        wallet_opt = f"?TNS_ADMIN={WALLET_DIR}"
        conn_str = f"ADMIN/{cloud_password}@{cloud_tns}{wallet_opt}"
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
        console.print("[yellow]Skipping cloud connection[/yellow] (no credentials in .env)")

    console.print("\n[bold green]MCP setup complete![/bold green]")
    console.print("Test: sql -name hr_local or sql -name hr_cloud")


# =============================================================================
# CLI
# =============================================================================

@click.group()
def cli():
    """Oracle Database MCP Demo Manager."""


@cli.group()
def local():
    """Local database commands."""


@local.command("setup")
def local_setup_cmd():
    """Set up local Oracle FREE container."""
    local_setup()


@local.command("clean")
def local_clean_cmd():
    """Stop and remove local container."""
    local_clean()


@cli.group()
def cloud():
    """Cloud database commands."""


@cloud.command("setup")
def cloud_setup_cmd():
    """Interactive OCI configuration."""
    cloud_setup()


@cloud.command("deploy")
def cloud_deploy_cmd():
    """Extract wallet and run Liquibase."""
    cloud_deploy()


@cloud.command("clean")
def cloud_clean_cmd():
    """Remove generated cloud files."""
    cloud_clean()


@cli.group()
def mcp():
    """MCP configuration."""


@mcp.command("setup")
def mcp_setup_cmd():
    """Configure SQLcl saved connections."""
    mcp_setup()


if __name__ == "__main__":
    cli()
