"""Tests for the CLI Scale EC2 ASG module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from P67_awstools import cli_scale_ec2_asg


class TestCliScaleEc2Asg:
    """Test cases for CLI Scale EC2 ASG functionality."""

    @patch('P67_awstools.cli_scale_ec2_asg.boto3.client')
    def test_get_autoscaling_groups(self, mock_boto_client):
        """Test retrieving autoscaling groups."""
        # Mock client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock response
        mock_client.describe_auto_scaling_groups.return_value = {
            'AutoScalingGroups': [
                {
                    'AutoScalingGroupName': 'test-asg-1',
                    'MinSize': 1,
                    'MaxSize': 3,
                    'DesiredCapacity': 2
                },
                {
                    'AutoScalingGroupName': 'test-asg-2',
                    'MinSize': 0,
                    'MaxSize': 5,
                    'DesiredCapacity': 1
                }
            ]
        }
        
        result = cli_scale_ec2_asg.get_autoscaling_groups()
        
        assert len(result) == 2
        assert result[0]['AutoScalingGroupName'] == 'test-asg-1'
        assert result[1]['AutoScalingGroupName'] == 'test-asg-2'
        
        # Verify the API call
        mock_client.describe_auto_scaling_groups.assert_called_once_with(MaxRecords=100)
        mock_boto_client.assert_called_once_with('autoscaling')

    def test_get_instance_ids(self):
        """Test extracting instance IDs from autoscaling group."""
        autoscaling_group = {
            'AutoScalingGroupName': 'test-asg',
            'Instances': [
                {'InstanceId': 'i-1234567890abcdef0'},
                {'InstanceId': 'i-0987654321fedcba0'},
                {'InstanceId': 'i-abcdef1234567890f'}
            ]
        }
        
        result = cli_scale_ec2_asg.get_instance_ids(autoscaling_group)
        
        assert len(result) == 3
        assert 'i-1234567890abcdef0' in result
        assert 'i-0987654321fedcba0' in result
        assert 'i-abcdef1234567890f' in result

    def test_get_instance_ids_empty(self):
        """Test extracting instance IDs from empty autoscaling group."""
        autoscaling_group = {
            'AutoScalingGroupName': 'empty-asg',
            'Instances': []
        }
        
        result = cli_scale_ec2_asg.get_instance_ids(autoscaling_group)
        
        assert len(result) == 0
        assert result == []

    @patch('P67_awstools.cli_scale_ec2_asg.boto3.client')
    def test_get_instance_uptime(self, mock_boto_client):
        """Test calculating instance uptime."""
        # Mock EC2 client
        mock_ec2_client = MagicMock()
        mock_boto_client.return_value = mock_ec2_client
        
        # Mock launch time (2 days ago)
        launch_time = datetime.utcnow() - timedelta(days=2)
        launch_time_str = launch_time.strftime('%Y-%m-%d %H:%M:%S+00:00')
        
        mock_ec2_client.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-1234567890abcdef0',
                            'LaunchTime': launch_time_str
                        }
                    ]
                }
            ]
        }
        
        result = cli_scale_ec2_asg.get_instance_uptime('i-1234567890abcdef0')
        
        # Should be approximately 2 days (allowing for small time differences)
        assert result.days >= 1
        assert result.days <= 2
        
        # Verify the API call
        mock_ec2_client.describe_instances.assert_called_once_with(
            InstanceIds=['i-1234567890abcdef0']
        )
        mock_boto_client.assert_called_once_with('ec2')

    @patch('P67_awstools.cli_scale_ec2_asg.get_instance_uptime')
    @patch('P67_awstools.cli_scale_ec2_asg.get_instance_ids')
    @patch('builtins.print')
    def test_show_instance_uptimes(self, mock_print, mock_get_instance_ids, mock_get_uptime):
        """Test showing instance uptimes."""
        # Mock data
        autoscaling_groups = [
            {'AutoScalingGroupName': 'test-asg-1'},
            {'AutoScalingGroupName': 'test-asg-2'}
        ]
        
        mock_get_instance_ids.side_effect = [
            ['i-1234567890abcdef0', 'i-0987654321fedcba0'],
            ['i-abcdef1234567890f']
        ]
        
        mock_uptime = timedelta(days=2, hours=3, minutes=45)
        mock_get_uptime.return_value = mock_uptime
        
        cli_scale_ec2_asg.show_instance_uptimes(autoscaling_groups)
        
        # Verify function calls
        assert mock_get_instance_ids.call_count == 2
        assert mock_get_uptime.call_count == 3
        
        # Verify print calls
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any('test-asg-1' in call for call in print_calls)
        assert any('test-asg-2' in call for call in print_calls)
        assert any('i-1234567890abcdef0' in call for call in print_calls)

    @patch('P67_awstools.cli_scale_ec2_asg.boto3.client')
    @patch('builtins.print')
    def test_scale_ec2_asg(self, mock_print, mock_boto_client):
        """Test scaling autoscaling groups."""
        # Mock client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        autoscaling_groups = [
            {'AutoScalingGroupName': 'test-asg-1'},
            {'AutoScalingGroupName': 'test-asg-2'}
        ]
        
        cli_scale_ec2_asg.scale_ec2_asg(autoscaling_groups, 5)
        
        # Verify API calls
        assert mock_client.update_auto_scaling_group.call_count == 2
        
        # Check the calls were made with correct parameters
        calls = mock_client.update_auto_scaling_group.call_args_list
        
        # First ASG
        assert calls[0][1]['AutoScalingGroupName'] == 'test-asg-1'
        assert calls[0][1]['MinSize'] == 5
        assert calls[0][1]['MaxSize'] == 5
        assert calls[0][1]['DesiredCapacity'] == 5
        
        # Second ASG
        assert calls[1][1]['AutoScalingGroupName'] == 'test-asg-2'
        assert calls[1][1]['MinSize'] == 5
        assert calls[1][1]['MaxSize'] == 5
        assert calls[1][1]['DesiredCapacity'] == 5
        
        # Verify print statements
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any('test-asg-1' in call and '5 instances' in call for call in print_calls)
        assert any('test-asg-2' in call and '5 instances' in call for call in print_calls)
        
        # Verify boto3 client was called
        mock_boto_client.assert_called_once_with('autoscaling')

    @patch('P67_awstools.cli_scale_ec2_asg.get_autoscaling_groups')
    @patch('P67_awstools.cli_scale_ec2_asg.show_instance_uptimes')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_main_function_show_uptimes(self, mock_print, mock_input, mock_show_uptimes, mock_get_asgs):
        """Test main function with show uptimes option."""
        # Mock data
        mock_asgs = [{'AutoScalingGroupName': 'test-asg'}]
        mock_get_asgs.return_value = mock_asgs
        
        # Mock user input - choose option 1 (show uptimes)
        mock_input.return_value = '1'
        
        cli_scale_ec2_asg.main()
        
        # Verify functions were called
        mock_get_asgs.assert_called_once()
        mock_show_uptimes.assert_called_once_with(mock_asgs)
        
        # Verify menu was displayed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any('Select an action:' in call for call in print_calls)
        assert any('Show instance uptimes' in call for call in print_calls)

    @patch('P67_awstools.cli_scale_ec2_asg.get_autoscaling_groups')
    @patch('P67_awstools.cli_scale_ec2_asg.scale_ec2_asg')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_main_function_scale_asg(self, mock_print, mock_input, mock_scale, mock_get_asgs):
        """Test main function with scale ASG option."""
        # Mock data
        mock_asgs = [
            {'AutoScalingGroupName': 'test-asg-1'},
            {'AutoScalingGroupName': 'test-asg-2'},
            {'AutoScalingGroupName': 'test-asg-3'}
        ]
        mock_get_asgs.return_value = mock_asgs
        
        # Mock user inputs - choose option 2, select ASGs 1 and 3, size 4
        mock_input.side_effect = ['2', '1,3', '4']
        
        cli_scale_ec2_asg.main()
        
        # Verify functions were called
        mock_get_asgs.assert_called_once()
        
        # Verify scale_ec2_asg was called with correct ASGs and size
        mock_scale.assert_called_once()
        call_args = mock_scale.call_args[0]
        selected_asgs = call_args[0]
        size = call_args[1]
        
        assert len(selected_asgs) == 2
        assert selected_asgs[0]['AutoScalingGroupName'] == 'test-asg-1'
        assert selected_asgs[1]['AutoScalingGroupName'] == 'test-asg-3'
        assert size == 4

    @patch('P67_awstools.cli_scale_ec2_asg.get_autoscaling_groups')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_main_function_invalid_choice(self, mock_print, mock_input, mock_get_asgs):
        """Test main function with invalid choice."""
        # Mock data
        mock_get_asgs.return_value = []
        
        # Mock user input - invalid choice
        mock_input.return_value = '3'
        
        cli_scale_ec2_asg.main()
        
        # Verify error message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any('Invalid choice' in call for call in print_calls)

    @patch('P67_awstools.cli_scale_ec2_asg.get_autoscaling_groups')
    @patch('P67_awstools.cli_scale_ec2_asg.scale_ec2_asg')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_main_function_scale_single_asg(self, mock_print, mock_input, mock_scale, mock_get_asgs):
        """Test main function scaling a single ASG."""
        # Mock data
        mock_asgs = [{'AutoScalingGroupName': 'single-asg'}]
        mock_get_asgs.return_value = mock_asgs
        
        # Mock user inputs - choose option 2, select ASG 1, size 2
        mock_input.side_effect = ['2', '1', '2']
        
        cli_scale_ec2_asg.main()
        
        # Verify scale_ec2_asg was called with correct parameters
        mock_scale.assert_called_once()
        call_args = mock_scale.call_args[0]
        selected_asgs = call_args[0]
        size = call_args[1]
        
        assert len(selected_asgs) == 1
        assert selected_asgs[0]['AutoScalingGroupName'] == 'single-asg'
        assert size == 2

    @patch('P67_awstools.cli_scale_ec2_asg.get_autoscaling_groups')
    @patch('builtins.input')
    def test_main_function_scale_invalid_asg_selection(self, mock_input, mock_get_asgs):
        """Test main function with invalid ASG selection."""
        # Mock data
        mock_asgs = [{'AutoScalingGroupName': 'test-asg'}]
        mock_get_asgs.return_value = mock_asgs
        
        # Mock user inputs - choose option 2, select invalid ASG number
        mock_input.side_effect = ['2', '5', '2']
        
        # Should raise IndexError when trying to access non-existent ASG
        with pytest.raises(IndexError):
            cli_scale_ec2_asg.main()

    @patch('P67_awstools.cli_scale_ec2_asg.boto3.client')
    def test_scale_ec2_asg_empty_list(self, mock_boto_client):
        """Test scaling with empty autoscaling groups list."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        cli_scale_ec2_asg.scale_ec2_asg([], 3)
        
        # Should not make any API calls
        mock_client.update_auto_scaling_group.assert_not_called()

    @patch('P67_awstools.cli_scale_ec2_asg.boto3.client')
    def test_get_instance_uptime_error_handling(self, mock_boto_client):
        """Test error handling in get_instance_uptime."""
        # Mock EC2 client
        mock_ec2_client = MagicMock()
        mock_boto_client.return_value = mock_ec2_client
        
        # Mock API error
        from botocore.exceptions import ClientError
        mock_ec2_client.describe_instances.side_effect = ClientError(
            {'Error': {'Code': 'InvalidInstanceID.NotFound', 'Message': 'Instance not found'}},
            'DescribeInstances'
        )
        
        # Should raise the exception
        with pytest.raises(ClientError):
            cli_scale_ec2_asg.get_instance_uptime('i-invalid')

    @patch('P67_awstools.cli_scale_ec2_asg.boto3.client')
    def test_scale_ec2_asg_api_error(self, mock_boto_client):
        """Test error handling in scale_ec2_asg."""
        # Mock client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock API error
        from botocore.exceptions import ClientError
        mock_client.update_auto_scaling_group.side_effect = ClientError(
            {'Error': {'Code': 'ValidationError', 'Message': 'Invalid ASG name'}},
            'UpdateAutoScalingGroup'
        )
        
        autoscaling_groups = [{'AutoScalingGroupName': 'invalid-asg'}]
        
        # Should raise the exception
        with pytest.raises(ClientError):
            cli_scale_ec2_asg.scale_ec2_asg(autoscaling_groups, 2)