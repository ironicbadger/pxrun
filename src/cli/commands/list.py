"""List command for displaying containers."""

import click
import json
import sys
from typing import List, Dict, Any
from tabulate import tabulate

from src.services.proxmox import ProxmoxService


@click.command('list')
@click.option('--node', '-n', help='Filter by node')
@click.option('--status', '-s', type=click.Choice(['running', 'stopped', 'all']),
              default='all', help='Filter by status')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.option('--sort', type=click.Choice(['vmid', 'name', 'node', 'status', 'memory', 'cpu']),
              default='vmid', help='Sort by field')
@click.pass_context
def list_containers(ctx, node, status, output_format, sort):
    """List all LXC containers in the cluster."""
    try:
        # Initialize service
        proxmox = ProxmoxService()

        if not proxmox.test_connection():
            click.echo("Failed to connect to Proxmox server", err=True)
            sys.exit(1)

        # Get containers
        containers = proxmox.list_containers(node_name=node)

        # Filter by status
        if status != 'all':
            containers = [c for c in containers if c.get('status') == status]

        # Sort containers
        if sort == 'vmid':
            containers.sort(key=lambda x: x.get('vmid', 0))
        elif sort == 'name':
            containers.sort(key=lambda x: x.get('name', ''))
        elif sort == 'node':
            containers.sort(key=lambda x: x.get('node', ''))
        elif sort == 'status':
            containers.sort(key=lambda x: x.get('status', ''))
        elif sort == 'memory':
            containers.sort(key=lambda x: x.get('maxmem', 0), reverse=True)
        elif sort == 'cpu':
            containers.sort(key=lambda x: x.get('cpus', 0), reverse=True)

        # Format output
        if output_format == 'json':
            click.echo(json.dumps(containers, indent=2))

        elif output_format == 'yaml':
            import yaml
            click.echo(yaml.dump(containers, default_flow_style=False))

        else:  # table format
            if not containers:
                click.echo("No containers found")
                return

            # Prepare table data
            headers = ['VMID', 'Name', 'Node', 'Status', 'CPU', 'Memory (MB)', 'Disk (GB)', 'Uptime']
            rows = []

            for ct in containers:
                vmid = ct.get('vmid', '')
                name = ct.get('name', f"ct{vmid}")
                node_name = ct.get('node', '')
                status_val = ct.get('status', 'unknown')

                # Format status with color
                if status_val == 'running':
                    status_display = click.style('● running', fg='green')
                elif status_val == 'stopped':
                    status_display = click.style('○ stopped', fg='red')
                else:
                    status_display = status_val

                cpus = ct.get('cpus', 0)
                memory_mb = ct.get('maxmem', 0) // (1024 * 1024) if ct.get('maxmem') else 0
                disk_gb = ct.get('maxdisk', 0) // (1024 ** 3) if ct.get('maxdisk') else 0

                # Format uptime
                uptime_seconds = ct.get('uptime', 0)
                if uptime_seconds > 0:
                    days = uptime_seconds // 86400
                    hours = (uptime_seconds % 86400) // 3600
                    minutes = (uptime_seconds % 3600) // 60
                    if days > 0:
                        uptime = f"{days}d {hours}h"
                    elif hours > 0:
                        uptime = f"{hours}h {minutes}m"
                    else:
                        uptime = f"{minutes}m"
                else:
                    uptime = '-'

                rows.append([
                    vmid,
                    name,
                    node_name,
                    status_display,
                    cpus,
                    memory_mb,
                    disk_gb,
                    uptime
                ])

            # Display summary
            total = len(containers)
            running = len([c for c in containers if c.get('status') == 'running'])
            stopped = total - running

            click.echo(f"\nContainers: {total} total, {running} running, {stopped} stopped\n")

            # Display table
            click.echo(tabulate(rows, headers=headers, tablefmt='simple'))

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)