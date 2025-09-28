"""Configuration manager for YAML config files."""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

import yaml

from src.models.container import Container
from src.models.provisioning import ProvisioningConfig, ProvisioningScript
from src.models.tailscale import TailscaleConfig
from src.models.user import UserConfig
from src.models.mount import MountPoint, Device

logger = logging.getLogger(__name__)


class ConfigManager:
    """Service for managing YAML configuration files."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize config manager.

        Args:
            config_dir: Directory for config files (default: ~/.pxrun)
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".pxrun"

        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self, filepath: str) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Args:
            filepath: Path to YAML config file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        config_path = Path(filepath)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Validate basic structure
            if not isinstance(config, dict):
                raise ValueError("Config must be a dictionary")

            # Validate version
            version = config.get('version', '1.0')
            if version != '1.0':
                logger.warning(f"Unknown config version: {version}")

            logger.info(f"Loaded config from {filepath}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def save_config(self, config: Dict[str, Any], filepath: str):
        """Save configuration to YAML file.

        Args:
            config: Configuration dictionary
            filepath: Path to save YAML file
        """
        config_path = Path(filepath)

        # Create parent directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved config to {filepath}")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def parse_container_config(self, config: Dict[str, Any]) -> Container:
        """Parse container configuration from config dict.

        Args:
            config: Configuration dictionary

        Returns:
            Container object

        Raises:
            ValueError: If configuration is invalid
        """
        container_config = config.get('container', {})

        # Get basic container settings
        hostname = container_config.get('hostname')
        if not hostname:
            raise ValueError("Container hostname is required")

        template = container_config.get('template')
        if not template:
            raise ValueError("Container template is required")

        # Expand template shorthand if needed
        if not ':' in template:
            # Try to find full template path - would need API access
            # For now, assume local:vztmpl/ prefix
            template = f"local:vztmpl/{template}"

        # Get resource settings (check both direct and nested locations)
        resources = container_config.get('resources', {})
        cores = container_config.get('cores', resources.get('cores', 2))
        memory = container_config.get('memory', resources.get('memory', 1024))
        storage = container_config.get('storage', resources.get('storage', 10))

        # Get network settings (check both direct and nested locations)
        network = container_config.get('network', {})
        bridge = container_config.get('network_bridge', network.get('bridge', 'vmbr0'))
        ip = container_config.get('network_ip', network.get('ip'))
        gateway = container_config.get('network_gateway', network.get('gateway'))

        # Get features
        features = container_config.get('features', {})

        # Parse mount points
        mount_points = []
        for mp_config in container_config.get('mount_points', []):
            mp_id = f"mp{len(mount_points)}"
            mount_point = MountPoint(
                id=mp_id,
                host_path=mp_config['host'],
                container_path=mp_config['container'],
                read_only=mp_config.get('read_only', False),
                size=mp_config.get('size'),
                backup=mp_config.get('backup', True)
            )
            mount_points.append(mount_point)

        # Parse devices
        devices = []
        for dev_config in container_config.get('devices', []):
            device = Device(
                path=dev_config['path'],
                mode=dev_config.get('mode', 'rw'),
                uid=dev_config.get('uid', 0),
                gid=dev_config.get('gid', 0)
            )
            devices.append(device)

        # Parse provisioning if present
        provisioning = None
        if 'provisioning' in config:
            provisioning = self.parse_provisioning_config(config['provisioning'])

        # Create container object (vmid and node will be set later)
        container = Container(
            vmid=container_config.get('vmid', 0),  # Will be assigned if 0
            hostname=hostname,
            template=template,
            node=container_config.get('node', ''),  # Will be selected if empty
            cores=cores,
            memory=memory,
            storage=storage,
            storage_pool=container_config.get('storage_pool', resources.get('storage_pool', 'local-lvm')),
            network_bridge=bridge,
            network_ip=ip,
            network_gateway=gateway,
            start_on_boot=container_config.get('start_on_boot', False),
            unprivileged=container_config.get('unprivileged', True),
            features=features,
            mount_points=mount_points,
            devices=devices,
            provisioning=provisioning
        )

        return container

    def parse_provisioning_config(self, prov_config: Dict[str, Any]) -> ProvisioningConfig:
        """Parse provisioning configuration.

        Args:
            prov_config: Provisioning section of config

        Returns:
            ProvisioningConfig object
        """
        provisioning = ProvisioningConfig()

        # Parse packages
        provisioning.packages = prov_config.get('packages', [])

        # Parse Docker flag
        provisioning.docker = prov_config.get('docker', False)

        # Parse SSH keys
        provisioning.ssh_keys = prov_config.get('ssh_keys', [])

        # Parse Tailscale config
        if 'tailscale' in prov_config:
            provisioning.tailscale = TailscaleConfig.from_yaml(prov_config['tailscale'])

        # Parse users
        for user_data in prov_config.get('users', []):
            user = UserConfig.from_yaml(user_data)
            provisioning.users.append(user)

        # Parse scripts
        for script_data in prov_config.get('scripts', []):
            if isinstance(script_data, dict):
                script = ProvisioningScript(
                    name=script_data.get('name', 'unnamed'),
                    content=script_data.get('content', ''),
                    interpreter=script_data.get('interpreter', 'bash'),
                    run_as=script_data.get('run_as', 'root'),
                    working_dir=script_data.get('working_dir', '/root'),
                    environment=script_data.get('environment', {}),
                    timeout=script_data.get('timeout', 300),
                    continue_on_error=script_data.get('continue_on_error', False)
                )
                provisioning.scripts.append(script)

        return provisioning

    def export_container_config(self, container: Container,
                               provisioning: Optional[ProvisioningConfig] = None) -> Dict[str, Any]:
        """Export container configuration to dict.

        Args:
            container: Container object
            provisioning: Optional provisioning config

        Returns:
            Configuration dictionary
        """
        config = {
            'version': '1.0',
            'container': {
                'hostname': container.hostname,
                'template': container.template,
                'resources': {
                    'cores': container.cores,
                    'memory': container.memory,
                    'storage': container.storage,
                    'storage_pool': container.storage_pool
                },
                'network': {
                    'bridge': container.network_bridge
                }
            }
        }

        # Add optional container fields
        if container.vmid:
            config['container']['vmid'] = container.vmid

        if container.node:
            config['container']['node'] = container.node

        if container.network_ip:
            config['container']['network']['ip'] = container.network_ip

        if container.network_gateway:
            config['container']['network']['gateway'] = container.network_gateway

        if container.features:
            config['container']['features'] = container.features

        if container.start_on_boot:
            config['container']['start_on_boot'] = container.start_on_boot

        if not container.unprivileged:
            config['container']['unprivileged'] = False

        # Add mount points
        if container.mount_points:
            config['container']['mount_points'] = []
            for mp in container.mount_points:
                mp_config = {
                    'host': mp.host_path,
                    'container': mp.container_path
                }
                if mp.read_only:
                    mp_config['read_only'] = True
                if mp.size:
                    mp_config['size'] = mp.size
                if not mp.backup:
                    mp_config['backup'] = False
                config['container']['mount_points'].append(mp_config)

        # Add devices
        if container.devices:
            config['container']['devices'] = []
            for dev in container.devices:
                dev_config = {
                    'path': dev.path,
                    'mode': dev.mode
                }
                if dev.uid != 0:
                    dev_config['uid'] = dev.uid
                if dev.gid != 0:
                    dev_config['gid'] = dev.gid
                config['container']['devices'].append(dev_config)

        # Add provisioning
        if provisioning and provisioning.has_provisioning():
            prov_config = {}

            if provisioning.packages:
                prov_config['packages'] = provisioning.packages

            if provisioning.docker:
                prov_config['docker'] = True

            if provisioning.ssh_keys:
                prov_config['ssh_keys'] = provisioning.ssh_keys

            if provisioning.tailscale:
                prov_config['tailscale'] = {
                    'auth_key': provisioning.tailscale.auth_key
                }
                if provisioning.tailscale.hostname:
                    prov_config['tailscale']['hostname'] = provisioning.tailscale.hostname
                if provisioning.tailscale.accept_routes:
                    prov_config['tailscale']['accept_routes'] = True
                if provisioning.tailscale.advertise_routes:
                    prov_config['tailscale']['advertise_routes'] = provisioning.tailscale.advertise_routes
                if provisioning.tailscale.shields_up:
                    prov_config['tailscale']['shields_up'] = True

            if provisioning.users:
                prov_config['users'] = []
                for user in provisioning.users:
                    user_config = {
                        'username': user.username
                    }
                    if user.uid:
                        user_config['uid'] = user.uid
                    if user.gid:
                        user_config['gid'] = user.gid
                    if user.groups:
                        user_config['groups'] = user.groups
                    if user.shell != '/bin/bash':
                        user_config['shell'] = user.shell
                    if user.home != f"/home/{user.username}":
                        user_config['home'] = user.home
                    if user.ssh_keys:
                        user_config['ssh_keys'] = user.ssh_keys
                    prov_config['users'].append(user_config)

            if provisioning.scripts:
                prov_config['scripts'] = []
                for script in provisioning.scripts:
                    script_config = {
                        'name': script.name,
                        'content': script.content
                    }
                    if script.interpreter != 'bash':
                        script_config['interpreter'] = script.interpreter
                    if script.run_as != 'root':
                        script_config['run_as'] = script.run_as
                    if script.working_dir != '/root':
                        script_config['working_dir'] = script.working_dir
                    if script.environment:
                        script_config['environment'] = script.environment
                    if script.timeout != 300:
                        script_config['timeout'] = script.timeout
                    if script.continue_on_error:
                        script_config['continue_on_error'] = True
                    prov_config['scripts'].append(script_config)

            config['provisioning'] = prov_config

        return config

    def list_configs(self) -> List[str]:
        """List all saved configurations.

        Returns:
            List of config file names
        """
        configs = []
        for file in self.config_dir.glob("*.yaml"):
            configs.append(file.name)
        for file in self.config_dir.glob("*.yml"):
            configs.append(file.name)
        return sorted(configs)

    def get_config_path(self, name: str) -> Path:
        """Get full path for a config name.

        Args:
            name: Config name (without extension)

        Returns:
            Full path to config file
        """
        if not name.endswith('.yaml') and not name.endswith('.yml'):
            name += '.yaml'
        return self.config_dir / name