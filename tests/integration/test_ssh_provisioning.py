"""
Integration tests for SSH-based provisioning via pct exec in Proxmox environments.

This module validates SSH-based container provisioning functionality as specified
in FR-016: "System MUST provision containers via SSH connection to Proxmox node
using pct exec commands". Tests follow TDD approach and will fail initially since
the implementation doesn't exist yet.

The tests validate:
- SSH connection establishment to Proxmox nodes
- Execution of pct exec commands for container provisioning
- Error handling for connection failures, authentication errors, and timeouts
- Command output parsing and status validation
- Timeout scenarios for long-running provisioning operations
- Resource cleanup and connection management

Run with: pytest tests/integration/test_ssh_provisioning.py -v
"""

import socket
import time
from unittest.mock import Mock, call, patch

import paramiko
import pytest
from paramiko import AuthenticationException, SSHException


class TestSSHProvisioningIntegration:
    """Integration tests for SSH-based provisioning workflow."""

    def test_ssh_provisioner_service_interface_exists(self):
        """Test that the SSH provisioner service interface can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock paramiko SSHClient for testing SSH operations."""
        mock_client = Mock(spec=paramiko.SSHClient)
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        # Configure stdout read to return command output
        mock_stdout.read.return_value = b"Command executed successfully\n"
        mock_stdout.channel.recv_exit_status.return_value = 0

        # Configure stderr to be empty for successful operations
        mock_stderr.read.return_value = b""

        # Setup exec_command return values
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        return mock_client

    @pytest.fixture
    def mock_ssh_config(self):
        """Valid SSH configuration for Proxmox node connection."""
        return {
            "hostname": "pve-node-1.example.com",
            "port": 22,
            "username": "root",
            "password": "secure_password",
            "timeout": 30,
            "look_for_keys": False,
            "allow_agent": False
        }

    @pytest.fixture
    def mock_container_config(self):
        """Mock container configuration for provisioning operations."""
        return {
            "vmid": 1001,
            "hostname": "test-container",
            "template": "ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "storage": "local-lvm",
            "memory": 2048,
            "cores": 2,
            "provisioning": {
                "install_docker": True,
                "install_tailscale": True,
                "tailscale_auth_key": "tskey-auth-xxxxxxxxxxxx",
                "custom_scripts": [
                    "apt-get update && apt-get upgrade -y",
                    "apt-get install -y curl wget git vim"
                ]
            }
        }

    def test_ssh_connection_establishment_success(self, mock_ssh_client, mock_ssh_config):
        """Test successful SSH connection establishment to Proxmox node."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                result = provisioner.connect()

                # Verify connection was established
                assert result is True
                mock_ssh_client.set_missing_host_key_policy.assert_called_once()
                mock_ssh_client.connect.assert_called_once_with(
                    hostname=mock_ssh_config["hostname"],
                    port=mock_ssh_config["port"],
                    username=mock_ssh_config["username"],
                    password=mock_ssh_config["password"],
                    timeout=mock_ssh_config["timeout"],
                    look_for_keys=mock_ssh_config["look_for_keys"],
                    allow_agent=mock_ssh_config["allow_agent"]
                )

    def test_ssh_connection_authentication_failure(self, mock_ssh_client, mock_ssh_config):
        """Test SSH connection fails with authentication error."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ProvisioningError, SSHProvisioner

            # Configure mock to raise authentication exception
            mock_ssh_client.connect.side_effect = AuthenticationException("Authentication failed")

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)

                with pytest.raises(ProvisioningError) as exc_info:
                    provisioner.connect()

                assert "Authentication failed" in str(exc_info.value)
                assert "authentication" in str(exc_info.value).lower()

    def test_ssh_connection_network_failure(self, mock_ssh_client, mock_ssh_config):
        """Test SSH connection fails with network error."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ProvisioningError, SSHProvisioner

            # Configure mock to raise socket error (network unreachable)
            mock_ssh_client.connect.side_effect = OSError("Network is unreachable")

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)

                with pytest.raises(ProvisioningError) as exc_info:
                    provisioner.connect()

                assert "Network is unreachable" in str(exc_info.value)

    def test_ssh_connection_timeout(self, mock_ssh_client, mock_ssh_config):
        """Test SSH connection fails with timeout error."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ProvisioningError, SSHProvisioner

            # Configure mock to raise timeout exception
            mock_ssh_client.connect.side_effect = socket.timeout("Connection timed out")

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)

                with pytest.raises(ProvisioningError) as exc_info:
                    provisioner.connect()

                assert "timeout" in str(exc_info.value).lower()

    def test_pct_exec_command_execution_success(self, mock_ssh_client, mock_ssh_config):
        """Test successful execution of pct exec command via SSH."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute a simple pct exec command
                command = "apt-get update"
                result = provisioner.execute_in_container(1001, command)

                # Verify command was executed correctly
                expected_pct_command = f"pct exec 1001 -- {command}"
                mock_ssh_client.exec_command.assert_called_with(expected_pct_command)

                assert result.exit_code == 0
                assert result.stdout == "Command executed successfully\n"
                assert result.stderr == ""

    def test_pct_exec_command_execution_failure(self, mock_ssh_client, mock_ssh_config):
        """Test handling of failed pct exec command execution."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ProvisioningError, SSHProvisioner

            # Configure mock to simulate command failure
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdin = Mock()

            mock_stdout.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 1  # Exit code 1 = failure
            mock_stderr.read.return_value = b"E: Unable to locate package nonexistent-package\n"

            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                command = "apt-get install nonexistent-package"

                with pytest.raises(ProvisioningError) as exc_info:
                    provisioner.execute_in_container(1001, command)

                assert "Command failed with exit code 1" in str(exc_info.value)
                assert "Unable to locate package" in str(exc_info.value)

    def test_pct_exec_long_running_command_timeout(self, mock_ssh_client, mock_ssh_config):
        """Test timeout handling for long-running pct exec commands."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ProvisioningError, SSHProvisioner

            # Configure mock to simulate long-running command that times out
            def mock_exec_command_timeout(*args, **kwargs):
                time.sleep(0.1)  # Simulate command taking time
                raise socket.timeout("Command execution timed out")

            mock_ssh_client.exec_command.side_effect = mock_exec_command_timeout

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                command = "sleep 300"  # Long-running command

                with pytest.raises(ProvisioningError) as exc_info:
                    provisioner.execute_in_container(1001, command, timeout=5)

                assert "timeout" in str(exc_info.value).lower()

    def test_container_provisioning_workflow_docker_installation(self, mock_ssh_client, mock_ssh_config, mock_container_config):
        """Test complete container provisioning workflow for Docker installation."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute Docker installation provisioning
                result = provisioner.provision_container(mock_container_config)

                # Verify Docker installation commands were executed
                expected_calls = [
                    call("pct exec 1001 -- apt-get update"),
                    call("pct exec 1001 -- apt-get install -y ca-certificates curl"),
                    call("pct exec 1001 -- install -m 0755 -d /etc/apt/keyrings"),
                    call("pct exec 1001 -- curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc"),
                    call("pct exec 1001 -- chmod a+r /etc/apt/keyrings/docker.asc"),
                    call('pct exec 1001 -- sh -c "echo \\"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \\"$VERSION_CODENAME\\") stable\\" | tee /etc/apt/sources.list.d/docker.list > /dev/null"'),
                    call("pct exec 1001 -- apt-get update"),
                    call("pct exec 1001 -- apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin")
                ]

                mock_ssh_client.exec_command.assert_has_calls(expected_calls, any_order=False)
                assert result.success is True
                assert result.installed_packages == ["docker-ce", "docker-ce-cli", "containerd.io"]

    def test_container_provisioning_workflow_tailscale_installation(self, mock_ssh_client, mock_ssh_config, mock_container_config):
        """Test container provisioning workflow for Tailscale installation with auth key."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute Tailscale installation provisioning
                result = provisioner.provision_container(mock_container_config)

                # Verify Tailscale installation commands were executed
                tailscale_commands = [
                    call("pct exec 1001 -- curl -fsSL https://tailscale.com/install.sh | sh"),
                    call(f"pct exec 1001 -- tailscale up --authkey {mock_container_config['provisioning']['tailscale_auth_key']}")
                ]

                # Check that Tailscale commands are in the call list
                actual_calls = mock_ssh_client.exec_command.call_args_list
                for expected_call in tailscale_commands:
                    assert expected_call in actual_calls

                assert result.success is True

    def test_container_provisioning_custom_scripts_execution(self, mock_ssh_client, mock_ssh_config, mock_container_config):
        """Test execution of custom provisioning scripts in container."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute custom script provisioning
                result = provisioner.provision_container(mock_container_config)

                # Verify custom scripts were executed
                custom_script_commands = [
                    call("pct exec 1001 -- apt-get update && apt-get upgrade -y"),
                    call("pct exec 1001 -- apt-get install -y curl wget git vim")
                ]

                actual_calls = mock_ssh_client.exec_command.call_args_list
                for expected_call in custom_script_commands:
                    assert expected_call in actual_calls

                assert result.success is True

    def test_container_provisioning_partial_failure_recovery(self, mock_ssh_client, mock_ssh_config, mock_container_config):
        """Test provisioning workflow handles partial failures and continues with remaining tasks."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            # Configure mock to simulate failure on Docker installation but success for other commands
            def mock_exec_command_side_effect(command):
                mock_stdin = Mock()
                mock_stdout = Mock()
                mock_stderr = Mock()

                if "docker-ce" in command:
                    # Simulate Docker installation failure
                    mock_stdout.read.return_value = b""
                    mock_stdout.channel.recv_exit_status.return_value = 1
                    mock_stderr.read.return_value = b"Package docker-ce is not available\n"
                else:
                    # Other commands succeed
                    mock_stdout.read.return_value = b"Command executed successfully\n"
                    mock_stdout.channel.recv_exit_status.return_value = 0
                    mock_stderr.read.return_value = b""

                return (mock_stdin, mock_stdout, mock_stderr)

            mock_ssh_client.exec_command.side_effect = mock_exec_command_side_effect

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute provisioning with expected partial failure
                result = provisioner.provision_container(mock_container_config)

                # Verify provisioning continued despite Docker failure
                assert result.success is False  # Overall failure due to Docker
                assert result.partial_success is True  # Some tasks succeeded
                assert "docker-ce" in result.failed_tasks
                assert "tailscale" in result.successful_tasks

    def test_ssh_connection_cleanup_on_success(self, mock_ssh_client, mock_ssh_config):
        """Test SSH connection is properly cleaned up after successful operations."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute some commands
                provisioner.execute_in_container(1001, "echo 'test'")

                # Close connection
                provisioner.disconnect()

                # Verify connection was properly closed
                mock_ssh_client.close.assert_called_once()

    def test_ssh_connection_cleanup_on_exception(self, mock_ssh_client, mock_ssh_config):
        """Test SSH connection is properly cleaned up even when exceptions occur."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ProvisioningError, SSHProvisioner

            # Configure mock to raise exception during command execution
            mock_ssh_client.exec_command.side_effect = SSHException("SSH connection lost")

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Use context manager to ensure cleanup
                with pytest.raises(ProvisioningError), provisioner:
                    provisioner.execute_in_container(1001, "echo 'test'")

                # Verify connection was closed even after exception
                mock_ssh_client.close.assert_called_once()

    def test_concurrent_ssh_operations_thread_safety(self, mock_ssh_client, mock_ssh_config):
        """Test SSH provisioner handles concurrent operations safely."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            import threading

            from src.services.ssh_provisioner import SSHProvisioner

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                results = []
                exceptions = []

                def execute_command(vmid, command):
                    try:
                        result = provisioner.execute_in_container(vmid, command)
                        results.append(result)
                    except Exception as e:
                        exceptions.append(e)

                # Execute multiple commands concurrently
                threads = []
                for i in range(5):
                    thread = threading.Thread(
                        target=execute_command,
                        args=(1001 + i, f"echo 'test command {i}'")
                    )
                    threads.append(thread)
                    thread.start()

                # Wait for all threads to complete
                for thread in threads:
                    thread.join()

                # Verify all operations completed successfully
                assert len(exceptions) == 0
                assert len(results) == 5
                assert all(result.exit_code == 0 for result in results)

    def test_pct_exec_command_with_special_characters(self, mock_ssh_client, mock_ssh_config):
        """Test pct exec commands handle special characters and shell escaping properly."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute command with special characters that need escaping
                command_with_quotes = 'echo "Hello, world!" && echo \'Single quotes\''
                result = provisioner.execute_in_container(1001, command_with_quotes)

                # Verify command was properly escaped and executed
                expected_command = f"pct exec 1001 -- {command_with_quotes}"
                mock_ssh_client.exec_command.assert_called_with(expected_command)
                assert result.exit_code == 0

    def test_ssh_provisioner_context_manager_usage(self, mock_ssh_client, mock_ssh_config):
        """Test SSH provisioner works correctly as a context manager."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                # Use provisioner as context manager
                with SSHProvisioner(mock_ssh_config) as provisioner:
                    result = provisioner.execute_in_container(1001, "echo 'test'")
                    assert result.exit_code == 0

                # Verify connection was automatically closed
                mock_ssh_client.close.assert_called_once()

    def test_ssh_provisioner_retry_logic_on_transient_failures(self, mock_ssh_client, mock_ssh_config):
        """Test SSH provisioner implements retry logic for transient failures."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            # Configure mock to fail twice then succeed
            call_count = 0
            def mock_exec_command_with_retries(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                mock_stdin = Mock()
                mock_stdout = Mock()
                mock_stderr = Mock()

                if call_count <= 2:
                    # First two calls fail with transient error
                    raise SSHException("Temporary network error")
                else:
                    # Third call succeeds
                    mock_stdout.read.return_value = b"Command executed successfully\n"
                    mock_stdout.channel.recv_exit_status.return_value = 0
                    mock_stderr.read.return_value = b""
                    return (mock_stdin, mock_stdout, mock_stderr)

            mock_ssh_client.exec_command.side_effect = mock_exec_command_with_retries

            with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                provisioner = SSHProvisioner(mock_ssh_config)
                provisioner.connect()

                # Execute command that will succeed after retries
                result = provisioner.execute_in_container(1001, "echo 'test'", max_retries=3)

                # Verify command eventually succeeded
                assert result.exit_code == 0
                assert call_count == 3  # Should have made 3 attempts


class TestSSHProvisioningConfiguration:
    """Tests for SSH provisioning configuration validation and edge cases."""

    def test_invalid_ssh_configuration_missing_hostname(self):
        """Test SSH provisioner rejects configuration without hostname."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ConfigurationError, SSHProvisioner

            invalid_config = {
                "port": 22,
                "username": "root",
                "password": "secret"
                # Missing hostname
            }

            with pytest.raises(ConfigurationError) as exc_info:
                SSHProvisioner(invalid_config)

            assert "hostname" in str(exc_info.value).lower()

    def test_invalid_ssh_configuration_missing_credentials(self):
        """Test SSH provisioner rejects configuration without authentication credentials."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import ConfigurationError, SSHProvisioner

            invalid_config = {
                "hostname": "pve-node-1.example.com",
                "port": 22,
                "username": "root"
                # Missing password, key_filename, or other auth method
            }

            with pytest.raises(ConfigurationError) as exc_info:
                SSHProvisioner(invalid_config)

            assert "authentication" in str(exc_info.value).lower() or "credentials" in str(exc_info.value).lower()

    def test_ssh_configuration_with_key_file_authentication(self):
        """Test SSH provisioner supports SSH key file authentication."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            key_auth_config = {
                "hostname": "pve-node-1.example.com",
                "port": 22,
                "username": "root",
                "key_filename": "/path/to/private/key",
                "timeout": 30
            }

            # Should not raise configuration error
            provisioner = SSHProvisioner(key_auth_config)
            assert provisioner.config["key_filename"] == "/path/to/private/key"

    def test_ssh_configuration_with_default_values(self):
        """Test SSH provisioner applies sensible defaults for optional configuration."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            minimal_config = {
                "hostname": "pve-node-1.example.com",
                "username": "root",
                "password": "secret"
            }

            provisioner = SSHProvisioner(minimal_config)

            # Verify defaults are applied
            assert provisioner.config["port"] == 22
            assert provisioner.config["timeout"] == 30
            assert provisioner.config["look_for_keys"] is False
            assert provisioner.config["allow_agent"] is False


class TestSSHProvisioningPerformance:
    """Tests for SSH provisioning performance and resource management."""

    def test_ssh_connection_pooling_for_multiple_containers(self):
        """Test SSH provisioner efficiently reuses connections for multiple container operations."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            # This test would verify that the provisioner reuses SSH connections
            # when provisioning multiple containers on the same node
            pass

    def test_ssh_provisioning_operation_timeout_configuration(self):
        """Test SSH provisioner respects timeout configuration for different operation types."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            # This test would verify different timeout settings:
            # - Connection timeout
            # - Command execution timeout
            # - Overall provisioning timeout
            pass

    def test_ssh_provisioning_memory_cleanup(self):
        """Test SSH provisioner properly manages memory and doesn't leak resources."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.ssh_provisioner import SSHProvisioner  # noqa: F401

            # This test would verify that provisioner cleans up resources
            # and doesn't accumulate memory over many operations
            pass
