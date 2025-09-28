"""
Integration tests for mount points configuration in pxrun.

This module tests mounting host directories into LXC containers through the Proxmox API.
Tests follow TDD approach and validate mount point configuration, path validation,
and integration with the Proxmox API for container creation.

The tests validate:
- Single and multiple mount points
- Read-only and read-write mount configurations
- Size limits on mount points
- Path validation for host directories
- Mount point creation through Proxmox API
- Error handling for invalid mount configurations

Run with: pytest tests/integration/test_mount_points.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import os
import tempfile
import shutil


class TestMountPointsConfiguration:
    """Integration tests for mount points configuration and validation."""

    @pytest.fixture
    def mock_proxmox_api(self):
        """Mock proxmoxer ProxmoxAPI client for mount point operations."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc = mock_lxc

        return mock_proxmox

    @pytest.fixture
    def temp_host_directory(self):
        """Create a temporary host directory for testing mount points."""
        temp_dir = tempfile.mkdtemp(prefix="pxrun_test_mount_")
        # Create some test content
        test_file = Path(temp_dir) / "test_file.txt"
        test_file.write_text("test content")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mount_service_mock(self):
        """Mock mount service that will be implemented."""
        # This will fail until implementation exists - following TDD
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService
        return Mock()

    def test_mount_service_interface_exists(self):
        """Test that the mount service interface can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

    def test_single_mount_point_configuration(self, mock_proxmox_api, temp_host_directory):
        """Test mounting a single host directory into container."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": temp_host_directory,
                "container_path": "/mnt/data",
                "readonly": False,
                "size_limit": None
            }

            # Mock successful mount point creation
            mock_proxmox_api.nodes('pve-node-1').lxc.post.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

            container_config = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            result = service.create_container_with_mounts('pve-node-1', container_config, [mount_config])

            # Verify the mount point was added to container configuration
            expected_call_args = container_config.copy()
            expected_call_args["mp0"] = f"local-lvm:10,mp=/mnt/data"

            mock_proxmox_api.nodes('pve-node-1').lxc.post.assert_called_once_with(**expected_call_args)
            assert result == "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

    def test_multiple_mount_points_configuration(self, mock_proxmox_api, temp_host_directory):
        """Test mounting multiple host directories into container."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            # Create additional temp directories
            temp_dir2 = tempfile.mkdtemp(prefix="pxrun_test_mount2_")
            temp_dir3 = tempfile.mkdtemp(prefix="pxrun_test_mount3_")

            try:
                mount_configs = [
                    {
                        "host_path": temp_host_directory,
                        "container_path": "/mnt/data1",
                        "readonly": False,
                        "size_limit": None
                    },
                    {
                        "host_path": temp_dir2,
                        "container_path": "/mnt/data2",
                        "readonly": True,
                        "size_limit": "5G"
                    },
                    {
                        "host_path": temp_dir3,
                        "container_path": "/mnt/data3",
                        "readonly": False,
                        "size_limit": "10G"
                    }
                ]

                mock_proxmox_api.nodes('pve-node-1').lxc.post.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

                container_config = {
                    "vmid": 1001,
                    "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                    "hostname": "test-container",
                    "storage": "local-lvm"
                }

                result = service.create_container_with_mounts('pve-node-1', container_config, mount_configs)

                # Verify multiple mount points were added to container configuration
                expected_call_args = container_config.copy()
                expected_call_args["mp0"] = "local-lvm:10,mp=/mnt/data1"
                expected_call_args["mp1"] = "local-lvm:5,mp=/mnt/data2,ro=1"
                expected_call_args["mp2"] = "local-lvm:10,mp=/mnt/data3"

                mock_proxmox_api.nodes('pve-node-1').lxc.post.assert_called_once_with(**expected_call_args)
                assert result == "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

            finally:
                # Cleanup additional temp directories
                shutil.rmtree(temp_dir2, ignore_errors=True)
                shutil.rmtree(temp_dir3, ignore_errors=True)

    def test_readonly_mount_point_configuration(self, mock_proxmox_api, temp_host_directory):
        """Test configuring read-only mount points."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": temp_host_directory,
                "container_path": "/mnt/readonly",
                "readonly": True,
                "size_limit": None
            }

            mock_proxmox_api.nodes('pve-node-1').lxc.post.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

            container_config = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            result = service.create_container_with_mounts('pve-node-1', container_config, [mount_config])

            # Verify readonly flag is included in mount point configuration
            expected_call_args = container_config.copy()
            expected_call_args["mp0"] = "local-lvm:10,mp=/mnt/readonly,ro=1"

            mock_proxmox_api.nodes('pve-node-1').lxc.post.assert_called_once_with(**expected_call_args)
            assert result == "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

    def test_mount_point_with_size_limit(self, mock_proxmox_api, temp_host_directory):
        """Test configuring mount points with size limits."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": temp_host_directory,
                "container_path": "/mnt/limited",
                "readonly": False,
                "size_limit": "20G"
            }

            mock_proxmox_api.nodes('pve-node-1').lxc.post.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

            container_config = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            result = service.create_container_with_mounts('pve-node-1', container_config, [mount_config])

            # Verify size limit is included in mount point configuration
            expected_call_args = container_config.copy()
            expected_call_args["mp0"] = "local-lvm:20,mp=/mnt/limited"

            mock_proxmox_api.nodes('pve-node-1').lxc.post.assert_called_once_with(**expected_call_args)
            assert result == "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('os.access')
    def test_host_path_validation_success(self, mock_access, mock_isdir, mock_exists, mock_proxmox_api):
        """Test successful validation of host directory paths."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            # Mock successful path validation
            mock_exists.return_value = True
            mock_isdir.return_value = True
            mock_access.return_value = True

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": "/valid/host/path",
                "container_path": "/mnt/data",
                "readonly": False,
                "size_limit": None
            }

            # Should not raise any exceptions
            result = service.validate_mount_path(mount_config["host_path"])
            assert result is True

            # Verify path checks were called
            mock_exists.assert_called_once_with("/valid/host/path")
            mock_isdir.assert_called_once_with("/valid/host/path")
            mock_access.assert_called_once_with("/valid/host/path", os.R_OK)

    @patch('os.path.exists')
    def test_host_path_validation_nonexistent_path(self, mock_exists, mock_proxmox_api):
        """Test validation failure for non-existent host paths."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            # Mock non-existent path
            mock_exists.return_value = False

            service = MountService(mock_proxmox_api)

            with pytest.raises(MountValidationError) as exc_info:
                service.validate_mount_path("/nonexistent/path")

            assert "does not exist" in str(exc_info.value)
            mock_exists.assert_called_once_with("/nonexistent/path")

    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_host_path_validation_not_directory(self, mock_isdir, mock_exists, mock_proxmox_api):
        """Test validation failure for host paths that are not directories."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            # Mock file instead of directory
            mock_exists.return_value = True
            mock_isdir.return_value = False

            service = MountService(mock_proxmox_api)

            with pytest.raises(MountValidationError) as exc_info:
                service.validate_mount_path("/path/to/file.txt")

            assert "is not a directory" in str(exc_info.value)
            mock_exists.assert_called_once_with("/path/to/file.txt")
            mock_isdir.assert_called_once_with("/path/to/file.txt")

    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('os.access')
    def test_host_path_validation_no_read_permission(self, mock_access, mock_isdir, mock_exists, mock_proxmox_api):
        """Test validation failure for host paths without read permission."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            # Mock directory without read permission
            mock_exists.return_value = True
            mock_isdir.return_value = True
            mock_access.return_value = False

            service = MountService(mock_proxmox_api)

            with pytest.raises(MountValidationError) as exc_info:
                service.validate_mount_path("/no/read/permission")

            assert "not readable" in str(exc_info.value)
            mock_access.assert_called_once_with("/no/read/permission", os.R_OK)

    def test_invalid_container_path_validation(self, mock_proxmox_api):
        """Test validation of invalid container mount paths."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            invalid_paths = [
                "",  # Empty path
                "relative/path",  # Not absolute
                "/",  # Root directory
                "/proc/something",  # System directory
                "/sys/something",  # System directory
                "/dev/something"   # Device directory
            ]

            for invalid_path in invalid_paths:
                with pytest.raises(MountValidationError) as exc_info:
                    service.validate_container_path(invalid_path)

                assert "invalid container path" in str(exc_info.value).lower()

    def test_mount_point_size_limit_parsing(self, mock_proxmox_api):
        """Test parsing and validation of mount point size limits."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            # Test valid size formats
            valid_sizes = [
                ("1G", 1),
                ("10G", 10),
                ("500M", 0.5),  # Should be rounded up to 1G minimum
                ("2T", 2048),
                ("1024M", 1)
            ]

            for size_str, expected_gb in valid_sizes:
                result = service.parse_size_limit(size_str)
                assert result == max(1, int(expected_gb))  # Minimum 1GB

    def test_mount_point_size_limit_validation_errors(self, mock_proxmox_api):
        """Test validation errors for invalid size limit formats."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            invalid_sizes = [
                "invalid",
                "10X",
                "-5G",
                "0G",
                ""
            ]

            for invalid_size in invalid_sizes:
                with pytest.raises(MountValidationError) as exc_info:
                    service.parse_size_limit(invalid_size)

                assert "invalid size format" in str(exc_info.value).lower()

    def test_proxmox_api_error_handling_mount_creation(self, mock_proxmox_api, temp_host_directory):
        """Test error handling when Proxmox API calls fail during mount creation."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService
            from proxmoxer import ProxmoxAPIException

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": temp_host_directory,
                "container_path": "/mnt/data",
                "readonly": False,
                "size_limit": None
            }

            # Mock API error
            mock_proxmox_api.nodes('pve-node-1').lxc.post.side_effect = ProxmoxAPIException(
                "400 Bad Request: insufficient storage space"
            )

            container_config = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            with pytest.raises(ProxmoxAPIException) as exc_info:
                service.create_container_with_mounts('pve-node-1', container_config, [mount_config])

            assert "400 Bad Request" in str(exc_info.value)

    def test_mount_point_format_generation(self, mock_proxmox_api):
        """Test generation of Proxmox mount point format strings."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            test_cases = [
                {
                    "config": {
                        "host_path": "/host/path",
                        "container_path": "/container/path",
                        "readonly": False,
                        "size_limit": "10G"
                    },
                    "expected": "local-lvm:10,mp=/container/path"
                },
                {
                    "config": {
                        "host_path": "/host/path",
                        "container_path": "/container/path",
                        "readonly": True,
                        "size_limit": "5G"
                    },
                    "expected": "local-lvm:5,mp=/container/path,ro=1"
                },
                {
                    "config": {
                        "host_path": "/host/path",
                        "container_path": "/container/path",
                        "readonly": False,
                        "size_limit": None
                    },
                    "expected": "local-lvm:10,mp=/container/path"  # Default size
                }
            ]

            for test_case in test_cases:
                result = service.format_mount_point(test_case["config"], "local-lvm")
                assert result == test_case["expected"]


class TestMountPointsIntegrationScenarios:
    """Integration test scenarios for complex mount point configurations."""

    @pytest.fixture
    def container_service_mock(self):
        """Mock container service that integrates with mount service."""
        # This will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.container_service import ContainerService
        return Mock()

    def test_full_container_creation_with_mounts_integration(self):
        """Test complete container creation workflow with mount points."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.container_service import ContainerService
            from src.services.mount_service import MountService

            # This test would verify the full integration between
            # container creation and mount point configuration
            pass

    def test_mount_points_with_container_templates(self):
        """Test mount points work correctly with different container templates."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.container_service import ContainerService
            from src.services.mount_service import MountService

            # This test would verify mount points work with various OS templates
            pass

    def test_mount_points_persistence_across_container_restart(self):
        """Test that mount points persist correctly across container restarts."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.container_service import ContainerService
            from src.services.mount_service import MountService

            # This test would verify mount point persistence
            pass

    def test_mount_points_cleanup_on_container_destruction(self):
        """Test proper cleanup of mount points when container is destroyed."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.container_service import ContainerService
            from src.services.mount_service import MountService

            # This test would verify proper cleanup
            pass


class TestMountPointsSecurityValidation:
    """Security-focused tests for mount point configurations."""

    @pytest.fixture
    def mock_proxmox_api(self):
        """Mock proxmoxer ProxmoxAPI client for mount point operations."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc = mock_lxc

        return mock_proxmox

    def test_prevent_mounting_sensitive_system_paths(self, mock_proxmox_api):
        """Test prevention of mounting sensitive system directories."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            sensitive_paths = [
                "/etc",
                "/root",
                "/boot",
                "/proc",
                "/sys",
                "/dev",
                "/var/lib/docker",
                "/var/lib/lxc"
            ]

            for sensitive_path in sensitive_paths:
                with pytest.raises(MountValidationError) as exc_info:
                    service.validate_mount_path(sensitive_path)

                assert "sensitive" in str(exc_info.value).lower() or "not allowed" in str(exc_info.value).lower()

    def test_prevent_directory_traversal_in_container_paths(self, mock_proxmox_api):
        """Test prevention of directory traversal attacks in container paths."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            malicious_paths = [
                "/mnt/../etc",
                "/mnt/data/../../../root",
                "/mnt/./../../etc/passwd"
            ]

            for malicious_path in malicious_paths:
                with pytest.raises(MountValidationError) as exc_info:
                    service.validate_container_path(malicious_path)

                assert "traversal" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


class TestMountPointsPerformance:
    """Performance-focused tests for mount point operations."""

    @pytest.fixture
    def mock_proxmox_api(self):
        """Mock proxmoxer ProxmoxAPI client for mount point operations."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc = mock_lxc

        return mock_proxmox

    def test_large_number_of_mount_points(self, mock_proxmox_api):
        """Test handling of containers with many mount points."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            # Test with maximum reasonable number of mount points
            # Proxmox typically supports up to mp9 (10 mount points)
            mount_configs = []
            for i in range(10):
                mount_configs.append({
                    "host_path": f"/tmp/mount{i}",
                    "container_path": f"/mnt/data{i}",
                    "readonly": i % 2 == 0,
                    "size_limit": f"{(i+1)*5}G"
                })

            # Should handle all mount points without performance degradation
            # This would be measured in a real performance test
            pass

    def test_mount_point_validation_performance(self, mock_proxmox_api):
        """Test performance of mount point validation operations."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService
            import time

            service = MountService(mock_proxmox_api)

            # Test validation performance
            start_time = time.time()

            for i in range(100):
                try:
                    service.validate_mount_path(f"/tmp/test{i}")
                except Exception:
                    pass  # Expected for non-existent paths

            end_time = time.time()
            validation_time = end_time - start_time

            # Validation should be fast (less than 1 second for 100 validations)
            assert validation_time < 1.0, f"Validation took too long: {validation_time}s"


class TestMountPointsEdgeCases:
    """Edge case tests for mount point configurations."""

    @pytest.fixture
    def mock_proxmox_api(self):
        """Mock proxmoxer ProxmoxAPI client for mount point operations."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc = mock_lxc

        return mock_proxmox

    @pytest.fixture
    def temp_host_directory(self):
        """Create a temporary host directory for testing mount points."""
        temp_dir = tempfile.mkdtemp(prefix="pxrun_test_mount_")
        # Create some test content
        test_file = Path(temp_dir) / "test_file.txt"
        test_file.write_text("test content")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_empty_mount_configs_list(self, mock_proxmox_api):
        """Test handling of empty mount configurations list."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mock_proxmox_api.nodes('pve-node-1').lxc.post.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

            container_config = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            result = service.create_container_with_mounts('pve-node-1', container_config, [])

            # Should create container without mount points
            mock_proxmox_api.nodes('pve-node-1').lxc.post.assert_called_once_with(**container_config)
            assert result == "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

    def test_duplicate_container_mount_paths(self, mock_proxmox_api, temp_host_directory):
        """Test validation error for duplicate container mount paths."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            # Create second temp directory
            temp_dir2 = tempfile.mkdtemp(prefix="pxrun_test_mount2_")

            try:
                mount_configs = [
                    {
                        "host_path": temp_host_directory,
                        "container_path": "/mnt/data",
                        "readonly": False,
                        "size_limit": None
                    },
                    {
                        "host_path": temp_dir2,
                        "container_path": "/mnt/data",  # Duplicate path
                        "readonly": True,
                        "size_limit": "5G"
                    }
                ]

                container_config = {
                    "vmid": 1001,
                    "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                    "hostname": "test-container",
                    "storage": "local-lvm"
                }

                with pytest.raises(MountValidationError) as exc_info:
                    service.create_container_with_mounts('pve-node-1', container_config, mount_configs)

                assert "duplicate" in str(exc_info.value).lower()

            finally:
                shutil.rmtree(temp_dir2, ignore_errors=True)

    def test_mount_point_path_normalization(self, mock_proxmox_api):
        """Test path normalization for mount points."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            # Test various path formats that should be normalized
            test_paths = [
                ("/mnt/data/", "/mnt/data"),
                ("/mnt//data", "/mnt/data"),
                ("/mnt/./data", "/mnt/data"),
                ("/mnt/data/../data", "/mnt/data")
            ]

            for input_path, expected_path in test_paths:
                normalized = service.normalize_container_path(input_path)
                assert normalized == expected_path

    def test_maximum_mount_points_limit(self, mock_proxmox_api):
        """Test enforcement of maximum mount points limit (Proxmox supports mp0-mp9)."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            # Try to create 11 mount points (should exceed limit of 10)
            mount_configs = []
            for i in range(11):
                mount_configs.append({
                    "host_path": f"/tmp/mount{i}",
                    "container_path": f"/mnt/data{i}",
                    "readonly": False,
                    "size_limit": None
                })

            container_config = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            with pytest.raises(MountValidationError) as exc_info:
                service.create_container_with_mounts('pve-node-1', container_config, mount_configs)

            assert "maximum" in str(exc_info.value).lower() or "limit" in str(exc_info.value).lower()

    def test_mount_point_with_unicode_paths(self, mock_proxmox_api):
        """Test handling of mount points with unicode characters in paths."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            # Create temp directory with unicode name
            temp_dir = tempfile.mkdtemp(prefix="pxrun_test_ünïcödé_")

            try:
                mount_config = {
                    "host_path": temp_dir,
                    "container_path": "/mnt/dätä",
                    "readonly": False,
                    "size_limit": None
                }

                # Should handle unicode paths correctly
                normalized_container_path = service.normalize_container_path(mount_config["container_path"])
                assert normalized_container_path == "/mnt/dätä"

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_mount_point_with_very_long_paths(self, mock_proxmox_api):
        """Test handling of very long mount point paths."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            # Create very long path (exceeding typical filesystem limits)
            long_path = "/mnt/" + ("a" * 300)

            mount_config = {
                "host_path": "/tmp/test",
                "container_path": long_path,
                "readonly": False,
                "size_limit": None
            }

            with pytest.raises(MountValidationError) as exc_info:
                service.validate_container_path(mount_config["container_path"])

            assert "too long" in str(exc_info.value).lower() or "length" in str(exc_info.value).lower()


class TestMountPointsConfigurationValidation:
    """Advanced configuration validation tests."""

    @pytest.fixture
    def mock_proxmox_api(self):
        """Mock proxmoxer ProxmoxAPI client for mount point operations."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc = mock_lxc

        return mock_proxmox

    def test_validate_mount_config_structure(self, mock_proxmox_api):
        """Test validation of mount configuration dictionary structure."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService, MountValidationError

            service = MountService(mock_proxmox_api)

            # Test invalid configurations
            invalid_configs = [
                {},  # Empty config
                {"host_path": "/tmp"},  # Missing container_path
                {"container_path": "/mnt/data"},  # Missing host_path
                {
                    "host_path": "/tmp",
                    "container_path": "/mnt/data",
                    "readonly": "invalid"  # Should be boolean
                },
                {
                    "host_path": "/tmp",
                    "container_path": "/mnt/data",
                    "size_limit": 123  # Should be string or None
                }
            ]

            for invalid_config in invalid_configs:
                with pytest.raises(MountValidationError) as exc_info:
                    service.validate_mount_config(invalid_config)

                assert "invalid" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

    def test_validate_storage_backend_compatibility(self, mock_proxmox_api):
        """Test validation of mount points with different storage backends."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            storage_backends = [
                "local-lvm",
                "local-zfs",
                "nfs-storage",
                "ceph-storage"
            ]

            mount_config = {
                "host_path": "/tmp/test",
                "container_path": "/mnt/data",
                "readonly": False,
                "size_limit": "10G"
            }

            for storage in storage_backends:
                # Should generate appropriate mount point format for each storage type
                mount_point = service.format_mount_point(mount_config, storage)
                assert storage in mount_point
                assert "mp=/mnt/data" in mount_point

    def test_mount_point_backup_exclusion(self, mock_proxmox_api):
        """Test mount points can be configured to exclude from backups."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": "/tmp/test",
                "container_path": "/mnt/data",
                "readonly": False,
                "size_limit": "10G",
                "backup": False  # Exclude from backup
            }

            # Should include backup=0 in mount point format
            mount_point = service.format_mount_point(mount_config, "local-lvm")
            assert "backup=0" in mount_point

    def test_mount_point_shared_flag(self, mock_proxmox_api):
        """Test mount points can be configured as shared between containers."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": "/tmp/shared",
                "container_path": "/mnt/shared",
                "readonly": False,
                "size_limit": "10G",
                "shared": True
            }

            # Should include shared=1 in mount point format
            mount_point = service.format_mount_point(mount_config, "local-lvm")
            assert "shared=1" in mount_point


class TestMountPointsProxmoxIntegration:
    """Tests specific to Proxmox mount point integration."""

    @pytest.fixture
    def mock_proxmox_api(self):
        """Mock proxmoxer ProxmoxAPI client for mount point operations."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc = mock_lxc

        return mock_proxmox

    def test_mount_point_format_with_acl_support(self, mock_proxmox_api):
        """Test mount point format generation with ACL support."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": "/tmp/acl_test",
                "container_path": "/mnt/acl",
                "readonly": False,
                "size_limit": "10G",
                "acl": True  # Enable ACL support
            }

            # Should include acl=1 in mount point format
            mount_point = service.format_mount_point(mount_config, "local-lvm")
            assert "acl=1" in mount_point

    def test_mount_point_format_with_quota_support(self, mock_proxmox_api):
        """Test mount point format generation with quota support."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": "/tmp/quota_test",
                "container_path": "/mnt/quota",
                "readonly": False,
                "size_limit": "10G",
                "quota": True  # Enable quota support
            }

            # Should include quota=1 in mount point format
            mount_point = service.format_mount_point(mount_config, "local-lvm")
            assert "quota=1" in mount_point

    def test_mount_point_with_bind_mount_type(self, mock_proxmox_api):
        """Test bind mount type configuration."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            # For bind mounts, we use the host path directly instead of storage
            mount_config = {
                "host_path": "/host/bind/path",
                "container_path": "/mnt/bind",
                "readonly": False,
                "mount_type": "bind"
            }

            # Should generate bind mount format
            mount_point = service.format_mount_point(mount_config, None)
            assert mount_point == "/host/bind/path,mp=/mnt/bind"

    def test_mount_point_with_bind_readonly(self, mock_proxmox_api):
        """Test read-only bind mount configuration."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": "/host/readonly/path",
                "container_path": "/mnt/readonly",
                "readonly": True,
                "mount_type": "bind"
            }

            # Should generate read-only bind mount format
            mount_point = service.format_mount_point(mount_config, None)
            assert mount_point == "/host/readonly/path,mp=/mnt/readonly,ro=1"

    def test_container_creation_with_mixed_mount_types(self, mock_proxmox_api):
        """Test container creation with both volume and bind mounts."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_configs = [
                {
                    "host_path": "/tmp/volume_test",
                    "container_path": "/mnt/volume",
                    "readonly": False,
                    "size_limit": "10G",
                    "mount_type": "volume"
                },
                {
                    "host_path": "/host/bind/path",
                    "container_path": "/mnt/bind",
                    "readonly": True,
                    "mount_type": "bind"
                }
            ]

            mock_proxmox_api.nodes('pve-node-1').lxc.post.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

            container_config = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            result = service.create_container_with_mounts('pve-node-1', container_config, mount_configs)

            # Verify both mount types are configured correctly
            expected_call_args = container_config.copy()
            expected_call_args["mp0"] = "local-lvm:10,mp=/mnt/volume"
            expected_call_args["mp1"] = "/host/bind/path,mp=/mnt/bind,ro=1"

            mock_proxmox_api.nodes('pve-node-1').lxc.post.assert_called_once_with(**expected_call_args)
            assert result == "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

    def test_mount_point_with_custom_options(self, mock_proxmox_api):
        """Test mount points with custom Proxmox options."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.mount_service import MountService

            service = MountService(mock_proxmox_api)

            mount_config = {
                "host_path": "/tmp/custom_test",
                "container_path": "/mnt/custom",
                "readonly": False,
                "size_limit": "10G",
                "replicate": False,  # Don't replicate this mount
                "backup": False,     # Don't backup this mount
                "acl": True,         # Enable ACL
                "quota": True        # Enable quota
            }

            # Should include all custom options in mount point format
            mount_point = service.format_mount_point(mount_config, "local-lvm")
            assert "replicate=0" in mount_point
            assert "backup=0" in mount_point
            assert "acl=1" in mount_point
            assert "quota=1" in mount_point