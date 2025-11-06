"""Tests for the Password Rotate module."""

import pytest
from unittest.mock import patch, MagicMock
from P67_awstools import password_rotate


class TestPasswordRotate:
    """Test cases for Password Rotate functionality."""

    @patch('P67_awstools.password_rotate.boto3.client')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_main_function_success(self, mock_print, mock_input, mock_boto_client):
        """Test successful password rotation and access key replacement."""
        # Mock user inputs
        mock_input.side_effect = ['old_password', 'new_password']
        
        # Mock IAM client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock list_access_keys response
        mock_client.list_access_keys.return_value = {
            'AccessKeyMetadata': [
                {
                    'UserName': 'test-user',
                    'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE'
                }
            ]
        }
        
        # Mock create_access_key response
        mock_client.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIAI44QH8DHBEXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'UserName': 'test-user'
            }
        }
        
        # Run the main function
        password_rotate.main()
        
        # Verify password change was called
        mock_client.change_password.assert_called_once_with(
            OldPassword='old_password',
            NewPassword='new_password'
        )
        
        # Verify old access key was deleted
        mock_client.delete_access_key.assert_called_once_with(
            UserName='test-user',
            AccessKeyId='AKIAIOSFODNN7EXAMPLE'
        )
        
        # Verify new access key was created
        mock_client.create_access_key.assert_called_once_with(UserName='test-user')
        
        # Verify output was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any('New Access Key:' in call for call in print_calls)
        assert any('AKIAI44QH8DHBEXAMPLE' in call for call in print_calls)

    @patch('P67_awstools.password_rotate.boto3.client')
    @patch('builtins.input')
    def test_main_function_multiple_access_keys(self, mock_input, mock_boto_client):
        """Test handling multiple access keys."""
        # Mock user inputs
        mock_input.side_effect = ['old_password', 'new_password']
        
        # Mock IAM client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock list_access_keys response with multiple keys
        mock_client.list_access_keys.return_value = {
            'AccessKeyMetadata': [
                {
                    'UserName': 'test-user',
                    'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE'
                },
                {
                    'UserName': 'test-user',
                    'AccessKeyId': 'AKIAI44QH8DHBEXAMPLE'
                }
            ]
        }
        
        # Mock create_access_key response
        mock_client.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': 'AKIAINEWKEY123456789',
                'SecretAccessKey': 'newSecretKey123456789',
                'UserName': 'test-user'
            }
        }
        
        # Run the main function
        password_rotate.main()
        
        # Verify both access keys were deleted
        assert mock_client.delete_access_key.call_count == 2
        
        # Verify the calls were made with correct parameters
        delete_calls = mock_client.delete_access_key.call_args_list
        assert any(call[1]['AccessKeyId'] == 'AKIAIOSFODNN7EXAMPLE' for call in delete_calls)
        assert any(call[1]['AccessKeyId'] == 'AKIAI44QH8DHBEXAMPLE' for call in delete_calls)

    @patch('P67_awstools.password_rotate.boto3.client')
    @patch('builtins.input')
    def test_main_function_no_access_keys(self, mock_input, mock_boto_client):
        """Test handling when user has no access keys."""
        # Mock user inputs
        mock_input.side_effect = ['old_password', 'new_password']
        
        # Mock IAM client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock list_access_keys response with no keys
        mock_client.list_access_keys.return_value = {
            'AccessKeyMetadata': []
        }
        
        # This should raise an error because the code tries to access access_key['UserName']
        # when there are no access keys, which is a bug in the original code
        with pytest.raises(UnboundLocalError):
            password_rotate.main()

    @patch('P67_awstools.password_rotate.boto3.client')
    @patch('builtins.input')
    def test_main_function_password_change_error(self, mock_input, mock_boto_client):
        """Test handling password change errors."""
        # Mock user inputs
        mock_input.side_effect = ['wrong_password', 'new_password']
        
        # Mock IAM client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock password change to raise an exception
        from botocore.exceptions import ClientError
        mock_client.change_password.side_effect = ClientError(
            {'Error': {'Code': 'InvalidUserPassword', 'Message': 'Invalid password'}},
            'ChangePassword'
        )
        
        # Should raise the exception
        with pytest.raises(ClientError):
            password_rotate.main()
        
        # Verify password change was attempted
        mock_client.change_password.assert_called_once()
        
        # Verify no access key operations were performed
        mock_client.list_access_keys.assert_not_called()
        mock_client.delete_access_key.assert_not_called()
        mock_client.create_access_key.assert_not_called()

    @patch('P67_awstools.password_rotate.boto3.client')
    @patch('builtins.input')
    def test_main_function_access_key_deletion_error(self, mock_input, mock_boto_client):
        """Test handling access key deletion errors."""
        # Mock user inputs
        mock_input.side_effect = ['old_password', 'new_password']
        
        # Mock IAM client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful password change
        mock_client.change_password.return_value = {}
        
        # Mock list_access_keys response
        mock_client.list_access_keys.return_value = {
            'AccessKeyMetadata': [
                {
                    'UserName': 'test-user',
                    'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE'
                }
            ]
        }
        
        # Mock access key deletion to raise an exception
        from botocore.exceptions import ClientError
        mock_client.delete_access_key.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchEntity', 'Message': 'Access key not found'}},
            'DeleteAccessKey'
        )
        
        # Should raise the exception
        with pytest.raises(ClientError):
            password_rotate.main()
        
        # Verify password was changed
        mock_client.change_password.assert_called_once()
        
        # Verify access key deletion was attempted
        mock_client.delete_access_key.assert_called_once()
        
        # Verify new access key creation was not attempted
        mock_client.create_access_key.assert_not_called()

    @patch('P67_awstools.password_rotate.boto3.client')
    @patch('builtins.input')
    def test_main_function_create_access_key_error(self, mock_input, mock_boto_client):
        """Test handling access key creation errors."""
        # Mock user inputs
        mock_input.side_effect = ['old_password', 'new_password']
        
        # Mock IAM client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful operations up to access key creation
        mock_client.change_password.return_value = {}
        mock_client.list_access_keys.return_value = {
            'AccessKeyMetadata': [
                {
                    'UserName': 'test-user',
                    'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE'
                }
            ]
        }
        mock_client.delete_access_key.return_value = {}
        
        # Mock access key creation to raise an exception
        from botocore.exceptions import ClientError
        mock_client.create_access_key.side_effect = ClientError(
            {'Error': {'Code': 'LimitExceeded', 'Message': 'Access key limit exceeded'}},
            'CreateAccessKey'
        )
        
        # Should raise the exception
        with pytest.raises(ClientError):
            password_rotate.main()
        
        # Verify all operations up to creation were performed
        mock_client.change_password.assert_called_once()
        mock_client.list_access_keys.assert_called_once()
        mock_client.delete_access_key.assert_called_once()
        mock_client.create_access_key.assert_called_once()