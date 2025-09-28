"""List Tailscale nodes command."""

import click
import sys
from tabulate import tabulate
from datetime import datetime

from src.services.tailscale import TailscaleAPIClient


@click.command('list-tailscale-nodes')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.option('--online-only', is_flag=True, help='Show only online nodes')
@click.pass_context
def list_tailscale_nodes(ctx, format, online_only):
    """List all nodes in the Tailnet.
    
    Requires TAILSCALE_API_KEY and TAILSCALE_TAILNET environment variables.
    """
    try:
        # Initialize API client (will use env vars)
        client = TailscaleAPIClient()
        
        # Get all nodes
        nodes = client.list_nodes()
        
        if not nodes:
            click.echo("No Tailscale nodes found in the Tailnet")
            return
        
        # Filter if needed
        if online_only:
            nodes = [n for n in nodes if n.online]
            if not nodes:
                click.echo("No online Tailscale nodes found")
                return
        
        if format == 'json':
            import json
            output = []
            for node in nodes:
                output.append({
                    'id': node.id,
                    'name': node.name,
                    'hostname': node.hostname,
                    'addresses': node.addresses,
                    'os': node.os,
                    'online': node.online,
                    'last_seen': node.last_seen,
                    'created': node.created
                })
            click.echo(json.dumps(output, indent=2))
            
        elif format == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Name', 'Hostname', 'IP Addresses', 'OS', 'Online', 'Last Seen'])
            for node in nodes:
                writer.writerow([
                    node.id,
                    node.name,
                    node.hostname,
                    ', '.join(node.addresses) if node.addresses else 'N/A',
                    node.os,
                    'Yes' if node.online else 'No',
                    node.last_seen
                ])
            click.echo(output.getvalue())
            
        else:  # table format
            # Prepare table data
            table_data = []
            for node in nodes:
                # Format last seen time
                try:
                    if node.last_seen:
                        last_seen_dt = datetime.fromisoformat(node.last_seen.replace('Z', '+00:00'))
                        now = datetime.now(last_seen_dt.tzinfo)
                        delta = now - last_seen_dt
                        if delta.days > 0:
                            last_seen = f"{delta.days}d ago"
                        elif delta.seconds > 3600:
                            last_seen = f"{delta.seconds // 3600}h ago"
                        elif delta.seconds > 60:
                            last_seen = f"{delta.seconds // 60}m ago"
                        else:
                            last_seen = "just now"
                    else:
                        last_seen = "Unknown"
                except:
                    last_seen = node.last_seen or "Unknown"
                
                # Get primary IP
                primary_ip = node.addresses[0] if node.addresses else "N/A"
                
                table_data.append([
                    node.hostname or node.name,
                    primary_ip,
                    node.os,
                    "✓" if node.online else "✗",
                    last_seen,
                    node.id[:8] + "..." if len(node.id) > 11 else node.id
                ])
            
            # Sort by hostname
            table_data.sort(key=lambda x: x[0])
            
            headers = ["Hostname", "IP Address", "OS", "Online", "Last Seen", "ID"]
            click.echo("\nTailscale Nodes:")
            click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))
            click.echo(f"\nTotal: {len(nodes)} node(s)")
            
            if online_only:
                click.echo(f"Showing online nodes only")
            else:
                online_count = sum(1 for n in nodes if n.online)
                click.echo(f"Online: {online_count}, Offline: {len(nodes) - online_count}")
    
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        click.echo("\nPlease ensure the following environment variables are set:", err=True)
        click.echo("  - TAILSCALE_API_KEY: Your Tailscale API key", err=True)
        click.echo("  - TAILSCALE_TAILNET: Your Tailnet organization", err=True)
        sys.exit(1)
        
    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)