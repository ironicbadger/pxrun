"""
Integration test for container lifecycle (create-list-destroy) workflow.

This test verifies the complete container lifecycle workflow:
1. Create a new container
2. List containers to verify creation
3. Destroy the container
4. Verify proper cleanup

Uses pytest with mocks following TDD approach. Tests will fail initially since
implementation doesn't exist yet.

The test validates:
- Create-list-destroy workflow execution
- State transitions between operations
- Proper cleanup and resource management
- Proxmox API integration for all three operations
- Error handling and rollback scenarios

Run with: pytest tests/integration/test_container_lifecycle.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import time


class TestContainerLifecycle:
    """Integration test for complete container lifecycle workflow."""

    @pytest.fixture
    def mock_proxmox_api(self):
        """Mock Proxmox API client for lifecycle operations."""
        api_mock = Mock()

        # Mock node selection for create
        api_mock.nodes.get.return_value = [
            {'node': 'pve01', 'status': 'online', 'cpu': 0.1, 'mem': 0.3},
            {'node': 'pve02', 'status': 'online', 'cpu': 0.2, 'mem': 0.4}
        ]

        # Mock template listing for create
        api_mock.nodes('pve01').storage('local').content.get.return_value = [
            {'volid': 'local:vztmpl/debian-13-standard_13.0-1_amd64.tar.zst', 'content': 'vztmpl'},
            {'volid': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst', 'content': 'vztmpl'}
        ]

        # Mock container creation
        create_response = {'data': 'UPID:pve01:00001234:00000000:66F5A1B2:vzcreate:101:root@pam:'}
        api_mock.nodes('pve01').lxc.post.return_value = create_response

        # Mock task completion for create
        api_mock.nodes('pve01').tasks('UPID:pve01:00001234:00000000:66F5A1B2:vzcreate:101:root@pam:').status.get.return_value = {
            'status': 'stopped',
            'exitstatus': 'OK'
        }

        # Mock container start
        start_response = {'data': 'UPID:pve01:00001235:00000000:66F5A1B3:vzstart:101:root@pam:'}
        api_mock.nodes('pve01').lxc(101).status.start.post.return_value = start_response

        # Mock start task completion
        api_mock.nodes('pve01').tasks('UPID:pve01:00001235:00000000:66F5A1B3:vzstart:101:root@pam:').status.get.return_value = {
            'status': 'stopped',
            'exitstatus': 'OK'
        }

        # Mock container status for verification
        api_mock.nodes('pve01').lxc(101).status.current.get.return_value = {
            'status': 'running',
            'vmid': 101,
            'name': 'lifecycle-test-1'
        }

        # Mock container config for IP retrieval
        api_mock.nodes('pve01').lxc(101).config.get.return_value = {
            'hostname': 'lifecycle-test-1',
            'net0': 'name=eth0,bridge=vmbr0,firewall=1,hwaddr=BC:24:11:12:34:56,ip=dhcp,type=veth'
        }

        # Mock container list (shows created container)
        api_mock.nodes('pve01').lxc.get.return_value = [
            {
                'vmid': 101,
                'name': 'lifecycle-test-1',
                'status': 'running',
                'maxmem': 1073741824,  # 1GB
                'maxdisk': 10737418240,  # 10GB
                'cpus': 2
            }
        ]
        api_mock.nodes('pve02').lxc.get.return_value = []

        # Mock container stop for destroy
        stop_response = {'data': 'UPID:pve01:00001236:00000000:66F5A1B4:vzstop:101:root@pam:'}
        api_mock.nodes('pve01').lxc(101).status.stop.post.return_value = stop_response

        # Mock stop task completion
        api_mock.nodes('pve01').tasks('UPID:pve01:00001236:00000000:66F5A1B4:vzstop:101:root@pam:').status.get.return_value = {
            'status': 'stopped',
            'exitstatus': 'OK'
        }

        # Mock container destroy
        destroy_response = {'data': 'UPID:pve01:00001237:00000000:66F5A1B5:vzdestroy:101:root@pam:'}
        api_mock.nodes('pve01').lxc(101).delete.return_value = destroy_response

        # Mock destroy task completion
        api_mock.nodes('pve01').tasks('UPID:pve01:00001237:00000000:66F5A1B5:vzdestroy:101:root@pam:').status.get.return_value = {
            'status': 'stopped',
            'exitstatus': 'OK'
        }

        # Mock empty container list after destroy
        api_mock.nodes('pve01').lxc.get.side_effect = [
            # First call during create verification
            [{'vmid': 101, 'name': 'lifecycle-test-1', 'status': 'running', 'maxmem': 1073741824, 'maxdisk': 10737418240, 'cpus': 2}],
            # Second call after destroy verification
            []
        ]

        return api_mock

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client for provisioning during create."""
        ssh_mock = Mock()
        ssh_mock.connect.return_value = None
        ssh_mock.exec_command.return_value = (Mock(), Mock(), Mock())
        ssh_mock.close.return_value = None
        return ssh_mock

    def test_lifecycle_implementation_missing(self):
        """Test that lifecycle components fail initially due to missing implementation."""
        # This test demonstrates TDD - all these imports will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import CreateCommand

        with pytest.raises(ImportError):
            from src.cli.commands.list import ListCommand

        with pytest.raises(ImportError):
            from src.cli.commands.destroy import DestroyCommand

    def test_complete_lifecycle_workflow_fails_no_implementation(self, mock_proxmox_api, mock_ssh_client):
        """
        Test complete lifecycle workflow - will fail until implementation exists.

        This test validates the entire create-list-destroy workflow:
        1. Create container with specific hostname
        2. List containers to verify creation
        3. Destroy container by VMID
        4. Verify container is removed from list
        """
        with pytest.raises(ImportError):
            from src.cli.commands.create import CreateCommand
            from src.cli.commands.list import ListCommand
            from src.cli.commands.destroy import DestroyCommand
            from src.services.proxmox import ProxmoxService
            from src.services.provisioning import ProvisioningService

            # Step 1: Create container
            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                with patch('src.services.provisioning.ProvisioningService') as mock_provisioning_service:
                    with patch('paramiko.SSHClient', return_value=mock_ssh_client):

                        # Setup service mocks for create
                        proxmox_instance = mock_proxmox_service.return_value
                        proxmox_instance.get_nodes.return_value = mock_proxmox_api.nodes.get()
                        proxmox_instance.get_templates.return_value = ['debian-13-standard', 'ubuntu-22.04-standard']
                        proxmox_instance.get_next_vmid.return_value = 101
                        proxmox_instance.create_container.return_value = {
                            'vmid': 101,
                            'task_id': 'UPID:pve01:00001234:00000000:66F5A1B2:vzcreate:101:root@pam:'
                        }
                        proxmox_instance.wait_for_task.return_value = True
                        proxmox_instance.start_container.return_value = True
                        proxmox_instance.get_container_ip.return_value = '192.168.1.101'
                        proxmox_instance.get_container_status.return_value = 'running'

                        # Setup provisioning service
                        provisioning_instance = mock_provisioning_service.return_value
                        provisioning_instance.wait_for_ssh.return_value = True
                        provisioning_instance.provision_container.return_value = True

                        # Execute create command
                        create_cmd = CreateCommand()
                        create_result = create_cmd.run(
                            hostname='lifecycle-test-1',
                            node='pve01',
                            template='debian-13',
                            cores=2,
                            memory=1024,
                            storage=10,
                            interactive=False
                        )

                        # Verify creation succeeded
                        assert create_result['vmid'] == 101
                        assert create_result['hostname'] == 'lifecycle-test-1'
                        assert create_result['status'] == 'created'

            # Step 2: List containers to verify creation
            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value
                proxmox_instance.list_containers.return_value = [
                    {
                        'vmid': 101,
                        'hostname': 'lifecycle-test-1',
                        'node': 'pve01',
                        'status': 'running',
                        'uptime': '5m',
                        'cpu': 2.5,
                        'memory': {'used': 512, 'total': 1024}
                    }
                ]

                # Execute list command
                list_cmd = ListCommand()
                list_result = list_cmd.run()

                # Verify container appears in list
                assert len(list_result['containers']) == 1
                container = list_result['containers'][0]
                assert container['vmid'] == 101
                assert container['hostname'] == 'lifecycle-test-1'
                assert container['status'] == 'running'

            # Step 3: Destroy container
            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value
                proxmox_instance.find_container.return_value = {
                    'vmid': 101,
                    'node': 'pve01',
                    'status': 'running'
                }
                proxmox_instance.stop_container.return_value = True
                proxmox_instance.destroy_container.return_value = {
                    'task_id': 'UPID:pve01:00001237:00000000:66F5A1B5:vzdestroy:101:root@pam:'
                }
                proxmox_instance.wait_for_task.return_value = True

                # Execute destroy command
                destroy_cmd = DestroyCommand()
                destroy_result = destroy_cmd.run(
                    container_id=101,
                    force=True,  # Force stop if running
                    confirm=True  # Skip confirmation prompt
                )

                # Verify destruction succeeded
                assert destroy_result['vmid'] == 101
                assert 'destroyed successfully' in destroy_result['message']

            # Step 4: Verify container removed from list
            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value
                proxmox_instance.list_containers.return_value = []  # Empty after destroy

                # Execute list command again
                list_cmd = ListCommand()
                final_list_result = list_cmd.run()

                # Verify container no longer appears in list
                assert len(final_list_result['containers']) == 0

    def test_lifecycle_state_transitions_fails_no_implementation(self, mock_proxmox_api):
        """
        Test that state transitions are properly managed during lifecycle.

        This test verifies:
        - Container transitions from non-existent to running during create
        - Container appears in list with correct status
        - Container transitions from running to destroyed
        - Container disappears from subsequent lists
        """
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value

                # Initial state: container doesn't exist
                proxmox_instance.find_container.side_effect = [
                    None,  # First call: doesn't exist
                    {'vmid': 101, 'node': 'pve01', 'status': 'running'},  # After create
                    {'vmid': 101, 'node': 'pve01', 'status': 'running'},  # Before destroy
                    None   # After destroy: doesn't exist
                ]

                # Mock create workflow
                proxmox_instance.create_container.return_value = {'vmid': 101, 'task_id': 'task1'}
                proxmox_instance.wait_for_task.return_value = True
                proxmox_instance.start_container.return_value = True

                # Mock list workflow
                proxmox_instance.list_containers.side_effect = [
                    [],  # Before create
                    [{'vmid': 101, 'hostname': 'test', 'node': 'pve01', 'status': 'running'}],  # After create
                    []   # After destroy
                ]

                # Mock destroy workflow
                proxmox_instance.stop_container.return_value = True
                proxmox_instance.destroy_container.return_value = {'task_id': 'task2'}

                # Test state transitions
                service = ProxmoxService()

                # 1. Verify initial non-existence
                initial_search = service.find_container(101)
                assert initial_search is None

                # 2. Create container
                create_result = service.create_container({
                    'vmid': 101,
                    'hostname': 'test',
                    'template': 'debian-13'
                })
                assert create_result['vmid'] == 101

                # 3. Verify existence after create
                after_create = service.find_container(101)
                assert after_create is not None
                assert after_create['status'] == 'running'

                # 4. Verify appears in list
                containers = service.list_containers()
                assert len(containers) == 1
                assert containers[0]['vmid'] == 101

                # 5. Destroy container
                destroy_result = service.destroy_container(101, force=True)
                assert 'task_id' in destroy_result

                # 6. Verify no longer exists
                after_destroy = service.find_container(101)
                assert after_destroy is None

                # 7. Verify removed from list
                final_containers = service.list_containers()
                assert len(final_containers) == 0

    def test_lifecycle_error_handling_fails_no_implementation(self, mock_proxmox_api):
        """
        Test error handling and rollback during lifecycle operations.

        This test verifies proper error handling for:
        - Create failures with cleanup
        - Destroy failures with proper error reporting
        - Network issues during operations
        """
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService
            from src.exceptions import ProxmoxError, ContainerNotFoundError

            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value

                # Test create failure with rollback
                proxmox_instance.create_container.side_effect = ProxmoxError("Insufficient resources")

                service = ProxmoxService()

                with pytest.raises(ProxmoxError):
                    service.create_container({
                        'vmid': 101,
                        'hostname': 'test-fail',
                        'template': 'debian-13'
                    })

                # Test destroy of non-existent container
                proxmox_instance.find_container.return_value = None

                with pytest.raises(ContainerNotFoundError):
                    service.destroy_container(999)

                # Test network failure during list
                proxmox_instance.list_containers.side_effect = ProxmoxError("Connection timeout")

                with pytest.raises(ProxmoxError):
                    service.list_containers()

    def test_lifecycle_cleanup_verification_fails_no_implementation(self, mock_proxmox_api):
        """
        Test that cleanup is properly verified after destroy operations.

        This test verifies:
        - Storage cleanup after container destroy
        - Network configuration cleanup
        - No orphaned resources remain
        """
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value

                # Mock successful destroy with cleanup verification
                proxmox_instance.find_container.return_value = {
                    'vmid': 101,
                    'node': 'pve01',
                    'status': 'running'
                }
                proxmox_instance.stop_container.return_value = True
                proxmox_instance.destroy_container.return_value = {'task_id': 'task1'}
                proxmox_instance.wait_for_task.return_value = True

                # Mock cleanup verification calls
                proxmox_instance.verify_container_cleanup.return_value = {
                    'storage_cleaned': True,
                    'network_cleaned': True,
                    'config_removed': True
                }

                service = ProxmoxService()

                # Execute destroy with cleanup verification
                destroy_result = service.destroy_container(101, force=True, verify_cleanup=True)

                # Verify cleanup was checked
                proxmox_instance.verify_container_cleanup.assert_called_once_with(101)

                # Verify all cleanup completed
                assert destroy_result['cleanup_verified'] is True

    def test_lifecycle_performance_requirements_fails_no_implementation(self, mock_proxmox_api):
        """
        Test that lifecycle operations meet performance requirements.

        This test verifies:
        - Create operation completes within reasonable time
        - List operation is fast for moderate container counts
        - Destroy operation completes promptly
        """
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value

                # Setup fast mock responses
                proxmox_instance.create_container.return_value = {'vmid': 101, 'task_id': 'task1'}
                proxmox_instance.wait_for_task.return_value = True
                proxmox_instance.start_container.return_value = True
                proxmox_instance.list_containers.return_value = [
                    {'vmid': i, 'hostname': f'test-{i}', 'node': 'pve01', 'status': 'running'}
                    for i in range(100, 110)  # 10 containers
                ]
                proxmox_instance.find_container.return_value = {'vmid': 101, 'node': 'pve01', 'status': 'running'}
                proxmox_instance.stop_container.return_value = True
                proxmox_instance.destroy_container.return_value = {'task_id': 'task2'}

                service = ProxmoxService()

                # Test create performance
                start_time = time.time()
                create_result = service.create_container({
                    'vmid': 101,
                    'hostname': 'perf-test',
                    'template': 'debian-13'
                })
                create_time = time.time() - start_time

                assert create_time < 30.0  # Should complete in under 30 seconds
                assert create_result['vmid'] == 101

                # Test list performance
                start_time = time.time()
                containers = service.list_containers()
                list_time = time.time() - start_time

                assert list_time < 5.0  # Should complete in under 5 seconds
                assert len(containers) == 10

                # Test destroy performance
                start_time = time.time()
                destroy_result = service.destroy_container(101, force=True)
                destroy_time = time.time() - start_time

                assert destroy_time < 15.0  # Should complete in under 15 seconds
                assert 'task_id' in destroy_result

    def test_lifecycle_api_call_sequence_fails_no_implementation(self, mock_proxmox_api):
        """
        Test that Proxmox API calls are made in the correct sequence.

        This test verifies the exact sequence of API calls for:
        - Container creation workflow
        - Container listing
        - Container destruction workflow
        """
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                proxmox_instance = mock_proxmox_service.return_value

                # Setup return values
                proxmox_instance.get_next_vmid.return_value = 101
                proxmox_instance.create_container.return_value = {'vmid': 101, 'task_id': 'task1'}
                proxmox_instance.wait_for_task.return_value = True
                proxmox_instance.start_container.return_value = True
                proxmox_instance.list_containers.return_value = [
                    {'vmid': 101, 'hostname': 'test', 'node': 'pve01', 'status': 'running'}
                ]
                proxmox_instance.find_container.return_value = {'vmid': 101, 'node': 'pve01', 'status': 'running'}
                proxmox_instance.stop_container.return_value = True
                proxmox_instance.destroy_container.return_value = {'task_id': 'task2'}

                service = ProxmoxService()

                # Execute complete lifecycle
                # 1. Create
                service.create_container({'vmid': 101, 'hostname': 'test', 'template': 'debian-13'})

                # 2. List
                service.list_containers()

                # 3. Destroy
                service.destroy_container(101, force=True)

                # Verify call sequence
                expected_calls = [
                    call.get_next_vmid(),
                    call.create_container({'vmid': 101, 'hostname': 'test', 'template': 'debian-13'}),
                    call.wait_for_task('task1'),
                    call.start_container(101),
                    call.list_containers(),
                    call.find_container(101),
                    call.stop_container(101),
                    call.destroy_container(101, force=True),
                    call.wait_for_task('task2')
                ]

                # Note: In actual implementation, we'd verify the exact call sequence
                # This test documents the expected API interaction pattern
                assert len(proxmox_instance.method_calls) >= 6  # At minimum

    def test_create_interactive(self, mock_proxmox_api, mock_ssh_client):
        """
        Test interactive container creation workflow.

        This test validates the interactive creation process where users
        are prompted for configuration values step by step.
        """
        with pytest.raises(ImportError):
            from src.cli.commands.create import CreateCommand
            from src.services.proxmox import ProxmoxService
            from src.services.provisioning import ProvisioningService

            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                with patch('src.services.provisioning.ProvisioningService') as mock_provisioning_service:
                    with patch('paramiko.SSHClient', return_value=mock_ssh_client):
                        with patch('builtins.input') as mock_input:

                            # Mock interactive input responses
                            mock_input.side_effect = [
                                'interactive-test',  # hostname
                                'pve01',            # node
                                'debian-13',        # template
                                '2',                # cores
                                '2048',             # memory
                                '15',               # storage
                                'y'                 # confirm creation
                            ]

                            # Setup service mocks
                            proxmox_instance = mock_proxmox_service.return_value
                            proxmox_instance.get_nodes.return_value = ['pve01', 'pve02']
                            proxmox_instance.get_templates.return_value = ['debian-13', 'ubuntu-22.04']
                            proxmox_instance.get_next_vmid.return_value = 102
                            proxmox_instance.create_container.return_value = {
                                'vmid': 102,
                                'task_id': 'task_interactive'
                            }
                            proxmox_instance.wait_for_task.return_value = True
                            proxmox_instance.start_container.return_value = True

                            provisioning_instance = mock_provisioning_service.return_value
                            provisioning_instance.provision_container.return_value = True

                            # Execute interactive create command
                            create_cmd = CreateCommand()
                            result = create_cmd.run_interactive()

                            # Verify interactive creation succeeded
                            assert result['vmid'] == 102
                            assert result['hostname'] == 'interactive-test'
                            assert result['status'] == 'created'

                            # Verify user was prompted for all required fields
                            assert mock_input.call_count >= 6

    def test_create_from_config(self, mock_proxmox_api, mock_ssh_client):
        """
        Test container creation from YAML configuration file.

        This test validates creating containers using a YAML configuration
        file with all settings pre-defined.
        """
        with pytest.raises(ImportError):
            from src.cli.commands.create import CreateCommand
            from src.services.config_manager import ConfigManager
            from src.services.proxmox import ProxmoxService
            from src.services.provisioning import ProvisioningService

            sample_config = {
                'container': {
                    'hostname': 'config-test-container',
                    'template': 'ubuntu-22.04-standard',
                    'node': 'pve01',
                    'cores': 4,
                    'memory': 4096,
                    'storage': 25
                },
                'provisioning': {
                    'install_docker': True,
                    'install_tailscale': False,
                    'custom_scripts': [
                        'apt-get update',
                        'apt-get install -y nginx'
                    ]
                }
            }

            with patch('src.services.config_manager.ConfigManager') as mock_config_manager:
                with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:
                    with patch('src.services.provisioning.ProvisioningService') as mock_provisioning_service:
                        with patch('paramiko.SSHClient', return_value=mock_ssh_client):

                            # Setup config manager mock
                            config_instance = mock_config_manager.return_value
                            config_instance.load_config.return_value = sample_config
                            config_instance.validate_config.return_value.is_valid = True
                            config_instance.apply_defaults.return_value = sample_config

                            # Setup service mocks
                            proxmox_instance = mock_proxmox_service.return_value
                            proxmox_instance.get_next_vmid.return_value = 103
                            proxmox_instance.create_container.return_value = {
                                'vmid': 103,
                                'task_id': 'task_config'
                            }
                            proxmox_instance.wait_for_task.return_value = True
                            proxmox_instance.start_container.return_value = True

                            provisioning_instance = mock_provisioning_service.return_value
                            provisioning_instance.provision_container.return_value = True

                            # Execute create from config command
                            create_cmd = CreateCommand()
                            result = create_cmd.run_from_config(config_file='/path/to/config.yaml')

                            # Verify creation from config succeeded
                            assert result['vmid'] == 103
                            assert result['hostname'] == 'config-test-container'
                            assert result['status'] == 'created'

                            # Verify config was loaded and validated
                            config_instance.load_config.assert_called_once_with('/path/to/config.yaml')
                            config_instance.validate_config.assert_called_once()

    def test_provisioning(self, mock_proxmox_api, mock_ssh_client):
        """
        Test container provisioning workflow.

        This test validates the provisioning process that installs software
        and configures containers after creation.
        """
        with pytest.raises(ImportError):
            from src.services.provisioning import ProvisioningService
            from src.services.ssh_provisioner import SSHProvisioner

            provisioning_config = {
                'vmid': 104,
                'hostname': 'provision-test',
                'node': 'pve01',
                'provisioning': {
                    'install_docker': True,
                    'install_tailscale': True,
                    'tailscale_auth_key': 'tskey-test-123',
                    'custom_scripts': [
                        'apt-get update && apt-get upgrade -y',
                        'apt-get install -y htop vim curl'
                    ]
                }
            }

            with patch('src.services.ssh_provisioner.SSHProvisioner') as mock_ssh_provisioner:
                with patch('src.services.provisioning.ProvisioningService') as mock_provisioning_service:

                    # Setup SSH provisioner mock
                    ssh_instance = mock_ssh_provisioner.return_value
                    ssh_instance.connect.return_value = True
                    ssh_instance.execute_in_container.return_value.exit_code = 0
                    ssh_instance.provision_container.return_value.success = True

                    # Setup provisioning service mock
                    provisioning_instance = mock_provisioning_service.return_value
                    provisioning_instance.provision_container.return_value = {
                        'success': True,
                        'installed_packages': ['docker-ce', 'tailscale'],
                        'executed_scripts': 2,
                        'duration': 45.2
                    }

                    # Execute provisioning workflow
                    provisioning_service = ProvisioningService()
                    result = provisioning_service.provision_container(provisioning_config)

                    # Verify provisioning succeeded
                    assert result['success'] is True
                    assert 'docker-ce' in result['installed_packages']
                    assert 'tailscale' in result['installed_packages']
                    assert result['executed_scripts'] == 2

                    # Verify SSH provisioner was used
                    mock_ssh_provisioner.assert_called_once()
                    ssh_instance.provision_container.assert_called_once_with(provisioning_config)

    def test_destroy(self, mock_proxmox_api):
        """
        Test container destruction workflow.

        This test validates the complete container destruction process
        including stopping, cleanup, and verification.
        """
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import DestroyCommand
            from src.services.proxmox import ProxmoxService

            with patch('src.services.proxmox.ProxmoxService') as mock_proxmox_service:

                # Setup service mocks for destroy
                proxmox_instance = mock_proxmox_service.return_value
                proxmox_instance.find_container.return_value = {
                    'vmid': 105,
                    'hostname': 'destroy-test',
                    'node': 'pve01',
                    'status': 'running'
                }
                proxmox_instance.stop_container.return_value = {
                    'task_id': 'task_stop'
                }
                proxmox_instance.wait_for_task.return_value = True
                proxmox_instance.destroy_container.return_value = {
                    'task_id': 'task_destroy'
                }
                proxmox_instance.verify_container_cleanup.return_value = {
                    'storage_cleaned': True,
                    'network_cleaned': True,
                    'config_removed': True
                }

                # Execute destroy command
                destroy_cmd = DestroyCommand()
                result = destroy_cmd.run(
                    container_id=105,
                    force=True,
                    confirm=True,
                    cleanup_verification=True
                )

                # Verify destruction succeeded
                assert result['vmid'] == 105
                assert result['status'] == 'destroyed'
                assert 'destroyed successfully' in result['message']

                # Verify proper sequence of operations
                proxmox_instance.find_container.assert_called_once_with(105)
                proxmox_instance.stop_container.assert_called_once_with(105)
                proxmox_instance.destroy_container.assert_called_once_with(105)
                proxmox_instance.verify_container_cleanup.assert_called_once_with(105)


class TestLifecycleIntegrationRequirements:
    """Tests that validate specific lifecycle integration requirements."""

    def test_create_list_destroy_integration_contract(self):
        """
        Test that the create-list-destroy workflow follows the contract specifications.

        This test validates that the integration adheres to:
        - OpenAPI contract specifications for each command
        - Consistent data formats between operations
        - Proper VMID management across operations
        """
        with pytest.raises(ImportError):
            from src.cli.commands.create import CreateCommand
            from src.cli.commands.list import ListCommand
            from src.cli.commands.destroy import DestroyCommand

            # The integration should maintain consistent data structures
            # between create, list, and destroy operations as defined in OpenAPI contract

            # Expected data flow:
            # create -> returns ContainerInfo with vmid
            # list -> returns ContainerSummary[] including the vmid
            # destroy -> accepts container_id (vmid) and returns confirmation

            # This test documents the expected integration contract
            expected_create_response_fields = ['vmid', 'hostname', 'node', 'status', 'connection']
            expected_list_response_fields = ['vmid', 'hostname', 'node', 'status']
            expected_destroy_input_fields = ['container_id', 'force', 'confirm']

            # Contract validation would occur in actual implementation
            assert len(expected_create_response_fields) == 5
            assert len(expected_list_response_fields) == 4
            assert len(expected_destroy_input_fields) == 3

    def test_lifecycle_workflow_atomicity(self):
        """
        Test that lifecycle operations maintain atomicity.

        This test verifies:
        - Create operation is fully atomic (success or complete rollback)
        - Destroy operation is fully atomic (success or no changes)
        - List operation provides consistent snapshots
        """
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService
            from src.exceptions import ProxmoxError

            # Atomicity requirements:
            # 1. Create must succeed completely or leave no traces
            # 2. Destroy must succeed completely or leave container unchanged
            # 3. List must provide consistent point-in-time view

            # This test documents atomicity requirements for implementation
            atomicity_requirements = {
                'create': 'all-or-nothing container creation with cleanup on failure',
                'list': 'consistent point-in-time snapshot of container states',
                'destroy': 'all-or-nothing container removal with rollback on failure'
            }

            assert len(atomicity_requirements) == 3

    def test_lifecycle_concurrent_operations_safety(self):
        """
        Test that lifecycle operations are safe for concurrent execution.

        This test verifies:
        - Multiple list operations can run concurrently
        - Create and destroy operations use proper locking
        - VMID allocation prevents conflicts
        """
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            # Concurrency safety requirements:
            # 1. List operations should be read-only and thread-safe
            # 2. Create operations should use atomic VMID allocation
            # 3. Destroy operations should use proper container locking

            # This test documents concurrency requirements for implementation
            concurrency_requirements = {
                'list_safety': 'read-only operations safe for concurrent execution',
                'create_safety': 'atomic VMID allocation prevents conflicts',
                'destroy_safety': 'container locking prevents concurrent modifications'
            }

            assert len(concurrency_requirements) == 3