"""Tailscale management commands."""

import click
import sys
import json
import subprocess
from tabulate import tabulate
from datetime import datetime
from typing import Optional

from src.services.tailscale import TailscaleAPIClient
from src.utils import output


@click.group('tailscale')
@click.pass_context
def tailscale(ctx):
    """Manage Tailscale nodes and configuration."""
    pass


@tailscale.command('list-nodes')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.option('--online-only', is_flag=True, help='Show only online nodes')
@click.pass_context
def list_nodes(ctx, format, online_only):
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


@tailscale.command('generate-key')
@click.option('--description', '-d', default='pxrun generated key', help='Description for the auth key')
@click.option('--reusable', is_flag=True, help='Allow key to be used multiple times')
@click.option('--ephemeral/--permanent', default=True, help='Make devices ephemeral (default: ephemeral)')
@click.option('--preauthorized/--no-preauthorized', default=True, help='Pre-authorize devices (default: yes)')
@click.option('--expires', '-e', type=int, default=3600, help='Expiration time in seconds (default: 3600)')
@click.option('--tags', '-t', multiple=True, help='Tags to apply to devices (can be specified multiple times)')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text', help='Output format')
@click.pass_context
def generate_key(ctx, description, reusable, ephemeral, preauthorized, expires, tags, format):
    """Generate a new Tailscale auth key.
    
    This command creates a new authentication key that can be used to add
    devices to your Tailnet. By default, keys are ephemeral, single-use,
    and expire in 1 hour.
    
    Examples:
        # Generate a single-use ephemeral key
        pxrun tailscale generate-key
        
        # Generate a reusable key for development
        pxrun tailscale generate-key --reusable --expires 86400
        
        # Generate a key with tags
        pxrun tailscale generate-key --tags tag:server --tags tag:prod
    
    Requires TAILSCALE_API_KEY and TAILSCALE_TAILNET environment variables.
    """
    try:
        # Initialize API client
        client = TailscaleAPIClient()
        
        # Convert tags tuple to list if provided
        tags_list = list(tags) if tags else None
        
        # Create the auth key
        auth_key = client.create_auth_key(
            description=description,
            reusable=reusable,
            ephemeral=ephemeral,
            preauthorized=preauthorized,
            expiry_seconds=expires,
            tags=tags_list
        )
        
        if not auth_key:
            click.echo("Failed to generate auth key", err=True)
            sys.exit(1)
        
        if format == 'json':
            output = {
                'key': auth_key,
                'description': description,
                'reusable': reusable,
                'ephemeral': ephemeral,
                'preauthorized': preauthorized,
                'expiry_seconds': expires,
                'tags': tags_list or []
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"\nGenerated Tailscale auth key:")
            click.echo(f"\n{auth_key}\n")
            click.echo(f"Properties:")
            click.echo(f"  Description: {description}")
            click.echo(f"  Reusable: {'Yes' if reusable else 'No'}")
            click.echo(f"  Ephemeral: {'Yes' if ephemeral else 'No'}")
            click.echo(f"  Pre-authorized: {'Yes' if preauthorized else 'No'}")
            click.echo(f"  Expires in: {expires} seconds")
            if tags_list:
                click.echo(f"  Tags: {', '.join(tags_list)}")
            click.echo("\nStore this key securely. It will not be shown again.")
            
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


@tailscale.command("refresh")
@click.pass_context
def refresh(ctx):
    """Refresh local Tailscale connection.
    
    Performs 'tailscale down' followed by 'tailscale up' to quickly
    refresh the local machine's connection to the Tailnet.
    
    Example:
        pxrun tailscale refresh
    """
    try:
        # Check if tailscale is installed
        try:
            subprocess.run(["which", "tailscale"], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            output.error("Tailscale is not installed on this machine")
            output.info("Install Tailscale from: https://tailscale.com/download")
            sys.exit(1)
        
        # Bring Tailscale down
        with output.spinner("Refreshing Tailscale connection..."):
            result = subprocess.run(
                ["tailscale", "down"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Immediately bring it back up
            result = subprocess.run(
                ["tailscale", "up"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                output.error(f"Failed to refresh: {result.stderr}")
                sys.exit(1)
                
        output.success("Tailscale connection refreshed!")
            
    except Exception as e:
        if ctx.obj.get("DEBUG"):
            raise
        output.error(f"Error: {e}")
        sys.exit(1)
