"""Create command for creating new LXC containers."""

import click
import sys
import os
import time
import logging
from typing import Optional

from src.services.proxmox import ProxmoxService, ProxmoxAuth
from src.services.config_manager import ConfigManager
from src.services.ssh_provisioner import SSHProvisioner, SSHConfig
from src.services.node_selector import NodeSelector, SelectionStrategy
from src.models.container import Container
from src.models.provisioning import ProvisioningConfig
from src.cli import prompts
from src.utils import output

# Suppress debug logging
logger = logging.getLogger(__name__)


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
@click.option('--verbose', is_flag=True, help='Show detailed command output (or set PXRUN_VERBOSE=1)')
@click.pass_context
def create(ctx, config, hostname, template, node, cores, memory, storage,
           storage_pool, network_bridge, ip, gateway, ssh_key, start,
           provision, dry_run, verbose):
    """Create a new LXC container.

    Can be run interactively or with a configuration file.
    """
    try:
        # Initialize services
        proxmox = ProxmoxService()

        with output.spinner("Connecting to Proxmox server..."):
            if not proxmox.test_connection():
                output.error("Failed to connect to Proxmox server")
                sys.exit(1)

        # Get cluster information
        nodes = proxmox.list_nodes()

        # Load from config file if provided
        if config:
            output.info(f"Loading configuration from {config}")
            config_mgr = ConfigManager()
            config_data = config_mgr.load_config(config)
            container = config_mgr.parse_container_config(config_data)

            # Assign next available VMID if not specified in config
            # Start from 5000 for config-based containers to avoid conflicts
            if not container.vmid or container.vmid == 0:
                container.vmid = proxmox.get_next_vmid(min_vmid=5000)

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
                output.error("No node selected")
                sys.exit(1)

            # 2. Get hostname
            if not hostname:
                hostname = prompts.prompt_for_hostname()

            # 3. Get storage pools for selected node (filtered)
            if not storage_pool:
                pools = proxmox.get_storage_pools(node)
                storage_pool = prompts.prompt_for_storage_pool(pools)
                if not storage_pool:
                    output.error("No storage pool selected")
                    sys.exit(1)

            # 4. Get templates from template storage (filtered by selected node)
            if not template:
                template_storage = os.environ.get('TEMPLATE_STORAGE', 'local')
                templates = proxmox.get_templates(node_name=node, storage_name=template_storage)
                template = prompts.prompt_for_template(templates)
                if not template:
                    output.error("No template selected")
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
                            from src.services.tailscale import TailscaleProvisioningService
                            
                            # Get auth key from config or generate one
                            auth_key = prov_opts['tailscale'].get('auth_key')
                            
                            # If no auth key provided or it's a reference to env var, try auto-generation
                            if not auth_key or auth_key.startswith('${'):
                                try:
                                    provisioning_service = TailscaleProvisioningService()
                                    generated_key = provisioning_service.get_or_generate_auth_key(container.hostname)
                                    # Use generated key if we got one
                                    if generated_key:
                                        auth_key = generated_key
                                        output.info("Using auto-generated Tailscale auth key")
                                except Exception as e:
                                    # Fall back to the original auth key (might be env var reference)
                                    if not auth_key:
                                        auth_key = '${TAILSCALE_AUTH_KEY}'  # Default to env var
                                    logger.debug(f"Auth key generation failed, using fallback: {e}")
                            
                            provisioning_config.tailscale = TailscaleConfig(
                                auth_key=auth_key
                            )

        # Display configuration
        config_dict = {
            'vmid': container.vmid,
            'hostname': container.hostname,
            'node': container.node,
            'template': container.template,
            'cores': container.cores,
            'memory': container.memory,
            'storage': container.storage,
            'storage_pool': container.storage_pool,
            'network_bridge': container.network_bridge,
            'network_ip': container.network_ip or 'dhcp'
        }
        
        # Add provisioning config if present
        if provisioning_config:
            if provisioning_config.packages:
                config_dict['packages'] = provisioning_config.packages
            if provisioning_config.docker:
                config_dict['docker'] = True
            if provisioning_config.tailscale:
                # Include tailnet org if API is configured
                tailnet = os.environ.get('TAILSCALE_TAILNET')
                if tailnet:
                    config_dict['tailscale'] = {'enabled': True, 'tailnet': tailnet}
                else:
                    config_dict['tailscale'] = True
        
        if dry_run:
            output.container_config(config_dict)
            output.info("Dry run mode - no container will be created")
            return

        if not output.create_confirmation_prompt(config_dict):
            output.warning("Cancelled")
            return

        # Create container
        output.print("")
        with output.spinner(f"Creating container {container.hostname}...", 
                           success_text=f"Container created successfully (VMID: {container.vmid})"):
            try:
                task_id = proxmox.create_container(container)
                # Wait for creation to complete
                success, msg = proxmox.wait_for_task(container.node, task_id, timeout=120)
                if not success:
                    output.error(f"Container creation failed: {msg}")
                    sys.exit(1)
            except ValueError as e:
                # VMID conflict or validation error
                output.error(f"Configuration Error: {e}")
                output.print("\n[yellow]Suggestions:[/yellow]")
                output.print("  • Use 'pxrun list' to see existing containers")
                if "already exists" in str(e).lower():
                    try:
                        next_vmid = proxmox.get_next_vmid()
                        output.print(f"  • Next available VMID: {next_vmid}")
                    except:
                        pass
                output.print("  • Let pxrun auto-assign a VMID by removing it from your config")
                output.print("  • Or specify a different VMID in your configuration")
                sys.exit(1)
            except RuntimeError as e:
                output.error(f"Creation Failed: {e}")
                sys.exit(1)

        # Configure LXC for Tailscale if needed (must be done before starting)
        if provision and provisioning_config and provisioning_config.tailscale:
            if not proxmox.configure_lxc_for_tailscale(container.node, container.vmid):
                output.warning("Failed to configure LXC for Tailscale")

        # Start container if requested
        if start:
            with output.spinner("Starting container...", success_text="Container started"):
                task_id = proxmox.start_container(container.node, container.vmid)
                success, msg = proxmox.wait_for_task(container.node, task_id, timeout=60)
                if not success:
                    output.warning(f"Failed to start container: {msg}")

        # Run provisioning if configured OR just set up locales
        if provision:
            if provisioning_config and provisioning_config.has_provisioning():
                # Wait a moment for container to fully start
                time.sleep(3)

                # Don't use spinner - the provisioning method uses Live displays internally
                # Count total provisioning steps for progress indicator
                provisioning_steps = []
                if provisioning_config.packages:
                    provisioning_steps.append(f"Install {len(provisioning_config.packages)} package(s)")
                if provisioning_config.docker:
                    provisioning_steps.append("Install Docker")
                if provisioning_config.tailscale:
                    provisioning_steps.append("Configure Tailscale")
                if provisioning_config.scripts:
                    provisioning_steps.append(f"Run {len(provisioning_config.scripts)} script(s)")
                
                total_steps = len(provisioning_steps) + 1  # +1 for package list update
                output.info(f"Starting container provisioning ({total_steps} steps):")
                
                # Show what will be installed as an indented list
                output.print("  • Update package lists")
                for step in provisioning_steps:
                    output.print(f"  • {step}")
                
                success = proxmox.provision_container_via_exec(container.node, container.vmid, provisioning_config, verbose)
                if success:
                    output.success("All provisioning completed successfully!")
                else:
                    output.error("Some provisioning steps failed")
                    output.info("You can manually provision the container with:")
                    output.print(f"  pxrun ssh {container.vmid}")
                    output.print("  Or access it via the Proxmox web interface")
            else:
                # No explicit provisioning, but still set up locales to prevent SSH warnings
                time.sleep(3)  # Wait for container to be ready
                
                # Create an empty provisioning config just for locale setup
                from src.models.provisioning import ProvisioningConfig
                empty_config = ProvisioningConfig()
                
                # This will just run locale setup since the config is empty (no spinner due to potential live output)
                proxmox.provision_container_via_exec(container.node, container.vmid, empty_config, verbose=False)

        # Get actual IP address if using DHCP
        actual_ip = container.network_ip
        if not actual_ip or actual_ip.lower() == 'dhcp':
            # Try to get the actual assigned IP from Proxmox
            try:
                # Wait a moment for network to be ready
                time.sleep(2)
                container_info = proxmox.get_container_info(container.node, container.vmid)
                if container_info:
                    # Try to extract IP from various possible fields
                    # Check if there's a 'net' field with IP info
                    for key, value in container_info.items():
                        if key.startswith('net') and isinstance(value, str) and 'ip=' in value:
                            # Extract IP from format like "ip=192.168.1.100/24"
                            ip_part = value.split('ip=')[1].split(',')[0].split('/')[0]
                            if ip_part and ip_part != 'dhcp':
                                actual_ip = ip_part
                                break
            except Exception as e:
                pass  # Fall back to hostname if IP lookup fails

        output.success(f"Container {container.hostname} is ready!")
        
        # Get Tailscale info if available
        tailscale_info = proxmox.get_stored_tailscale_info()
        
        # Display connection options
        output.print("[cyan]Connect with:[/cyan]")
        if actual_ip and actual_ip.lower() != 'dhcp':
            output.print(f"  • Local:     ssh root@{actual_ip}")
        else:
            output.print(f"  • Local:     ssh root@{container.hostname}")
            if not tailscale_info:
                output.info("Container may need a few moments for DHCP assignment")
        
        if tailscale_info:
            output.print(f"  • Tailscale: ssh root@{tailscale_info['fqdn']} [dim]({tailscale_info['ip']})[/dim]")

    except Exception as e:
        if ctx.obj.get('DEBUG'):
            raise
        output.error(str(e))
        sys.exit(1)