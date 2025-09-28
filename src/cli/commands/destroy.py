"""Destroy command for removing LXC containers."""

import click
import sys
import os
import logging

from src.services.proxmox import ProxmoxService
from src.cli import prompts
from src.utils import output

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

        with output.spinner("Connecting to Proxmox server..."):
            if not proxmox.test_connection():
                output.error("Failed to connect to Proxmox server")
                sys.exit(1)

        # Find the container
        containers = proxmox.list_containers()
        container_info = None
        for ct in containers:
            if ct['vmid'] == vmid:
                container_info = ct
                break

        if not container_info:
            output.error(f"Container {vmid} not found")
            sys.exit(1)

        # Get container details
        node = container_info['node']
        hostname = container_info.get('name', f'ct{vmid}')
        status = container_info.get('status', 'unknown')

        # Display container info
        output.print(f"[bold]Container:[/bold] {hostname} (VMID: {vmid})")
        output.print(f"[bold]Node:[/bold] {node}")
        output.print(f"[bold]Status:[/bold] {status}")

        # Confirm destruction
        if not force:
            if not prompts.confirm_destroy(vmid, hostname):
                output.warning("Cancelled")
                return

        # Stop container if running
        if status == 'running':
            with output.spinner("Stopping container...", success_text="Container stopped"):
                try:
                    task_id = proxmox.stop_container(node, vmid)
                    success, msg = proxmox.wait_for_task(node, task_id, timeout=30)
                    if not success:
                        output.warning(f"Failed to stop container: {msg}")
                        if not force:
                            if not click.confirm("Continue with destruction anyway?", default=False):
                                output.warning("Cancelled")
                                return
                except Exception as e:
                    output.warning(f"Could not stop container: {e}")

        # Check for Tailscale node removal
        if remove_tailscale_node:
            # Check if Tailscale API is configured
            tailscale_configured = bool(os.getenv('TAILSCALE_API_KEY')) and bool(os.getenv('TAILSCALE_TAILNET'))
            
            if tailscale_configured:
                output.info("Checking for associated Tailscale node...")
                try:
                    from src.services.tailscale import TailscaleNodeManager
                    
                    node_manager = TailscaleNodeManager()
                    # Try to find and remove the Tailscale node
                    # Pass force flag to skip additional confirmation if --force was used
                    success = node_manager.remove_container_node(hostname, vmid, force=force)
                    
                    if not success and not force:
                        # If removal failed and not forced, ask if we should continue
                        if not click.confirm("Continue with container destruction anyway?", default=True):
                            output.warning("Cancelled")
                            return
                            
                except Exception as e:
                    logger.warning(f"Failed to check/remove Tailscale node: {e}")
                    if ctx.obj.get('DEBUG'):
                        output.warning(f"Tailscale error: {e}")
                    # Continue with container destruction even if Tailscale removal fails
            else:
                logger.debug("Tailscale API not configured, skipping node removal")

        # Destroy container
        with output.spinner(
            f"Destroying container {hostname}...",
            success_text=f"Container {hostname} destroyed successfully"
        ):
            task_id = proxmox.destroy_container(node, vmid, purge=purge)
            success, msg = proxmox.wait_for_task(node, task_id, timeout=60)
            
            if not success:
                output.error(f"Failed to destroy container: {msg}")
                sys.exit(1)

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        output.error(str(e))
        sys.exit(1)