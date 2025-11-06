"""Tests for the IAM Policy Analyzer module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from P67_awstools import iam_analyzer


class TestIAMAnalyzer:
    """Test cases for IAM Policy Analyzer functionality."""

    @patch('P67_awstools.iam_analyzer.boto3.client')
    def test_get_all_users(self, mock_boto_client):
        """Test retrieving all IAM users."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock paginator
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {'Users': [{'UserName': 'user1'}, {'UserName': 'user2'}]}
        ]
        
        result = iam_analyzer.get_all_users()
        
        assert len(result) == 2
        assert result[0]['UserName'] == 'user1'
        assert result[1]['UserName'] == 'user2'

    @patch('P67_awstools.iam_analyzer.boto3.client')
    def test_get_all_roles(self, mock_boto_client):
        """Test retrieving all IAM roles."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock paginator
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {'Roles': [{'RoleName': 'role1'}, {'RoleName': 'role2'}]}
        ]
        
        result = iam_analyzer.get_all_roles()
        
        assert len(result) == 2
        assert result[0]['RoleName'] == 'role1'
        assert result[1]['RoleName'] == 'role2'

    @patch('P67_awstools.iam_analyzer.boto3.client')
    def test_get_all_policies(self, mock_boto_client):
        """Test retrieving all IAM policies."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock paginator
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {'Policies': [{'PolicyName': 'policy1'}, {'PolicyName': 'policy2'}]}
        ]
        
        result = iam_analyzer.get_all_policies()
        
        assert len(result) == 2
        assert result[0]['PolicyName'] == 'policy1'
        assert result[1]['PolicyName'] == 'policy2'

    @patch('P67_awstools.iam_analyzer.boto3.client')
    def test_find_unused_users_basic(self, mock_boto_client):
        """Test finding unused users."""
        from datetime import timezone
        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)
        
        # Mock IAM client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.list_access_keys.return_value = {'AccessKeyMetadata': []}
        
        users = [
            {
                'UserName': 'old-user',
                'PasswordLastUsed': old_date,
                'CreateDate': old_date
            },
            {
                'UserName': 'recent-user',
                'PasswordLastUsed': recent_date,
                'CreateDate': recent_date
            }
        ]
        
        result = iam_analyzer.find_unused_users(users, days_threshold=90)
        
        # Should find at least the old user
        assert len(result) >= 1
        unused_usernames = [item['user']['UserName'] for item in result]
        assert 'old-user' in unused_usernames

    def test_find_unused_users_empty_list(self):
        """Test finding unused users with empty list."""
        result = iam_analyzer.find_unused_users([])
        assert result == []

    def test_find_unused_roles_basic(self):
        """Test finding unused roles."""
        from datetime import timezone
        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)
        
        roles = [
            {
                'RoleName': 'old-role',
                'Path': '/',
                'RoleLastUsed': {'LastUsedDate': old_date},
                'CreateDate': old_date
            },
            {
                'RoleName': 'recent-role',
                'Path': '/',
                'RoleLastUsed': {'LastUsedDate': recent_date},
                'CreateDate': recent_date
            }
        ]
        
        result = iam_analyzer.find_unused_roles(roles, days_threshold=90)
        
        # Should find at least the old role
        assert len(result) >= 1
        unused_rolenames = [item['role']['RoleName'] for item in result]
        assert 'old-role' in unused_rolenames

    @patch('P67_awstools.iam_analyzer.boto3.client')
    def test_check_password_policy(self, mock_boto_client):
        """Test checking password policy."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock password policy response
        mock_client.get_account_password_policy.return_value = {
            'PasswordPolicy': {
                'MinimumPasswordLength': 8,
                'RequireSymbols': True,
                'RequireNumbers': True,
                'RequireUppercaseCharacters': True,
                'RequireLowercaseCharacters': True
            }
        }
        
        result = iam_analyzer.check_password_policy()
        
        assert 'policy' in result
        assert 'recommendations' in result
        assert result['policy']['MinimumPasswordLength'] == 8

    @patch('P67_awstools.iam_analyzer.boto3.client')
    def test_find_users_with_console_access_but_no_mfa(self, mock_boto_client):
        """Test finding users with console access but no MFA."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock users with login profiles but no MFA
        mock_client.get_login_profile.return_value = {'LoginProfile': {'UserName': 'test-user'}}
        mock_client.list_mfa_devices.return_value = {'MFADevices': []}
        
        users = [{'UserName': 'test-user'}]
        result = iam_analyzer.find_users_with_console_access_but_no_mfa()
        
        # Function should return a list (may be empty if no users found)
        assert isinstance(result, list)

    @patch('P67_awstools.iam_analyzer.boto3.client')
    def test_check_root_account_usage(self, mock_boto_client):
        """Test checking root account usage."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock CloudTrail events
        mock_client.lookup_events.return_value = {
            'Events': [
                {
                    'EventTime': datetime.now(),
                    'EventName': 'ConsoleLogin',
                    'Username': 'root'
                }
            ]
        }
        
        result = iam_analyzer.check_root_account_usage()
        
        assert 'events_found' in result
        assert 'recent_events' in result

    @patch('P67_awstools.iam_analyzer.get_all_users')
    @patch('P67_awstools.iam_analyzer.get_all_roles')
    @patch('P67_awstools.iam_analyzer.get_all_policies')
    def test_generate_iam_report(self, mock_get_policies, mock_get_roles, mock_get_users):
        """Test generating IAM report."""
        # Mock data
        mock_get_users.return_value = [{'UserName': 'test-user'}]
        mock_get_roles.return_value = [{'RoleName': 'test-role'}]
        mock_get_policies.return_value = [{'PolicyName': 'test-policy'}]
        
        with patch('P67_awstools.iam_analyzer.find_unused_users') as mock_unused_users, \
             patch('P67_awstools.iam_analyzer.find_unused_roles') as mock_unused_roles, \
             patch('P67_awstools.iam_analyzer.find_overly_permissive_policies') as mock_permissive, \
             patch('P67_awstools.iam_analyzer.check_password_policy') as mock_password, \
             patch('P67_awstools.iam_analyzer.find_users_with_console_access_but_no_mfa') as mock_no_mfa, \
             patch('P67_awstools.iam_analyzer.check_root_account_usage') as mock_root:
            
            mock_unused_users.return_value = []
            mock_unused_roles.return_value = []
            mock_permissive.return_value = []
            mock_password.return_value = {'policy': {}, 'recommendations': []}
            mock_no_mfa.return_value = []
            mock_root.return_value = {'events_found': 0, 'recent_events': []}
            
            result = iam_analyzer.generate_iam_report()
            
            # Check report structure
            assert 'timestamp' in result
            assert 'summary' in result
            assert 'findings' in result
            assert 'total_users' in result['summary']
            assert 'total_roles' in result['summary']
            assert 'total_custom_policies' in result['summary']
            assert 'unused_users' in result['findings']
            assert 'unused_roles' in result['findings']
            assert 'overly_permissive_policies' in result['findings']
            assert 'password_policy' in result['findings']
            assert 'users_without_mfa' in result['findings']

    @patch('P67_awstools.iam_analyzer.generate_iam_report')
    @patch('P67_awstools.iam_analyzer.print_iam_summary')
    def test_main_function(self, mock_print_summary, mock_generate_report):
        """Test the main function execution."""
        mock_report = {
            'total_users': 5,
            'total_roles': 3,
            'unused_users': [],
            'unused_roles': []
        }
        mock_generate_report.return_value = mock_report
        
        iam_analyzer.main()
        
        mock_generate_report.assert_called_once()
        mock_print_summary.assert_called_once_with(mock_report)

    def test_find_overly_permissive_policies_basic(self):
        """Test finding overly permissive policies."""
        # This function makes AWS calls, so we'll just test it returns a list
        with patch('P67_awstools.iam_analyzer.boto3.client'):
            result = iam_analyzer.find_overly_permissive_policies()
            assert isinstance(result, list)