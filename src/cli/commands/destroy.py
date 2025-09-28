"""Destroy command for removing LXC containers."""

import click
import sys
import os
import logging

from src.services.proxmox import ProxmoxService
from src.cli import prompts

logger = logging.getLogger(__name__)


@click.command('destroy')
@click.argument('vmid', type=int)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.option('--purge', is_flag=True, default=True, help='Also remove from backup storage')
@click.option('--remove-tailscale-node', is_flag=True, default=True, help='Remove matching Tailscale node from Tailnet')
@click.pass_context
def destroy(ctx, vmid, force, purge, remove_tailscale_node):
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

        # Check for Tailscale node removal
        if remove_tailscale_node:
            # Check if Tailscale API is configured
            tailscale_configured = bool(os.getenv('TAILSCALE_API_KEY')) and bool(os.getenv('TAILSCALE_TAILNET'))
            
            if tailscale_configured:
                click.echo("\nChecking for associated Tailscale node...")
                try:
                    from src.services.tailscale import TailscaleNodeManager
                    
                    node_manager = TailscaleNodeManager()
                    # Try to find and remove the Tailscale node
                    # Pass force flag to skip additional confirmation if --force was used
                    success = node_manager.remove_container_node(hostname, vmid, force=force)
                    
                    if not success and not force:
                        # If removal failed and not forced, ask if we should continue
                        if not click.confirm("Continue with container destruction anyway?", default=True):
                            click.echo("Cancelled")
                            return
                            
                except Exception as e:
                    logger.warning(f"Failed to check/remove Tailscale node: {e}")
                    if ctx.obj.get('DEBUG'):
                        click.echo(f"Tailscale error: {e}", err=True)
                    # Continue with container destruction even if Tailscale removal fails
            else:
                logger.debug("Tailscale API not configured, skipping node removal")

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