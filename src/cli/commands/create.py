"""Create command for creating new LXC containers."""

import click
import sys
import os
import time
from typing import Optional

from src.services.proxmox import ProxmoxService, ProxmoxAuth
from src.services.config_manager import ConfigManager
from src.services.ssh_provisioner import SSHProvisioner, SSHConfig
from src.services.node_selector import NodeSelector, SelectionStrategy
from src.models.container import Container
from src.models.provisioning import ProvisioningConfig
from src.cli import prompts


@click.command('create')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to YAML configuration file')
@click.option('--hostname', '-h', help='Container hostname')
@click.option('--template', '-t', help='Template to use')
@click.option('--node', '-n', help='Target node')
@click.option('--cores', type=int, help='Number of CPU cores')
@click.option('--memory', type=int, help='Memory in MB')
@click.option('--storage', type=int, help='Storage in GB')
@click.option('--storage-pool', help='Storage pool to use')
@click.option('--network-bridge', default='vmbr0', help='Network bridge')
@click.option('--ip', help='IP address (CIDR) or "dhcp"')
@click.option('--gateway', help='Gateway IP address')
@click.option('--ssh-key', help='SSH public key to add')
@click.option('--start', is_flag=True, default=True, help='Start container after creation')
@click.option('--provision', is_flag=True, default=True, help='Run provisioning')
@click.option('--dry-run', is_flag=True, help='Validate without creating')
@click.pass_context
def create(ctx, config, hostname, template, node, cores, memory, storage,
           storage_pool, network_bridge, ip, gateway, ssh_key, start,
           provision, dry_run):
    """Create a new LXC container.

    Can be run interactively or with a configuration file.
    """
    try:
        # Initialize services
        proxmox = ProxmoxService()

        if not proxmox.test_connection():
            click.echo("Failed to connect to Proxmox server", err=True)
            sys.exit(1)

        # Get cluster information
        nodes = proxmox.list_nodes()

        # Load from config file if provided
        if config:
            click.echo(f"Loading configuration from {config}...")
            config_mgr = ConfigManager()
            config_data = config_mgr.load_config(config)
            container = config_mgr.parse_container_config(config_data)

            # Override with command line options
            if hostname:
                container.hostname = hostname
            if template:
                container.template = template
            if node:
                container.node = node
            if cores:
                container.cores = cores
            if memory:
                container.memory = memory
            if storage:
                container.storage = storage
            if storage_pool:
                container.storage_pool = storage_pool

            # Get provisioning config if present
            if 'provisioning' in config_data:
                provisioning_config = config_mgr.parse_provisioning_config(
                    config_data['provisioning']
                )
            else:
                provisioning_config = None

        else:
            # Interactive mode or command line args
            # 1. Select node first
            if not node:
                selector = NodeSelector(nodes)
                if cores and memory and storage_pool:
                    # Use intelligent selection
                    requirements = {
                        'cores': cores or 2,
                        'memory_mb': memory or 1024,
                        'storage_gb': storage or 10,
                        'storage_pool': storage_pool,
                        'network_bridge': network_bridge
                    }
                    selected_node = selector.select_node(
                        requirements,
                        strategy=SelectionStrategy.LEAST_LOADED
                    )
                    if selected_node:
                        node = selected_node.name

                # If intelligent selection didn't work or wasn't attempted, prompt user
                if not node:
                    node = prompts.prompt_for_node(nodes)

            if not node:
                click.echo("No node selected", err=True)
                sys.exit(1)

            # 2. Get hostname
            if not hostname:
                hostname = prompts.prompt_for_hostname()

            # 3. Get storage pools for selected node (filtered)
            if not storage_pool:
                pools = proxmox.get_storage_pools(node)
                storage_pool = prompts.prompt_for_storage_pool(pools)
                if not storage_pool:
                    click.echo("No storage pool selected", err=True)
                    sys.exit(1)

            # 4. Get templates from template storage (filtered by selected node)
            if not template:
                template_storage = os.environ.get('TEMPLATE_STORAGE', 'local')
                templates = proxmox.get_templates(node_name=node, storage_name=template_storage)
                template = prompts.prompt_for_template(templates)
                if not template:
                    click.echo("No template selected", err=True)
                    sys.exit(1)

            # Get resources if not specified
            if not all([cores, memory, storage]):
                resources = prompts.prompt_for_resources()
                cores = cores or resources['cores']
                memory = memory or resources['memory']
                storage = storage or resources['storage']

            # Network configuration
            if not ip:
                network = prompts.prompt_for_network()
                ip = network['ip']
                gateway = gateway or network.get('gateway')
                network_bridge = network_bridge or network.get('bridge', 'vmbr0')

            # SSH key
            if not ssh_key:
                ssh_key = prompts.prompt_for_ssh_key()

            # Create container object
            vmid = proxmox.get_next_vmid()
            container = Container(
                vmid=vmid,
                hostname=hostname,
                template=template,
                node=node,
                cores=cores,
                memory=memory,
                storage=storage,
                storage_pool=storage_pool,
                network_bridge=network_bridge,
                network_ip=ip,
                network_gateway=gateway,
                start_on_boot=False
            )

            # Provisioning configuration
            provisioning_config = None
            if provision:
                prov_opts = prompts.prompt_for_provisioning()
                if prov_opts or ssh_key:
                    provisioning_config = ProvisioningConfig()
                    if ssh_key:
                        provisioning_config.ssh_keys = [ssh_key]
                    if prov_opts:
                        provisioning_config.packages = prov_opts.get('packages', [])
                        provisioning_config.docker = prov_opts.get('docker', False)
                        if 'tailscale' in prov_opts:
                            from src.models.tailscale import TailscaleConfig
                            provisioning_config.tailscale = TailscaleConfig(
                                auth_key=prov_opts['tailscale']['auth_key']
                            )

        # Display configuration
        click.echo("\nContainer configuration:")
        click.echo(f"  VMID: {container.vmid}")
        click.echo(f"  Hostname: {container.hostname}")
        click.echo(f"  Node: {container.node}")
        click.echo(f"  Template: {container.template}")
        click.echo(f"  Resources: {container.cores} cores, {container.memory} MB RAM, {container.storage} GB storage")
        click.echo(f"  Storage pool: {container.storage_pool}")
        click.echo(f"  Network: {container.network_bridge}, IP: {container.network_ip or 'dhcp'}")

        if dry_run:
            click.echo("\nDry run mode - no container will be created")
            return

        if not click.confirm("\nProceed with container creation?", default=True):
            click.echo("Cancelled")
            return

        # Create container
        click.echo(f"\nCreating container {container.hostname}...")
        task_id = proxmox.create_container(container)
        click.echo(f"Creation task started: {task_id}")

        # Wait for creation to complete
        click.echo("Waiting for container creation to complete...")
        success, msg = proxmox.wait_for_task(container.node, task_id, timeout=120)

        if not success:
            click.echo(f"Container creation failed: {msg}", err=True)
            sys.exit(1)

        click.echo(f"✓ Container created successfully (VMID: {container.vmid})")

        # Start container if requested
        if start:
            click.echo("Starting container...")
            task_id = proxmox.start_container(container.node, container.vmid)
            success, msg = proxmox.wait_for_task(container.node, task_id, timeout=60)

            if success:
                click.echo("✓ Container started")
            else:
                click.echo(f"Warning: Failed to start container: {msg}", err=True)

        # Run provisioning if configured
        if provision and provisioning_config and provisioning_config.has_provisioning():
            click.echo("\nRunning provisioning...")

            # Get container IP address
            container_ip = None
            if container.network_ip and container.network_ip != 'dhcp':
                container_ip = container.network_ip.split('/')[0]
            else:
                # For DHCP containers, try to get IP from Proxmox
                click.echo("Container uses DHCP, attempting to discover IP address...")
                try:
                    # Wait a moment for network to come up
                    time.sleep(5)
                    container_status = proxmox.get_container(container.node, container.vmid)
                    if container_status and hasattr(container_status, 'network_ip') and container_status.network_ip:
                        container_ip = container_status.network_ip
                        click.echo(f"Discovered container IP: {container_ip}")
                    else:
                        click.echo("Could not auto-discover container IP address")
                        container_ip = click.prompt("Enter container IP address for provisioning", type=str)
                except Exception as e:
                    click.echo(f"Failed to discover IP: {e}")
                    if click.confirm("Enter IP address manually for provisioning?", default=True):
                        container_ip = click.prompt("Container IP address", type=str)

            if not container_ip:
                click.echo("Skipping provisioning - no IP address available", err=True)
                return

            # Try SSH key authentication first, then fall back to password
            ssh_key_path = os.environ.get('SSH_KEY_PATH', '~/.ssh/id_rsa')
            ssh_key_path = os.path.expanduser(ssh_key_path)

            ssh_config = SSHConfig(
                host=container_ip,
                username='root',
                key_filename=ssh_key_path if os.path.exists(ssh_key_path) else None,
                password=None,  # Try key first
                timeout=30,
                retry_attempts=12,  # More retries for container startup
                retry_delay=5
            )

            provisioner = SSHProvisioner(ssh_config)

            click.echo(f"Attempting SSH connection to {container_ip}...")
            if provisioner.connect(wait_for_ssh=True):
                click.echo("✓ SSH connection established")
                if provisioner.provision(provisioning_config):
                    click.echo("✓ Provisioning completed successfully")
                else:
                    click.echo("Warning: Some provisioning steps failed", err=True)
                provisioner.disconnect()
            else:
                click.echo("✗ Could not establish SSH connection", err=True)
                click.echo("\nTroubleshooting tips:")
                click.echo("1. Ensure your SSH key is added to the ssh-agent")
                click.echo("2. Check that the container is fully started")
                click.echo("3. Verify network connectivity to the container")
                click.echo(f"4. Try manual SSH: ssh root@{container_ip}")

                if click.confirm("Try provisioning with password authentication?", default=False):
                    password = click.prompt("Root password", hide_input=True)
                    ssh_config.password = password
                    ssh_config.key_filename = None

                    provisioner = SSHProvisioner(ssh_config)
                    if provisioner.connect(wait_for_ssh=False):
                        click.echo("✓ SSH connection established with password")
                        if provisioner.provision(provisioning_config):
                            click.echo("✓ Provisioning completed successfully")
                        else:
                            click.echo("Warning: Some provisioning steps failed", err=True)
                        provisioner.disconnect()
                    else:
                        click.echo("✗ Password authentication also failed", err=True)

        click.echo(f"\nContainer {container.hostname} is ready!")
        click.echo(f"Connect with: ssh root@{container.network_ip or container.hostname}")

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)