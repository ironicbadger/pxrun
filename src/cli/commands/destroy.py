"""Destroy command for removing LXC containers."""

import click
import sys

from src.services.proxmox import ProxmoxService
from src.cli import prompts


@click.command('destroy')
@click.argument('vmid', type=int)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.option('--purge', is_flag=True, default=True, help='Also remove from backup storage')
@click.pass_context
def destroy(ctx, vmid, force, purge):
    """Destroy an LXC container.

    VMID is the container ID to destroy.
    """
    try:
        # Initialize service
        proxmox = ProxmoxService()

        if not proxmox.test_connection():
            click.echo("Failed to connect to Proxmox server", err=True)
            sys.exit(1)

        # Find the container
        containers = proxmox.list_containers()
        container_info = None
        for ct in containers:
            if ct['vmid'] == vmid:
                container_info = ct
                break

        if not container_info:
            click.echo(f"Container {vmid} not found", err=True)
            sys.exit(1)

        # Get container details
        node = container_info['node']
        hostname = container_info.get('name', f'ct{vmid}')
        status = container_info.get('status', 'unknown')

        # Display container info
        click.echo(f"Container: {hostname} (VMID: {vmid})")
        click.echo(f"Node: {node}")
        click.echo(f"Status: {status}")

        # Confirm destruction
        if not force:
            if not prompts.confirm_destroy(vmid, hostname):
                click.echo("Cancelled")
                return

        # Stop container if running
        if status == 'running':
            click.echo("Stopping container...")
            try:
                task_id = proxmox.stop_container(node, vmid)
                success, msg = proxmox.wait_for_task(node, task_id, timeout=30)
                if success:
                    click.echo("✓ Container stopped")
                else:
                    click.echo(f"Warning: Failed to stop container: {msg}", err=True)
                    if not force:
                        if not click.confirm("Continue with destruction anyway?", default=False):
                            click.echo("Cancelled")
                            return
            except Exception as e:
                click.echo(f"Warning: Could not stop container: {e}", err=True)

        # Destroy container
        click.echo(f"Destroying container {hostname}...")
        task_id = proxmox.destroy_container(node, vmid, purge=purge)

        # Wait for destruction to complete
        click.echo("Waiting for destruction to complete...")
        success, msg = proxmox.wait_for_task(node, task_id, timeout=60)

        if success:
            click.echo(f"✓ Container {hostname} destroyed successfully")
        else:
            click.echo(f"Failed to destroy container: {msg}", err=True)
            sys.exit(1)

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)