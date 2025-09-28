"""Save-config command for exporting container configurations."""

import click
import sys
from pathlib import Path

from src.services.proxmox import ProxmoxService
from src.services.config_manager import ConfigManager
from src.models.container import Container


@click.command('save-config')
@click.argument('vmid', type=int)
@click.option('--output', '-o', type=click.Path(),
              help='Output file path (default: <hostname>.yaml)')
@click.option('--include-provisioning', '-p', is_flag=True,
              help='Include provisioning configuration (if available)')
@click.pass_context
def save_config(ctx, vmid, output, include_provisioning):
    """Export container configuration to YAML file.

    VMID is the container ID to export.
    """
    try:
        # Initialize services
        proxmox = ProxmoxService()
        config_mgr = ConfigManager()

        if not proxmox.test_connection():
            click.echo("Failed to connect to Proxmox server", err=True)
            sys.exit(1)

        # Find the container
        containers = proxmox.list_containers()
        container_info = None
        node = None

        for ct in containers:
            if ct['vmid'] == vmid:
                container_info = ct
                node = ct['node']
                break

        if not container_info:
            click.echo(f"Container {vmid} not found", err=True)
            sys.exit(1)

        # Get detailed container configuration
        container = proxmox.get_container(node, vmid)
        if not container:
            click.echo(f"Failed to get container details for {vmid}", err=True)
            sys.exit(1)

        # Prepare output path
        if not output:
            output = f"{container.hostname}.yaml"

        output_path = Path(output)

        # Check if file exists
        if output_path.exists():
            if not click.confirm(f"File {output} exists. Overwrite?", default=False):
                click.echo("Cancelled")
                return

        # Export configuration
        config_dict = config_mgr.export_container_config(container)

        # Add metadata
        config_dict['_metadata'] = {
            'exported_from': f"VMID {vmid} on node {node}",
            'export_date': str(Path.cwd()),
            'original_vmid': vmid
        }

        # Note about provisioning
        if include_provisioning:
            click.echo("Note: Provisioning configuration cannot be recovered from existing containers")
            config_dict['provisioning'] = {
                '_comment': 'Add your provisioning configuration here'
            }

        # Save configuration
        config_mgr.save_config(config_dict, str(output_path))

        click.echo(f"✓ Configuration exported to {output_path}")

        # Display the configuration
        if click.confirm("\nDisplay configuration?", default=False):
            import yaml
            click.echo("\n" + yaml.dump(config_dict, default_flow_style=False))

        click.echo(f"\nYou can use this configuration to create new containers:")
        click.echo(f"  pxrun create --config {output_path}")

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)