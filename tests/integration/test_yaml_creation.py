"""
Integration tests for container creation from YAML configuration.

This module validates the complete flow of loading a YAML configuration file
and creating a container with all settings from the file. Tests follow TDD
approach and will fail initially since the implementation doesn't exist yet.

The tests validate:
- Loading and parsing YAML configuration files
- Creating containers with YAML-defined settings
- Override parameter functionality
- Error handling for invalid YAML and configuration issues
- Integration between YAML config loader and Proxmox API services

Run with: pytest tests/integration/test_yaml_creation.py -v
"""

import json
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path
import yaml


class TestYamlContainerCreationIntegration:
    """Integration tests for container creation from YAML configuration."""

    @pytest.fixture
    def sample_yaml_config(self):
        """Sample YAML configuration for container creation."""
        return {
            'container': {
                'hostname': 'test-container',
                'node': 'pve-node-1',
                'template': 'ubuntu-22.04',
                'vmid': 1001,
                'resources': {
                    'cores': 2,
                    'memory': 2048,
                    'storage': 20
                },
                'network': {
                    'bridge': 'vmbr0',
                    'ip': 'dhcp'
                },
                'features': {
                    'nesting': True,
                    'keyctl': True
                }
            },
            'proxmox': {
                'storage': 'local-lvm',
                'ostemplate': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst'
            }
        }

    @pytest.fixture
    def sample_yaml_config_minimal(self):
        """Minimal YAML configuration with only required fields."""
        return {
            'container': {
                'hostname': 'minimal-container',
                'node': 'pve-node-1',
                'template': 'ubuntu-22.04'
            },
            'proxmox': {
                'storage': 'local-lvm',
                'ostemplate': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst'
            }
        }

    @pytest.fixture
    def override_parameters(self):
        """Override parameters to test parameter override functionality."""
        return {
            'hostname': 'overridden-container',
            'cores': 4,
            'memory': 4096,
            'node': 'pve-node-2'
        }

    @pytest.fixture
    def expected_proxmox_api_call(self, sample_yaml_config):
        """Expected parameters for Proxmox API call based on YAML config."""
        return {
            'vmid': 1001,
            'hostname': 'test-container',
            'ostemplate': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst',
            'storage': 'local-lvm',
            'cores': 2,
            'memory': 2048,
            'rootfs': 'local-lvm:20',
            'net0': 'name=eth0,bridge=vmbr0,ip=dhcp,type=veth',
            'features': 'nesting=1,keyctl=1',
            'unprivileged': True,
            'start': False
        }

    @pytest.fixture
    def expected_container_info_response(self):
        """Expected container info response after successful creation."""
        return {
            'vmid': 1001,
            'hostname': 'test-container',
            'node': 'pve-node-1',
            'status': 'created',
            'connection': {
                'ssh': 'ssh root@10.0.0.100',
                'ip': '10.0.0.100',
                'console': 'pct console 1001'
            },
            'resources': {
                'cores': 2,
                'memory': 2048,
                'storage': 20
            }
        }

    def test_yaml_config_loader_service_exists(self):
        """Test that the YAML config loader service can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader

    def test_yaml_container_creator_service_exists(self):
        """Test that the YAML container creator service can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

    def test_load_yaml_config_from_file_success(self, sample_yaml_config):
        """Test loading YAML configuration from file successfully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader

            yaml_content = yaml.dump(sample_yaml_config)

            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.exists', return_value=True):
                    loader = YamlConfigLoader()
                    config = loader.load_config('/path/to/config.yaml')

                    assert config == sample_yaml_config
                    assert config['container']['hostname'] == 'test-container'
                    assert config['container']['resources']['cores'] == 2

    def test_load_yaml_config_file_not_found(self):
        """Test error handling when YAML config file is not found."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader
            from src.services.yaml_config_loader import ConfigFileNotFoundError

            with patch('os.path.exists', return_value=False):
                loader = YamlConfigLoader()

                with pytest.raises(ConfigFileNotFoundError) as exc_info:
                    loader.load_config('/nonexistent/config.yaml')

                assert 'Config file not found' in str(exc_info.value)

    def test_load_yaml_config_invalid_yaml(self):
        """Test error handling when YAML file contains invalid syntax."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader
            from src.services.yaml_config_loader import InvalidYamlError

            invalid_yaml = "container:\n  hostname: test\n    invalid_indent: value"

            with patch('builtins.open', mock_open(read_data=invalid_yaml)):
                with patch('os.path.exists', return_value=True):
                    loader = YamlConfigLoader()

                    with pytest.raises(InvalidYamlError) as exc_info:
                        loader.load_config('/path/to/invalid.yaml')

                    assert 'Invalid YAML syntax' in str(exc_info.value)

    def test_validate_yaml_config_missing_required_fields(self):
        """Test validation error when required fields are missing from YAML config."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader
            from src.services.yaml_config_loader import ConfigValidationError

            incomplete_config = {
                'container': {
                    'hostname': 'test-container'
                    # Missing node, template, storage, ostemplate
                }
            }

            yaml_content = yaml.dump(incomplete_config)

            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.exists', return_value=True):
                    loader = YamlConfigLoader()

                    with pytest.raises(ConfigValidationError) as exc_info:
                        loader.load_config('/path/to/incomplete.yaml')

                    assert 'Missing required field' in str(exc_info.value)

    @patch('src.services.proxmox_lxc.ProxmoxLXCService')
    def test_create_container_from_yaml_config_success(self, mock_proxmox_service,
                                                     sample_yaml_config,
                                                     expected_proxmox_api_call,
                                                     expected_container_info_response):
        """Test successful container creation from complete YAML configuration."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

            # Mock YAML config loading
            yaml_content = yaml.dump(sample_yaml_config)

            # Mock Proxmox service responses
            mock_service_instance = Mock()
            mock_proxmox_service.return_value = mock_service_instance
            mock_service_instance.create_container.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"
            mock_service_instance.get_container_info.return_value = expected_container_info_response

            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.exists', return_value=True):
                    creator = YamlContainerCreator(
                        proxmox_host='pve.example.com',
                        proxmox_user='root@pam',
                        proxmox_password='secret'
                    )

                    result = creator.create_from_yaml('/path/to/config.yaml')

                    # Verify Proxmox service was called with correct parameters
                    mock_service_instance.create_container.assert_called_once_with(
                        'pve-node-1', expected_proxmox_api_call
                    )

                    # Verify result matches expected container info
                    assert result == expected_container_info_response
                    assert result['vmid'] == 1001
                    assert result['hostname'] == 'test-container'

    @patch('src.services.proxmox_lxc.ProxmoxLXCService')
    def test_create_container_from_yaml_with_overrides(self, mock_proxmox_service,
                                                     sample_yaml_config,
                                                     override_parameters):
        """Test container creation with override parameters applied."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

            yaml_content = yaml.dump(sample_yaml_config)

            # Mock Proxmox service
            mock_service_instance = Mock()
            mock_proxmox_service.return_value = mock_service_instance
            mock_service_instance.create_container.return_value = "UPID:pve-node-2:00001234:56789ABC:qmcreate:1001:root@pam:"

            expected_overridden_response = {
                'vmid': 1001,
                'hostname': 'overridden-container',
                'node': 'pve-node-2',
                'status': 'created',
                'connection': {
                    'ssh': 'ssh root@10.0.0.101',
                    'ip': '10.0.0.101',
                    'console': 'pct console 1001'
                },
                'resources': {
                    'cores': 4,
                    'memory': 4096,
                    'storage': 20
                }
            }
            mock_service_instance.get_container_info.return_value = expected_overridden_response

            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.exists', return_value=True):
                    creator = YamlContainerCreator(
                        proxmox_host='pve.example.com',
                        proxmox_user='root@pam',
                        proxmox_password='secret'
                    )

                    result = creator.create_from_yaml(
                        '/path/to/config.yaml',
                        overrides=override_parameters
                    )

                    # Verify override parameters were applied
                    call_args = mock_service_instance.create_container.call_args
                    actual_node = call_args[0][0]
                    actual_params = call_args[0][1]

                    assert actual_node == 'pve-node-2'  # Override applied
                    assert actual_params['hostname'] == 'overridden-container'  # Override applied
                    assert actual_params['cores'] == 4  # Override applied
                    assert actual_params['memory'] == 4096  # Override applied

                    # Verify result reflects overrides
                    assert result['hostname'] == 'overridden-container'
                    assert result['node'] == 'pve-node-2'
                    assert result['resources']['cores'] == 4

    @patch('src.services.proxmox_lxc.ProxmoxLXCService')
    def test_create_container_from_minimal_yaml_config(self, mock_proxmox_service,
                                                     sample_yaml_config_minimal):
        """Test container creation from minimal YAML configuration with defaults."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

            yaml_content = yaml.dump(sample_yaml_config_minimal)

            # Mock Proxmox service
            mock_service_instance = Mock()
            mock_proxmox_service.return_value = mock_service_instance
            mock_service_instance.create_container.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1002:root@pam:"

            expected_minimal_response = {
                'vmid': 1002,
                'hostname': 'minimal-container',
                'node': 'pve-node-1',
                'status': 'created',
                'connection': {
                    'ssh': 'ssh root@10.0.0.102',
                    'ip': '10.0.0.102',
                    'console': 'pct console 1002'
                },
                'resources': {
                    'cores': 1,  # Default value
                    'memory': 1024,  # Default value
                    'storage': 10  # Default value
                }
            }
            mock_service_instance.get_container_info.return_value = expected_minimal_response

            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.exists', return_value=True):
                    creator = YamlContainerCreator(
                        proxmox_host='pve.example.com',
                        proxmox_user='root@pam',
                        proxmox_password='secret'
                    )

                    result = creator.create_from_yaml('/path/to/minimal.yaml')

                    # Verify default values were applied
                    call_args = mock_service_instance.create_container.call_args[0][1]
                    assert call_args['cores'] == 1  # Default
                    assert call_args['memory'] == 1024  # Default
                    assert call_args['hostname'] == 'minimal-container'

    @patch('src.services.proxmox_lxc.ProxmoxLXCService')
    def test_create_container_dry_run_mode(self, mock_proxmox_service, sample_yaml_config):
        """Test dry run mode validates configuration without creating container."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

            yaml_content = yaml.dump(sample_yaml_config)

            # Mock Proxmox service (should not be called in dry run)
            mock_service_instance = Mock()
            mock_proxmox_service.return_value = mock_service_instance

            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.exists', return_value=True):
                    creator = YamlContainerCreator(
                        proxmox_host='pve.example.com',
                        proxmox_user='root@pam',
                        proxmox_password='secret'
                    )

                    result = creator.create_from_yaml(
                        '/path/to/config.yaml',
                        dry_run=True
                    )

                    # Verify no actual container creation was attempted
                    mock_service_instance.create_container.assert_not_called()

                    # Verify dry run result
                    assert result['dry_run'] == True
                    assert result['validation_status'] == 'passed'
                    assert 'would_create' in result
                    assert result['would_create']['hostname'] == 'test-container'

    @patch('src.services.proxmox_lxc.ProxmoxLXCService')
    def test_create_container_proxmox_api_error(self, mock_proxmox_service, sample_yaml_config):
        """Test error handling when Proxmox API call fails."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator
            from src.services.yaml_container_creator import ContainerCreationError
            from proxmoxer import ProxmoxAPIException

            yaml_content = yaml.dump(sample_yaml_config)

            # Mock Proxmox service to raise exception
            mock_service_instance = Mock()
            mock_proxmox_service.return_value = mock_service_instance
            mock_service_instance.create_container.side_effect = ProxmoxAPIException(
                "400 Bad Request: VMID 1001 already exists"
            )

            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('os.path.exists', return_value=True):
                    creator = YamlContainerCreator(
                        proxmox_host='pve.example.com',
                        proxmox_user='root@pam',
                        proxmox_password='secret'
                    )

                    with pytest.raises(ContainerCreationError) as exc_info:
                        creator.create_from_yaml('/path/to/config.yaml')

                    assert 'VMID 1001 already exists' in str(exc_info.value)

    def test_yaml_config_conversion_to_proxmox_params(self):
        """Test conversion of YAML config to Proxmox API parameters."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

            yaml_config = {
                'container': {
                    'hostname': 'test-container',
                    'node': 'pve-node-1',
                    'template': 'ubuntu-22.04',
                    'vmid': 1001,
                    'resources': {
                        'cores': 2,
                        'memory': 2048,
                        'storage': 20
                    },
                    'network': {
                        'bridge': 'vmbr0',
                        'ip': 'dhcp'
                    },
                    'features': {
                        'nesting': True,
                        'keyctl': False
                    }
                },
                'proxmox': {
                    'storage': 'local-lvm',
                    'ostemplate': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst'
                }
            }

            creator = YamlContainerCreator(
                proxmox_host='pve.example.com',
                proxmox_user='root@pam',
                proxmox_password='secret'
            )

            params = creator._convert_yaml_to_proxmox_params(yaml_config)

            assert params['vmid'] == 1001
            assert params['hostname'] == 'test-container'
            assert params['ostemplate'] == 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst'
            assert params['storage'] == 'local-lvm'
            assert params['cores'] == 2
            assert params['memory'] == 2048
            assert params['rootfs'] == 'local-lvm:20'
            assert params['net0'] == 'name=eth0,bridge=vmbr0,ip=dhcp,type=veth'
            assert params['features'] == 'nesting=1,keyctl=0'

    def test_apply_overrides_to_yaml_config(self, sample_yaml_config, override_parameters):
        """Test applying override parameters to loaded YAML configuration."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

            creator = YamlContainerCreator(
                proxmox_host='pve.example.com',
                proxmox_user='root@pam',
                proxmox_password='secret'
            )

            modified_config = creator._apply_overrides(sample_yaml_config, override_parameters)

            # Verify overrides were applied
            assert modified_config['container']['hostname'] == 'overridden-container'
            assert modified_config['container']['node'] == 'pve-node-2'
            assert modified_config['container']['resources']['cores'] == 4
            assert modified_config['container']['resources']['memory'] == 4096

            # Verify non-overridden values remain unchanged
            assert modified_config['container']['template'] == 'ubuntu-22.04'
            assert modified_config['container']['resources']['storage'] == 20

    def test_integration_end_to_end_yaml_creation_flow(self):
        """Test complete end-to-end flow from YAML file to container creation."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_container_creator import YamlContainerCreator

            # This test represents the complete integration flow:
            # 1. Load YAML config file
            # 2. Validate configuration
            # 3. Apply any overrides
            # 4. Convert to Proxmox API parameters
            # 5. Create container via Proxmox API
            # 6. Return container information

            # Mock the entire flow
            with patch('builtins.open'):
                with patch('os.path.exists', return_value=True):
                    with patch('yaml.safe_load'):
                        with patch('src.services.proxmox_lxc.ProxmoxLXCService'):
                            creator = YamlContainerCreator(
                                proxmox_host='pve.example.com',
                                proxmox_user='root@pam',
                                proxmox_password='secret'
                            )

                            # This should orchestrate the complete flow
                            result = creator.create_from_yaml(
                                '/path/to/config.yaml',
                                overrides={'hostname': 'integration-test'},
                                dry_run=False
                            )

                            # The result should be a ContainerInfo object
                            assert 'vmid' in result
                            assert 'hostname' in result
                            assert 'status' in result


class TestYamlConfigStructureValidation:
    """Tests for YAML configuration structure validation."""

    def test_valid_yaml_config_structure(self):
        """Test that valid YAML config structure passes validation."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader

            valid_config = {
                'container': {
                    'hostname': 'test-container',
                    'node': 'pve-node-1',
                    'template': 'ubuntu-22.04'
                },
                'proxmox': {
                    'storage': 'local-lvm',
                    'ostemplate': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst'
                }
            }

            loader = YamlConfigLoader()
            is_valid = loader.validate_config_structure(valid_config)
            assert is_valid == True

    def test_invalid_yaml_config_structure_missing_sections(self):
        """Test that YAML config missing required sections fails validation."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader
            from src.services.yaml_config_loader import ConfigValidationError

            invalid_config = {
                'container': {
                    'hostname': 'test-container'
                }
                # Missing 'proxmox' section
            }

            loader = YamlConfigLoader()

            with pytest.raises(ConfigValidationError) as exc_info:
                loader.validate_config_structure(invalid_config)

            assert 'Missing required section: proxmox' in str(exc_info.value)

    def test_yaml_config_with_optional_sections(self):
        """Test YAML config validation with optional sections."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.yaml_config_loader import YamlConfigLoader

            config_with_optional = {
                'container': {
                    'hostname': 'test-container',
                    'node': 'pve-node-1',
                    'template': 'ubuntu-22.04',
                    'resources': {
                        'cores': 2,
                        'memory': 2048,
                        'storage': 20
                    },
                    'network': {
                        'bridge': 'vmbr0',
                        'ip': 'dhcp'
                    },
                    'features': {
                        'nesting': True
                    }
                },
                'proxmox': {
                    'storage': 'local-lvm',
                    'ostemplate': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst'
                },
                'provisioning': {
                    'scripts': [
                        'setup-base.sh',
                        'install-docker.sh'
                    ],
                    'packages': [
                        'curl',
                        'vim',
                        'git'
                    ]
                }
            }

            loader = YamlConfigLoader()
            is_valid = loader.validate_config_structure(config_with_optional)
            assert is_valid == True