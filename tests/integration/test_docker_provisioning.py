"""
Integration tests for Docker provisioning functionality.

This module tests the automatic Docker installation during container provisioning
as specified in FR-012. Tests follow TDD approach and use mocks to simulate
SSH connections and pct exec commands.

The tests validate:
- Docker installation command sequence via SSH to Proxmox node
- Proper error handling for failed installations
- Correct pct exec command formatting and execution
- Integration with container provisioning workflow

Run with: pytest tests/integration/test_docker_provisioning.py -v
"""

import pytest
from unittest.mock import Mock, patch, call, MagicMock
import paramiko

# These imports will fail until implementation exists (TDD)
try:
    from src.services.provisioning import DockerProvisioningService
    from src.models.container_config import ContainerConfig
    from src.exceptions import ProvisioningError, SSHConnectionError
except ImportError:
    # Expected to fail in TDD approach
    DockerProvisioningService = None
    ContainerConfig = None
    ProvisioningError = Exception
    SSHConnectionError = Exception


class TestDockerProvisioningIntegration:
    """Integration tests for Docker provisioning service."""

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client for testing provisioning commands."""
        ssh_client = Mock(spec=paramiko.SSHClient)

        # Mock successful connection
        ssh_client.connect.return_value = None

        # Mock successful command execution
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        # Default to successful command execution
        mock_stdout.read.return_value = b"Docker installed successfully\n"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr.read.return_value = b""

        ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        return ssh_client

    @pytest.fixture
    def container_config(self):
        """Sample container configuration for testing."""
        return ContainerConfig(
            vmid=1001,
            hostname="test-docker-container",
            node="pve-node-1",
            template="debian-12-standard",
            cores=2,
            memory=2048,
            storage=20,
            enable_docker=True
        )

    @pytest.fixture
    def provisioning_service(self, mock_ssh_client):
        """Docker provisioning service with mocked SSH client."""
        with patch('src.services.provisioning.paramiko.SSHClient', return_value=mock_ssh_client):
            service = DockerProvisioningService(
                proxmox_host="pve.example.com",
                ssh_user="root",
                ssh_key_path="/path/to/key"
            )
            service._ssh_client = mock_ssh_client
            return service

    def test_docker_installation_success(self, provisioning_service, mock_ssh_client, container_config):
        """Test successful Docker installation via pct exec commands."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Execute Docker provisioning
            result = provisioning_service.provision_docker(container_config)

            # Verify SSH connection was established
            mock_ssh_client.connect.assert_called_once_with(
                hostname="pve.example.com",
                username="root",
                key_filename="/path/to/key",
                timeout=30
            )

            # Verify expected pct exec commands were executed in correct order
            expected_commands = [
                # Update package lists
                call('pct exec 1001 -- apt-get update'),

                # Install prerequisites
                call('pct exec 1001 -- apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release'),

                # Add Docker GPG key
                call('pct exec 1001 -- curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg'),

                # Add Docker repository
                call('pct exec 1001 -- echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null'),

                # Update package lists again
                call('pct exec 1001 -- apt-get update'),

                # Install Docker
                call('pct exec 1001 -- apt-get install -y docker-ce docker-ce-cli containerd.io'),

                # Start and enable Docker service
                call('pct exec 1001 -- systemctl enable docker'),
                call('pct exec 1001 -- systemctl start docker'),

                # Verify Docker installation
                call('pct exec 1001 -- docker --version')
            ]

            mock_ssh_client.exec_command.assert_has_calls(expected_commands, any_order=False)

            # Verify result indicates success
            assert result['status'] == 'success'
            assert result['service'] == 'docker'
            assert 'docker_version' in result

    def test_docker_installation_package_update_failure(self, provisioning_service, mock_ssh_client, container_config):
        """Test handling of package update failure during Docker installation."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Mock failed apt-get update command
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.read.return_value = b""
            mock_stdout.channel.recv_exit_status.return_value = 1
            mock_stderr.read.return_value = b"Failed to fetch package lists\n"

            mock_ssh_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

            # Expect ProvisioningError to be raised
            with pytest.raises(ProvisioningError) as exc_info:
                provisioning_service.provision_docker(container_config)

            assert "Failed to update package lists" in str(exc_info.value)
            assert exc_info.value.exit_code == 1

    def test_docker_installation_docker_install_failure(self, provisioning_service, mock_ssh_client, container_config):
        """Test handling of Docker installation failure."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Mock successful commands until Docker install fails
            def mock_exec_command(command):
                mock_stdout = Mock()
                mock_stderr = Mock()

                if 'apt-get install -y docker-ce' in command:
                    # Simulate Docker installation failure
                    mock_stdout.read.return_value = b""
                    mock_stdout.channel.recv_exit_status.return_value = 1
                    mock_stderr.read.return_value = b"Package docker-ce is not available\n"
                else:
                    # Other commands succeed
                    mock_stdout.read.return_value = b"Success\n"
                    mock_stdout.channel.recv_exit_status.return_value = 0
                    mock_stderr.read.return_value = b""

                return (Mock(), mock_stdout, mock_stderr)

            mock_ssh_client.exec_command.side_effect = mock_exec_command

            # Expect ProvisioningError to be raised
            with pytest.raises(ProvisioningError) as exc_info:
                provisioning_service.provision_docker(container_config)

            assert "Docker installation failed" in str(exc_info.value)
            assert exc_info.value.exit_code == 1

    def test_docker_installation_service_start_failure(self, provisioning_service, mock_ssh_client, container_config):
        """Test handling of Docker service start failure."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Mock successful commands until service start fails
            def mock_exec_command(command):
                mock_stdout = Mock()
                mock_stderr = Mock()

                if 'systemctl start docker' in command:
                    # Simulate service start failure
                    mock_stdout.read.return_value = b""
                    mock_stdout.channel.recv_exit_status.return_value = 1
                    mock_stderr.read.return_value = b"Failed to start docker.service\n"
                else:
                    # Other commands succeed
                    mock_stdout.read.return_value = b"Success\n"
                    mock_stdout.channel.recv_exit_status.return_value = 0
                    mock_stderr.read.return_value = b""

                return (Mock(), mock_stdout, mock_stderr)

            mock_ssh_client.exec_command.side_effect = mock_exec_command

            # Expect ProvisioningError to be raised
            with pytest.raises(ProvisioningError) as exc_info:
                provisioning_service.provision_docker(container_config)

            assert "Failed to start Docker service" in str(exc_info.value)

    def test_ssh_connection_failure(self, provisioning_service, mock_ssh_client, container_config):
        """Test handling of SSH connection failure."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Mock SSH connection failure
            mock_ssh_client.connect.side_effect = paramiko.SSHException("Connection failed")

            # Expect SSHConnectionError to be raised
            with pytest.raises(SSHConnectionError) as exc_info:
                provisioning_service.provision_docker(container_config)

            assert "Failed to connect to Proxmox node" in str(exc_info.value)
            assert "pve.example.com" in str(exc_info.value)

    def test_docker_version_verification(self, provisioning_service, mock_ssh_client, container_config):
        """Test Docker version verification after installation."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Mock Docker version command output
            def mock_exec_command(command):
                mock_stdout = Mock()
                mock_stderr = Mock()
                mock_stderr.read.return_value = b""

                if 'docker --version' in command:
                    mock_stdout.read.return_value = b"Docker version 24.0.6, build ed223bc\n"
                    mock_stdout.channel.recv_exit_status.return_value = 0
                else:
                    mock_stdout.read.return_value = b"Success\n"
                    mock_stdout.channel.recv_exit_status.return_value = 0

                return (Mock(), mock_stdout, mock_stderr)

            mock_ssh_client.exec_command.side_effect = mock_exec_command

            result = provisioning_service.provision_docker(container_config)

            # Verify Docker version is captured
            assert result['docker_version'] == "Docker version 24.0.6, build ed223bc"

    def test_container_not_docker_enabled(self, provisioning_service, container_config):
        """Test that Docker provisioning is skipped when not enabled in config."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Disable Docker in container config
            container_config.enable_docker = False

            result = provisioning_service.provision_docker(container_config)

            # Verify Docker provisioning is skipped
            assert result['status'] == 'skipped'
            assert result['reason'] == 'Docker not enabled in container configuration'

    def test_ubuntu_container_docker_installation(self, provisioning_service, mock_ssh_client, container_config):
        """Test Docker installation on Ubuntu container uses correct commands."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Set Ubuntu template
            container_config.template = "ubuntu-22.04-standard"

            result = provisioning_service.provision_docker(container_config)

            # Verify Ubuntu-specific commands are used
            expected_ubuntu_commands = [
                call('pct exec 1001 -- apt-get update'),
                call('pct exec 1001 -- apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release'),
                call('pct exec 1001 -- curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg'),
                call('pct exec 1001 -- echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null'),
            ]

            # Check that Ubuntu GPG key and repo are used instead of Debian
            mock_ssh_client.exec_command.assert_any_call('pct exec 1001 -- curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg')

    @pytest.mark.parametrize("template,expected_distro", [
        ("debian-12-standard", "debian"),
        ("ubuntu-22.04-standard", "ubuntu"),
        ("ubuntu-20.04-standard", "ubuntu"),
        ("debian-11-standard", "debian"),
    ])
    def test_docker_installation_distro_detection(self, provisioning_service, mock_ssh_client, container_config, template, expected_distro):
        """Test that Docker installation detects correct distribution from template."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            container_config.template = template

            result = provisioning_service.provision_docker(container_config)

            # Verify correct GPG key URL is used based on distribution
            expected_gpg_url = f"https://download.docker.com/linux/{expected_distro}/gpg"

            # Find the GPG key command in the call list
            gpg_command_found = False
            for call_args in mock_ssh_client.exec_command.call_args_list:
                command = call_args[0][0]
                if expected_gpg_url in command:
                    gpg_command_found = True
                    break

            assert gpg_command_found, f"Expected GPG URL {expected_gpg_url} not found in commands"

    def test_docker_installation_with_privileged_container(self, provisioning_service, mock_ssh_client, container_config):
        """Test Docker installation in privileged container (required for Docker)."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Set privileged mode (required for Docker)
            container_config.privileged = True

            result = provisioning_service.provision_docker(container_config)

            # Verify installation proceeds without privilege warnings
            assert result['status'] == 'success'

    def test_docker_installation_non_privileged_container_warning(self, provisioning_service, container_config):
        """Test warning when attempting Docker installation in non-privileged container."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            # Set non-privileged mode
            container_config.privileged = False

            with pytest.raises(ProvisioningError) as exc_info:
                provisioning_service.provision_docker(container_config)

            assert "Docker requires privileged container" in str(exc_info.value)
            assert "Consider setting privileged=true" in str(exc_info.value)


class TestDockerProvisioningCommandGeneration:
    """Test correct generation of Docker installation commands."""

    @pytest.fixture
    def provisioning_service(self):
        """Docker provisioning service for command generation testing."""
        # This will fail until the service is implemented
        with pytest.raises(ImportError):
            return DockerProvisioningService(
                proxmox_host="pve.example.com",
                ssh_user="root",
                ssh_key_path="/path/to/key"
            )

    def test_generate_debian_docker_commands(self, provisioning_service):
        """Test generation of Docker installation commands for Debian."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            commands = provisioning_service._generate_docker_commands(
                vmid=1001,
                distribution="debian"
            )

            expected_commands = [
                'pct exec 1001 -- apt-get update',
                'pct exec 1001 -- apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release',
                'pct exec 1001 -- curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg',
                'pct exec 1001 -- echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null',
                'pct exec 1001 -- apt-get update',
                'pct exec 1001 -- apt-get install -y docker-ce docker-ce-cli containerd.io',
                'pct exec 1001 -- systemctl enable docker',
                'pct exec 1001 -- systemctl start docker',
                'pct exec 1001 -- docker --version'
            ]

            assert commands == expected_commands

    def test_generate_ubuntu_docker_commands(self, provisioning_service):
        """Test generation of Docker installation commands for Ubuntu."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            commands = provisioning_service._generate_docker_commands(
                vmid=1001,
                distribution="ubuntu"
            )

            # Verify Ubuntu-specific GPG key and repository URLs are used
            assert any('https://download.docker.com/linux/ubuntu/gpg' in cmd for cmd in commands)
            assert any('https://download.docker.com/linux/ubuntu' in cmd for cmd in commands)

    def test_detect_distribution_from_template(self, provisioning_service):
        """Test distribution detection from container template name."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            test_cases = [
                ("debian-12-standard", "debian"),
                ("ubuntu-22.04-standard", "ubuntu"),
                ("ubuntu-20.04-standard", "ubuntu"),
                ("debian-11-standard", "debian"),
                ("custom-debian-template", "debian"),
                ("my-ubuntu-template", "ubuntu"),
            ]

            for template, expected_distro in test_cases:
                detected = provisioning_service._detect_distribution(template)
                assert detected == expected_distro, f"Failed to detect {expected_distro} from {template}"

    def test_unsupported_distribution_raises_error(self, provisioning_service):
        """Test that unsupported distributions raise appropriate error."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            with pytest.raises(ProvisioningError) as exc_info:
                provisioning_service._detect_distribution("centos-8-standard")

            assert "Unsupported distribution" in str(exc_info.value)
            assert "centos" in str(exc_info.value)


class TestDockerProvisioningSSHIntegration:
    """Test SSH integration for Docker provisioning commands."""

    @pytest.fixture
    def real_ssh_config(self):
        """Real SSH configuration for integration testing."""
        return {
            'hostname': 'test-pve.example.com',
            'username': 'root',
            'key_filename': '/tmp/test_ssh_key',
            'timeout': 30
        }

    @patch('src.services.provisioning.paramiko.SSHClient')
    def test_ssh_connection_parameters(self, mock_ssh_class):
        """Test that SSH connection uses correct parameters."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            mock_ssh_client = Mock()
            mock_ssh_class.return_value = mock_ssh_client

            service = DockerProvisioningService(
                proxmox_host="pve.example.com",
                ssh_user="root",
                ssh_key_path="/path/to/key"
            )

            # Trigger SSH connection
            container_config = Mock()
            container_config.vmid = 1001
            container_config.enable_docker = True
            container_config.privileged = True

            service.provision_docker(container_config)

            # Verify SSH connection parameters
            mock_ssh_client.connect.assert_called_once_with(
                hostname="pve.example.com",
                username="root",
                key_filename="/path/to/key",
                timeout=30
            )

    @patch('src.services.provisioning.paramiko.SSHClient')
    def test_ssh_command_execution_timeout(self, mock_ssh_class):
        """Test SSH command execution with proper timeout handling."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            mock_ssh_client = Mock()
            mock_ssh_class.return_value = mock_ssh_client

            # Mock command timeout
            mock_ssh_client.exec_command.side_effect = paramiko.SSHException("Command timeout")

            service = DockerProvisioningService(
                proxmox_host="pve.example.com",
                ssh_user="root",
                ssh_key_path="/path/to/key"
            )

            container_config = Mock()
            container_config.vmid = 1001
            container_config.enable_docker = True
            container_config.privileged = True

            with pytest.raises(ProvisioningError) as exc_info:
                service.provision_docker(container_config)

            assert "Command timeout" in str(exc_info.value)

    @patch('src.services.provisioning.paramiko.SSHClient')
    def test_ssh_connection_cleanup(self, mock_ssh_class):
        """Test that SSH connection is properly cleaned up after provisioning."""
        # This test will initially fail until DockerProvisioningService is implemented
        with pytest.raises(ImportError):
            mock_ssh_client = Mock()
            mock_ssh_class.return_value = mock_ssh_client

            service = DockerProvisioningService(
                proxmox_host="pve.example.com",
                ssh_user="root",
                ssh_key_path="/path/to/key"
            )

            container_config = Mock()
            container_config.vmid = 1001
            container_config.enable_docker = True
            container_config.privileged = True

            # Mock successful command execution
            mock_stdout = Mock()
            mock_stdout.read.return_value = b"Success\n"
            mock_stdout.channel.recv_exit_status.return_value = 0
            mock_stderr = Mock()
            mock_stderr.read.return_value = b""
            mock_ssh_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

            service.provision_docker(container_config)

            # Verify SSH connection is closed
            mock_ssh_client.close.assert_called_once()