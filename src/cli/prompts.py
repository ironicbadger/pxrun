"""Interactive prompt handlers for CLI commands."""

import click
from typing import Optional, List, Dict, Any

from src.models.cluster import ClusterNode
from src.models.template import Template
from src.models.storage import StoragePool


def prompt_for_hostname() -> str:
    """Prompt for container hostname.

    Returns:
        Valid hostname
    """
    while True:
        hostname = click.prompt("Container hostname", type=str)
        if hostname and len(hostname) <= 63:
            # Basic validation
            import re
            if re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', hostname.lower()):
                return hostname
        click.echo("Invalid hostname. Must be alphanumeric with dashes, max 63 chars.")


def prompt_for_template(templates: List[Template]) -> str:
    """Prompt user to select a template.

    Args:
        templates: List of available templates

    Returns:
        Selected template path
    """
    if not templates:
        click.echo("No templates available!", err=True)
        return ""

    click.echo("\nAvailable templates:")
    for i, template in enumerate(templates, 1):
        size_gb = template.size_gb
        click.echo(f"  {i}. {template.display_name} ({size_gb:.1f} GB)")

    while True:
        choice = click.prompt("Select template", type=int)
        if 1 <= choice <= len(templates):
            selected = templates[choice - 1]
            return selected.full_path
        click.echo(f"Please enter a number between 1 and {len(templates)}")


def prompt_for_node(nodes: List[ClusterNode]) -> str:
    """Prompt user to select a node.

    Args:
        nodes: List of available nodes

    Returns:
        Selected node name
    """
    if not nodes:
        click.echo("No nodes available!", err=True)
        return ""

    # Filter online nodes
    online_nodes = [n for n in nodes if n.is_online]
    if not online_nodes:
        click.echo("No online nodes available!", err=True)
        return ""

    click.echo("\nAvailable nodes:")
    for i, node in enumerate(online_nodes, 1):
        cpu_free = node.cpu_free_percent
        mem_free_gb = node.memory_free / (1024**3)
        click.echo(f"  {i}. {node.name} (CPU free: {cpu_free:.1f}%, Memory free: {mem_free_gb:.1f} GB)")

    if len(online_nodes) == 1:
        if click.confirm(f"Use node {online_nodes[0].name}?", default=True):
            return online_nodes[0].name

    while True:
        choice = click.prompt("Select node", type=int)
        if 1 <= choice <= len(online_nodes):
            return online_nodes[choice - 1].name
        click.echo(f"Please enter a number between 1 and {len(online_nodes)}")


def prompt_for_storage_pool(pools: List[StoragePool]) -> str:
    """Prompt user to select a storage pool.

    Args:
        pools: List of available storage pools

    Returns:
        Selected pool name
    """
    if not pools:
        click.echo("No storage pools available!", err=True)
        return ""

    # Filter pools that support containers
    container_pools = [p for p in pools if p.supports_containers()]
    if not container_pools:
        click.echo("No storage pools support containers!", err=True)
        return ""

    click.echo("\nAvailable storage pools:")
    for i, pool in enumerate(container_pools, 1):
        free_gb = pool.available_gb
        usage = pool.usage_percent
        click.echo(f"  {i}. {pool.name} ({pool.type}, {free_gb:.1f} GB free, {usage:.1f}% used)")

    if len(container_pools) == 1:
        if click.confirm(f"Use storage pool {container_pools[0].name}?", default=True):
            return container_pools[0].name

    while True:
        choice = click.prompt("Select storage pool", type=int)
        if 1 <= choice <= len(container_pools):
            return container_pools[choice - 1].name
        click.echo(f"Please enter a number between 1 and {len(container_pools)}")


def prompt_for_resources() -> Dict[str, int]:
    """Prompt for container resource allocation.

    Returns:
        Dictionary with cores, memory, and storage
    """
    resources = {}

    # CPU cores
    resources['cores'] = click.prompt(
        "CPU cores",
        type=click.IntRange(1, 128),
        default=2
    )

    # Memory in MB
    resources['memory'] = click.prompt(
        "Memory (MB)",
        type=click.IntRange(128, 524288),
        default=1024
    )

    # Storage in GB
    resources['storage'] = click.prompt(
        "Storage (GB)",
        type=click.IntRange(1, 8192),
        default=10
    )

    return resources


def prompt_for_network() -> Dict[str, Optional[str]]:
    """Prompt for network configuration.

    Returns:
        Dictionary with network settings
    """
    network = {}

    # Network bridge
    network['bridge'] = click.prompt(
        "Network bridge",
        type=str,
        default="vmbr0"
    )

    # IP configuration
    ip_type = click.prompt(
        "IP configuration",
        type=click.Choice(['dhcp', 'static']),
        default='dhcp'
    )

    if ip_type == 'dhcp':
        network['ip'] = 'dhcp'
        network['gateway'] = None
    else:
        # Static IP
        while True:
            ip = click.prompt("IP address (CIDR format, e.g., 192.168.1.100/24)")
            # Basic CIDR validation
            if '/' in ip:
                network['ip'] = ip
                break
            click.echo("Please enter IP in CIDR format (e.g., 192.168.1.100/24)")

        # Gateway
        network['gateway'] = click.prompt("Gateway IP", default=None)

    return network


def prompt_for_ssh_key() -> Optional[str]:
    """Prompt for SSH public key.

    Returns:
        SSH public key or None
    """
    if click.confirm("Add SSH public key for root access?", default=True):
        import os
        from pathlib import Path

        # Check for default key
        default_key_path = Path.home() / ".ssh" / "id_rsa.pub"
        if not default_key_path.exists():
            default_key_path = Path.home() / ".ssh" / "id_ed25519.pub"

        if default_key_path.exists():
            if click.confirm(f"Use key from {default_key_path}?", default=True):
                with open(default_key_path, 'r') as f:
                    return f.read().strip()

        # Manual entry
        return click.prompt("SSH public key", default="")

    return None


def prompt_for_provisioning() -> Dict[str, Any]:
    """Prompt for provisioning options.

    Returns:
        Dictionary with provisioning settings
    """
    prov = {}

    if not click.confirm("Configure provisioning?", default=False):
        return prov

    # Packages to install
    if click.confirm("Install additional packages?", default=False):
        packages = click.prompt("Packages (comma-separated)", default="")
        prov['packages'] = [p.strip() for p in packages.split(',') if p.strip()]

    # Docker installation
    prov['docker'] = click.confirm("Install Docker?", default=False)

    # Tailscale
    if click.confirm("Configure Tailscale?", default=False):
        import os
        # Check if auth key exists in environment
        env_auth_key = os.environ.get('TAILSCALE_AUTH_KEY', '')
        if env_auth_key:
            if click.confirm(f"Use Tailscale auth key from environment?", default=True):
                auth_key = env_auth_key
            else:
                auth_key = click.prompt("Tailscale auth key", hide_input=True)
        else:
            auth_key = click.prompt("Tailscale auth key", hide_input=True)
        prov['tailscale'] = {
            'auth_key': auth_key
        }

    return prov


def confirm_destroy(vmid: int, hostname: str = None) -> bool:
    """Confirm container destruction.

    Args:
        vmid: Container ID
        hostname: Optional container hostname

    Returns:
        True if confirmed
    """
    if hostname:
        message = f"Destroy container {hostname} (ID: {vmid})?"
    else:
        message = f"Destroy container {vmid}?"

    return click.confirm(message, default=False)


def confirm_action(action: str, details: str = None) -> bool:
    """Generic action confirmation.

    Args:
        action: Action description
        details: Optional additional details

    Returns:
        True if confirmed
    """
    message = action
    if details:
        message = f"{action}\n{details}"

    return click.confirm(message, default=True)


def confirm_tailscale_node_removal(node_name: str, node_id: str) -> bool:
    """Confirm Tailscale node removal.

    Args:
        node_name: Name of the Tailscale node
        node_id: ID of the Tailscale node

    Returns:
        True if confirmed
    """
    click.echo(f"\nTailscale node found: {node_name}")
    
    return click.confirm("Remove this node from Tailnet?", default=False)