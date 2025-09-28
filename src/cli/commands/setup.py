"""Setup command for configuring pxrun."""

import click
import sys
import os
from pathlib import Path

from src.services.proxmox import ProxmoxService
from src.services.credentials import CredentialsManager


@click.group('setup')
@click.pass_context
def setup(ctx):
    """Configure pxrun settings and environment."""
    pass


@setup.command('lxc-templates')
@click.pass_context
def setup_lxc_templates(ctx):
    """Configure LXC template storage location.

    This command helps you identify where LXC templates are stored
    on your Proxmox cluster and configure pxrun to use them.
    """
    try:
        click.echo("🔍 Discovering template storage locations...\n")

        # Initialize service
        proxmox = ProxmoxService()

        if not proxmox.test_connection():
            click.echo("Failed to connect to Proxmox server", err=True)
            click.echo("\nPlease check your .env file has correct Proxmox credentials.", err=True)
            sys.exit(1)

        # Get all storage pools
        click.echo("Checking storage pools across all nodes...")
        all_pools = proxmox.get_storage_pools()

        # Filter pools that support templates
        template_pools = [p for p in all_pools if p.supports_templates()]

        if not template_pools:
            click.echo("\n❌ No storage pools found that support LXC templates!", err=True)
            click.echo("\nYou need to configure a storage pool for templates in Proxmox.", err=True)
            click.echo("Common template storage types: local, nfs, cephfs", err=True)
            sys.exit(1)

        # Show available template storages
        click.echo(f"\n✓ Found {len(template_pools)} storage pool(s) that support templates:\n")

        for i, pool in enumerate(template_pools, 1):
            click.echo(f"  {i}. {pool.name}")
            click.echo(f"     Type: {pool.type}")
            click.echo(f"     Nodes: {', '.join(pool.nodes) if pool.nodes else 'all nodes'}")

            # Check for actual templates
            templates = proxmox.get_templates(storage_name=pool.name)
            if templates:
                click.echo(f"     Templates: {len(templates)} available")
                # Show first few templates
                for j, tmpl in enumerate(templates[:3]):
                    click.echo(f"       - {tmpl.display_name}")
                if len(templates) > 3:
                    click.echo(f"       ... and {len(templates) - 3} more")
            else:
                click.echo("     Templates: None found (empty)")
            click.echo()

        # Ask user to select
        if len(template_pools) == 1:
            selected_pool = template_pools[0]
            if click.confirm(f"Use '{selected_pool.name}' for template storage?", default=True):
                storage_name = selected_pool.name
            else:
                storage_name = click.prompt("Enter storage name manually")
        else:
            while True:
                choice = click.prompt("Select template storage", type=int, default=1)
                if 1 <= choice <= len(template_pools):
                    storage_name = template_pools[choice - 1].name
                    break
                click.echo(f"Please enter a number between 1 and {len(template_pools)}")

        # Update .env file
        env_file = Path('.env')
        if not env_file.exists():
            click.echo("\n⚠️  No .env file found. Creating from .env.example...", err=True)
            example_file = Path('.env.example')
            if example_file.exists():
                import shutil
                shutil.copy(example_file, env_file)
            else:
                click.echo("No .env.example found either. Please create .env manually.", err=True)
                click.echo(f"\nAdd this line to your .env file:")
                click.echo(f"TEMPLATE_STORAGE={storage_name}")
                return

        # Read current .env
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Update or add TEMPLATE_STORAGE
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('TEMPLATE_STORAGE='):
                lines[i] = f"TEMPLATE_STORAGE={storage_name}\n"
                updated = True
                break

        if not updated:
            # Find where to insert it (after DEFAULT_STORAGE_POOL or at end)
            insert_pos = len(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith('DEFAULT_STORAGE_POOL='):
                    insert_pos = i + 1
                    # Add section header if not present
                    lines.insert(insert_pos, "\n")
                    lines.insert(insert_pos + 1, "# Template Storage\n")
                    lines.insert(insert_pos + 2, "# ================\n")
                    lines.insert(insert_pos + 3, f"TEMPLATE_STORAGE={storage_name}\n")
                    updated = True
                    break

            if not updated:
                lines.append(f"\n# Template Storage\n")
                lines.append(f"TEMPLATE_STORAGE={storage_name}\n")

        # Write back
        with open(env_file, 'w') as f:
            f.writelines(lines)

        click.echo(f"\n✓ Configuration updated!")
        click.echo(f"  Template storage set to: {storage_name}")

        # Verify it works
        click.echo("\n🔍 Verifying template access...")
        templates = proxmox.get_templates(storage_name=storage_name)

        if templates:
            click.echo(f"✓ Successfully found {len(templates)} template(s)")
            click.echo("\n📋 Available templates:")
            for tmpl in templates[:5]:
                click.echo(f"  - {tmpl.display_name} ({tmpl.size_gb:.1f} GB)")
            if len(templates) > 5:
                click.echo(f"  ... and {len(templates) - 5} more")
        else:
            click.echo("\n⚠️  No templates found in this storage!", err=True)
            click.echo("\nTo download templates:")
            click.echo("1. Log into Proxmox web UI")
            click.echo(f"2. Go to Storage > {storage_name} > CT Templates")
            click.echo("3. Click 'Templates' button to download")
            click.echo("\nPopular templates:")
            click.echo("  - debian-12-standard")
            click.echo("  - ubuntu-22.04-standard")
            click.echo("  - alpine-3.18-default")

        click.echo("\n✅ Setup complete! You can now create containers with:")
        click.echo("  pxrun create")

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@setup.command('show')
@click.pass_context
def show_config(ctx):
    """Show current configuration."""
    try:
        creds = CredentialsManager()
        creds.load_env_file()

        click.echo("Current pxrun configuration:\n")

        # Proxmox settings
        click.echo("🔌 Proxmox Connection:")
        click.echo(f"  Host: {os.environ.get('PROXMOX_HOST', 'Not set')}")
        click.echo(f"  Token ID: {os.environ.get('PROXMOX_TOKEN_ID', 'Not set')}")
        token_secret = os.environ.get('PROXMOX_TOKEN_SECRET', '')
        if token_secret:
            click.echo(f"  Token Secret: {token_secret[:8]}...{token_secret[-4:]}")
        else:
            click.echo("  Token Secret: Not set")

        # Default settings
        click.echo("\n📦 Container Defaults:")
        click.echo(f"  Cores: {os.environ.get('DEFAULT_CORES', '2')}")
        click.echo(f"  Memory: {os.environ.get('DEFAULT_MEMORY', '1024')} MB")
        click.echo(f"  Storage: {os.environ.get('DEFAULT_STORAGE', '10')} GB")
        click.echo(f"  Bridge: {os.environ.get('DEFAULT_BRIDGE', 'vmbr0')}")
        click.echo(f"  Storage Pool: {os.environ.get('DEFAULT_STORAGE_POOL', 'local-lvm')}")

        # Template storage
        click.echo("\n📀 Template Storage:")
        template_storage = os.environ.get('TEMPLATE_STORAGE', 'Not configured')
        click.echo(f"  Storage: {template_storage}")

        if template_storage != 'Not configured':
            # Try to count templates
            try:
                proxmox = ProxmoxService()
                if proxmox.test_connection():
                    templates = proxmox.get_templates(storage_name=template_storage)
                    click.echo(f"  Templates available: {len(templates)}")
            except:
                pass

        # SSH settings
        click.echo("\n🔐 SSH Settings:")
        click.echo(f"  User: {os.environ.get('SSH_USER', 'root')}")
        click.echo(f"  Key Path: {os.environ.get('SSH_KEY_PATH', '~/.ssh/id_rsa')}")

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)