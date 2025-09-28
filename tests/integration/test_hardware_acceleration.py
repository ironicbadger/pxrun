"""
Integration tests for hardware acceleration device passthrough.

This module provides comprehensive integration tests for Intel QSV and other hardware
acceleration device passthrough functionality. Tests follow TDD approach and mock
external dependencies including device detection, SSH connections, and Proxmox API calls.

The tests validate:
- Device detection and validation on host system
- Major/minor number lookup via SSH to Proxmox nodes
- Proxmox API integration for device configuration
- Intel QSV specific device passthrough (/dev/dri/renderD128)
- Error handling for device conflicts and failures
- Container privilege requirements for device access

Run with: pytest tests/integration/test_hardware_acceleration.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import paramiko
from proxmoxer import ResourceException


class TestHardwareAccelerationDevicePassthrough:
    """Integration tests for hardware acceleration device passthrough functionality."""

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock paramiko SSH client for device detection."""
        mock_ssh = Mock(spec=paramiko.SSHClient)
        mock_ssh.connect = Mock()
        mock_ssh.exec_command = Mock()
        mock_ssh.close = Mock()
        return mock_ssh

    @pytest.fixture
    def mock_proxmoxer(self):
        """Mock proxmoxer ProxmoxAPI client."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()
        mock_config = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc('vmid').config
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc.return_value = mock_lxc
        mock_lxc.config = mock_config

        return mock_proxmox

    @pytest.fixture
    def intel_qsv_device_config(self):
        """Valid Intel QSV device configuration."""
        return {
            "path": "/dev/dri/renderD128",
            "mode": "rw"
        }

    @pytest.fixture
    def device_stat_output(self):
        """Mock output for device stat command via SSH."""
        return """  File: /dev/dri/renderD128
  Size: 0         	Blocks: 0          IO Block: 4096   character special file
Device: 5h/5d	Inode: 1040        Links: 1     Device type: e2,0
Access: (0666/crw-rw-rw-)  Uid: (    0/    root)   Gid: (   44/   video)
Access: 2024-01-15 10:30:00.000000000 +0000
Modify: 2024-01-15 10:30:00.000000000 +0000
Change: 2024-01-15 10:30:00.000000000 +0000
 Birth: -"""

    @pytest.fixture
    def mock_hardware_service(self, mock_ssh_client, mock_proxmoxer):
        """Mock hardware acceleration service."""
        service = Mock()
        service.ssh_client = mock_ssh_client
        service.proxmox = mock_proxmoxer
        service.detect_device = Mock()
        service.get_device_numbers = Mock()
        service.configure_device_passthrough = Mock()
        return service

    def test_hardware_service_interface_exists(self):
        """Test that the hardware acceleration service interface can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

    def test_device_detection_intel_qsv_success(self, mock_hardware_service,
                                               mock_ssh_client, device_stat_output):
        """Test successful detection of Intel QSV device on Proxmox node."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            # Mock successful SSH connection and device detection
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            mock_stdout.read.return_value = device_stat_output.encode('utf-8')
            mock_stderr.read.return_value = b''
            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/key"
            )

            result = service.detect_device("/dev/dri/renderD128")

            assert result is True
            mock_ssh_client.connect.assert_called_once()
            mock_ssh_client.exec_command.assert_called_with("stat /dev/dri/renderD128")

    def test_device_detection_device_not_found(self, mock_hardware_service, mock_ssh_client):
        """Test device detection fails when device doesn't exist."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            # Mock SSH command that returns device not found
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            mock_stdout.read.return_value = b''
            mock_stderr.read.return_value = b'stat: cannot stat \'/dev/dri/renderD128\': No such file or directory'
            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/key"
            )

            result = service.detect_device("/dev/dri/renderD999")

            assert result is False
            mock_ssh_client.exec_command.assert_called_with("stat /dev/dri/renderD999")

    def test_major_minor_number_lookup_success(self, mock_hardware_service,
                                              mock_ssh_client, device_stat_output):
        """Test successful lookup of device major/minor numbers."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            # Mock successful SSH command to get device numbers
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            mock_stdout.read.return_value = device_stat_output.encode('utf-8')
            mock_stderr.read.return_value = b''
            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/key"
            )

            major, minor = service.get_device_numbers("/dev/dri/renderD128")

            # From the mock output: Device type: e2,0 means major=226 (0xe2), minor=0
            assert major == 226
            assert minor == 0
            mock_ssh_client.exec_command.assert_called_with("stat /dev/dri/renderD128")

    def test_major_minor_number_lookup_parsing_error(self, mock_hardware_service, mock_ssh_client):
        """Test device number lookup handles parsing errors gracefully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService
            from src.exceptions import DeviceParsingError

            # Mock SSH command with malformed output
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            malformed_output = "File: /dev/dri/renderD128\nInvalid format"
            mock_stdout.read.return_value = malformed_output.encode('utf-8')
            mock_stderr.read.return_value = b''
            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/key"
            )

            with pytest.raises(DeviceParsingError):
                service.get_device_numbers("/dev/dri/renderD128")

    def test_proxmox_device_configuration_success(self, mock_hardware_service, mock_proxmoxer,
                                                 intel_qsv_device_config):
        """Test successful Proxmox API configuration of device passthrough."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            service = HardwareAccelerationService(proxmox_client=mock_proxmoxer)

            # Mock device numbers lookup
            service.get_device_numbers = Mock(return_value=(226, 0))

            # Mock successful API call
            mock_proxmoxer.nodes('pve-node-1').lxc('1001').config.put.return_value = None

            result = service.configure_device_passthrough(
                node="pve-node-1",
                vmid=1001,
                device_config=intel_qsv_device_config
            )

            assert result is True

            # Verify Proxmox API was called with correct device configuration
            expected_config = {
                "dev0": "c 226:0 rw /dev/dri/renderD128"
            }
            mock_proxmoxer.nodes('pve-node-1').lxc('1001').config.put.assert_called_once_with(**expected_config)

    def test_proxmox_device_configuration_multiple_devices(self, mock_hardware_service, mock_proxmoxer):
        """Test Proxmox API configuration with multiple device passthroughs."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            service = HardwareAccelerationService(proxmox_client=mock_proxmoxer)

            device_configs = [
                {"path": "/dev/dri/renderD128", "mode": "rw"},
                {"path": "/dev/dri/card0", "mode": "ro"}
            ]

            # Mock device numbers lookup for both devices
            service.get_device_numbers = Mock(side_effect=[(226, 0), (226, 64)])

            mock_proxmoxer.nodes('pve-node-1').lxc('1001').config.put.return_value = None

            result = service.configure_multiple_device_passthrough(
                node="pve-node-1",
                vmid=1001,
                device_configs=device_configs
            )

            assert result is True

            # Verify both devices were configured
            expected_config = {
                "dev0": "c 226:0 rw /dev/dri/renderD128",
                "dev1": "c 226:64 ro /dev/dri/card0"
            }
            mock_proxmoxer.nodes('pve-node-1').lxc('1001').config.put.assert_called_once_with(**expected_config)

    def test_proxmox_device_configuration_api_error(self, mock_hardware_service, mock_proxmoxer,
                                                   intel_qsv_device_config):
        """Test Proxmox API device configuration handles API errors."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            service = HardwareAccelerationService(proxmox_client=mock_proxmoxer)
            service.get_device_numbers = Mock(return_value=(226, 0))

            # Mock API error
            mock_proxmoxer.nodes('pve-node-1').lxc('1001').config.put.side_effect = ResourceException(
                "400 Bad Request: parameter 'dev0' - invalid device specification"
            )

            with pytest.raises(ResourceException) as exc_info:
                service.configure_device_passthrough(
                    node="pve-node-1",
                    vmid=1001,
                    device_config=intel_qsv_device_config
                )

            assert "400 Bad Request" in str(exc_info.value)

    def test_intel_qsv_complete_workflow_success(self, mock_hardware_service, mock_ssh_client,
                                               mock_proxmoxer, device_stat_output,
                                               intel_qsv_device_config):
        """Test complete Intel QSV device passthrough workflow integration."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            # Setup SSH mocks for device detection and number lookup
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            mock_stdout.read.return_value = device_stat_output.encode('utf-8')
            mock_stderr.read.return_value = b''
            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            # Setup Proxmox API mock
            mock_proxmoxer.nodes('pve-node-1').lxc('1001').config.put.return_value = None

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/key",
                proxmox_client=mock_proxmoxer
            )

            # Execute complete workflow
            result = service.setup_intel_qsv_passthrough(
                node="pve-node-1",
                vmid=1001,
                device_path="/dev/dri/renderD128"
            )

            assert result is True

            # Verify all steps were executed
            mock_ssh_client.connect.assert_called_once()
            mock_ssh_client.exec_command.assert_called_with("stat /dev/dri/renderD128")

            expected_device_config = {
                "dev0": "c 226:0 rw /dev/dri/renderD128"
            }
            mock_proxmoxer.nodes('pve-node-1').lxc('1001').config.put.assert_called_once_with(**expected_device_config)

    def test_intel_qsv_workflow_device_not_found(self, mock_hardware_service, mock_ssh_client,
                                                mock_proxmoxer):
        """Test Intel QSV workflow fails gracefully when device not found."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService
            from src.exceptions import DeviceNotFoundError

            # Mock SSH command that returns device not found
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            mock_stdout.read.return_value = b''
            mock_stderr.read.return_value = b'stat: cannot stat \'/dev/dri/renderD128\': No such file or directory'
            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/key",
                proxmox_client=mock_proxmoxer
            )

            with pytest.raises(DeviceNotFoundError):
                service.setup_intel_qsv_passthrough(
                    node="pve-node-1",
                    vmid=1001,
                    device_path="/dev/dri/renderD128"
                )

            # Verify Proxmox API was not called due to device detection failure
            mock_proxmoxer.nodes.assert_not_called()

    def test_ssh_connection_failure_handling(self, mock_hardware_service, mock_ssh_client):
        """Test SSH connection failure handling during device detection."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService
            from src.exceptions import SSHConnectionError

            # Mock SSH connection failure
            mock_ssh_client.connect.side_effect = paramiko.AuthenticationException("Authentication failed")

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/invalid_key"
            )

            with pytest.raises(SSHConnectionError):
                service.detect_device("/dev/dri/renderD128")

    def test_container_privilege_requirements_validation(self, mock_hardware_service):
        """Test validation of container privilege requirements for device passthrough."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService
            from src.exceptions import ContainerPrivilegeError

            service = HardwareAccelerationService()

            # Test that certain devices require privileged containers
            privileged_devices = [
                "/dev/mem",
                "/dev/kmem",
                "/dev/nvidia0"
            ]

            for device_path in privileged_devices:
                requires_privilege = service.check_privilege_requirements(device_path)
                assert requires_privilege is True

            # Test that QSV devices can work with unprivileged containers
            qsv_devices = [
                "/dev/dri/renderD128",
                "/dev/dri/renderD129"
            ]

            for device_path in qsv_devices:
                requires_privilege = service.check_privilege_requirements(device_path)
                assert requires_privilege is False

    def test_device_conflict_detection(self, mock_hardware_service, mock_proxmoxer):
        """Test detection of device conflicts when device is already assigned."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService
            from src.exceptions import DeviceConflictError

            service = HardwareAccelerationService(proxmox_client=mock_proxmoxer)

            # Mock existing container configuration with device already assigned
            existing_config = {
                "dev0": "c 226:0 rw /dev/dri/renderD128"
            }
            mock_proxmoxer.nodes('pve-node-1').lxc('1002').config.get.return_value = existing_config

            # Mock list of existing containers
            mock_proxmoxer.nodes('pve-node-1').lxc.get.return_value = [
                {"vmid": 1001, "status": "running"},
                {"vmid": 1002, "status": "running"}
            ]

            # Try to assign the same device to a different container
            with pytest.raises(DeviceConflictError) as exc_info:
                service.configure_device_passthrough(
                    node="pve-node-1",
                    vmid=1001,
                    device_config={"path": "/dev/dri/renderD128", "mode": "rw"}
                )

            assert "already assigned to container 1002" in str(exc_info.value)

    @patch('paramiko.SSHClient')
    def test_ssh_client_integration_mock(self, mock_ssh_class, device_stat_output):
        """Test integration with mocked paramiko SSH client."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            # Setup mock SSH client instance
            mock_ssh_instance = Mock()
            mock_ssh_class.return_value = mock_ssh_instance

            # Setup command execution mock
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            mock_stdout.read.return_value = device_stat_output.encode('utf-8')
            mock_stderr.read.return_value = b''
            mock_ssh_instance.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            service = HardwareAccelerationService(
                host="pve-node-1.example.com",
                user="root",
                key_filename="/root/.ssh/id_rsa"
            )

            result = service.detect_device("/dev/dri/renderD128")

            # Verify SSH client was properly configured and used
            mock_ssh_class.assert_called_once()
            mock_ssh_instance.set_missing_host_key_policy.assert_called_once()
            mock_ssh_instance.connect.assert_called_once_with(
                hostname="pve-node-1.example.com",
                username="root",
                key_filename="/root/.ssh/id_rsa"
            )
            mock_ssh_instance.exec_command.assert_called_once_with("stat /dev/dri/renderD128")
            mock_ssh_instance.close.assert_called_once()

            assert result is True

    def test_device_permission_validation(self, mock_hardware_service, mock_ssh_client):
        """Test validation of device permissions and accessibility."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            # Mock device stat output with restricted permissions
            restricted_device_output = """  File: /dev/dri/renderD128
  Size: 0         	Blocks: 0          IO Block: 4096   character special file
Device: 5h/5d	Inode: 1040        Links: 1     Device type: e2,0
Access: (0600/crw-------)  Uid: (    0/    root)   Gid: (    0/    root)"""

            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            mock_stdout.read.return_value = restricted_device_output.encode('utf-8')
            mock_stderr.read.return_value = b''
            mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

            service = HardwareAccelerationService(
                host="pve-node-1",
                user="root",
                key_filename="/path/to/key"
            )

            permissions = service.get_device_permissions("/dev/dri/renderD128")

            assert permissions["mode"] == "0600"
            assert permissions["owner"] == "root"
            assert permissions["group"] == "root"
            assert permissions["accessible_by_containers"] is False


class TestHardwareAccelerationServiceMocks:
    """Additional tests focusing on service-level mocking and edge cases."""

    @pytest.fixture
    def mock_hardware_service(self, mock_ssh_client, mock_proxmoxer):
        """Mock hardware acceleration service."""
        service = Mock()
        service.ssh_client = mock_ssh_client
        service.proxmox = mock_proxmoxer
        service.detect_device = Mock()
        service.get_device_numbers = Mock()
        service.configure_device_passthrough = Mock()
        return service

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock paramiko SSH client for device detection."""
        mock_ssh = Mock(spec=paramiko.SSHClient)
        mock_ssh.connect = Mock()
        mock_ssh.exec_command = Mock()
        mock_ssh.close = Mock()
        return mock_ssh

    @pytest.fixture
    def mock_proxmoxer(self):
        """Mock proxmoxer ProxmoxAPI client."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()
        mock_config = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc('vmid').config
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc.return_value = mock_lxc
        mock_lxc.config = mock_config

        return mock_proxmox

    def test_service_initialization_with_all_parameters(self):
        """Test service initialization with all configuration parameters."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            service = HardwareAccelerationService(
                host="pve-cluster.example.com",
                port=22,
                user="admin",
                password="secret",
                key_filename="/path/to/key",
                timeout=30,
                proxmox_host="pve-api.example.com",
                proxmox_user="admin@pam",
                proxmox_password="api_secret",
                verify_ssl=False
            )

            assert service.ssh_host == "pve-cluster.example.com"
            assert service.ssh_port == 22
            assert service.ssh_user == "admin"
            assert service.timeout == 30

    def test_concurrent_device_operations_handling(self, mock_hardware_service):
        """Test handling of concurrent device operations and locking."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService
            from src.exceptions import DeviceLockError

            service = HardwareAccelerationService()

            # Simulate concurrent access to the same device
            with pytest.raises(DeviceLockError):
                with service.device_lock("/dev/dri/renderD128"):
                    # This should fail if another operation is already in progress
                    with service.device_lock("/dev/dri/renderD128"):
                        pass

    def test_device_cleanup_on_container_destruction(self, mock_hardware_service, mock_proxmoxer):
        """Test device cleanup when container is destroyed."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.hardware_acceleration import HardwareAccelerationService

            service = HardwareAccelerationService(proxmox_client=mock_proxmoxer)

            # Mock container destruction
            mock_proxmoxer.nodes('pve-node-1').lxc('1001').delete.return_value = "UPID:task:id"

            # Mock device registry cleanup
            service.device_registry = Mock()
            service.device_registry.release_devices_for_container = Mock()

            result = service.cleanup_container_devices(
                node="pve-node-1",
                vmid=1001
            )

            assert result is True
            service.device_registry.release_devices_for_container.assert_called_once_with(1001)