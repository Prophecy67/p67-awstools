"""Tests for the Cross Account Finder module."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from P67_awstools import cross_account_finder


class TestCrossAccountFinder:
    """Test cases for Cross Account Finder functionality."""

    @patch('P67_awstools.cross_account_finder.boto3.client')
    def test_get_all_s3_buckets(self, mock_boto_client):
        """Test retrieving all S3 buckets."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.list_buckets.return_value = {
            'Buckets': [
                {'Name': 'test-bucket-1', 'CreationDate': datetime.now(timezone.utc)},
                {'Name': 'test-bucket-2', 'CreationDate': datetime.now(timezone.utc)}
            ]
        }
        
        # Mock get_bucket_location calls
        mock_client.get_bucket_location.return_value = {'LocationConstraint': 'us-west-2'}
        
        result = cross_account_finder.scan_s3_buckets()
        
        assert len(result) == 2
        assert result[0]['name'] == 'test-bucket-1'
        assert result[1]['name'] == 'test-bucket-2'
        assert result[0]['resource_type'] == 'S3 Bucket'
        assert result[0]['account'] == 'default'
        assert result[0]['region'] == 'us-west-2'

    def test_get_account_id(self):
        """Test getting account ID."""
        with patch('P67_awstools.cross_account_finder.boto3.client') as mock_boto_client:
            mock_client = MagicMock()
            mock_boto_client.return_value = mock_client
            
            mock_client.get_caller_identity.return_value = {
                'Account': '123456789012'
            }
            
            result = cross_account_finder.get_account_id()
            
            assert result == '123456789012'

    def test_get_all_regions(self):
        """Test getting all AWS regions."""
        with patch('P67_awstools.cross_account_finder.boto3.client') as mock_boto_client:
            mock_client = MagicMock()
            mock_boto_client.return_value = mock_client
            
            mock_client.describe_regions.return_value = {
                'Regions': [
                    {'RegionName': 'us-east-1'},
                    {'RegionName': 'us-west-2'},
                    {'RegionName': 'eu-west-1'}
                ]
            }
            
            result = cross_account_finder.get_all_regions()
            
            assert len(result) == 3
            assert 'us-east-1' in result
            assert 'us-west-2' in result
            assert 'eu-west-1' in result

    @patch('P67_awstools.cross_account_finder.boto3.client')
    def test_get_all_lambda_functions(self, mock_boto_client):
        """Test retrieving all Lambda functions across regions."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock regions
        mock_client.describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}, {'RegionName': 'us-west-2'}]
        }
        
        # Mock Lambda functions
        mock_client.list_functions.return_value = {
            'Functions': [
                {
                    'FunctionName': 'test-function-1',
                    'Runtime': 'python3.9',
                    'LastModified': '2023-01-01T00:00:00.000+0000'
                },
                {
                    'FunctionName': 'test-function-2',
                    'Runtime': 'nodejs18.x',
                    'LastModified': '2023-01-02T00:00:00.000+0000'
                }
            ]
        }
        
        result = cross_account_finder.scan_lambda_functions('us-east-1')
        
        # Should have 2 functions in the region
        assert len(result) == 2
        assert result[0]['name'] == 'test-function-1'
        assert result[1]['name'] == 'test-function-2'
        assert result[0]['resource_type'] == 'Lambda Function'
        assert result[0]['runtime'] == 'python3.9'
        assert result[0]['region'] == 'us-east-1'
        assert result[0]['account'] == 'default'

    def test_get_resource_name(self):
        """Test extracting resource name from tags."""
        # Test with Name tag
        tags_with_name = [
            {'Key': 'Environment', 'Value': 'prod'},
            {'Key': 'Name', 'Value': 'my-resource'},
            {'Key': 'Owner', 'Value': 'team-a'}
        ]
        
        result = cross_account_finder.get_resource_name(tags_with_name)
        assert result == 'my-resource'
        
        # Test without Name tag
        tags_without_name = [
            {'Key': 'Environment', 'Value': 'prod'},
            {'Key': 'Owner', 'Value': 'team-a'}
        ]
        
        result = cross_account_finder.get_resource_name(tags_without_name)
        assert result == 'N/A'

    def test_search_resources_by_name(self):
        """Test searching resources by name."""
        all_resources = [
            {'name': 'web-server-1', 'resource_type': 'EC2 Instance'},
            {'name': 'database-prod', 'resource_type': 'RDS Instance'},
            {'name': 'web-server-2', 'resource_type': 'EC2 Instance'},
            {'name': 'cache-redis', 'resource_type': 'ElastiCache'}
        ]
        
        # Search for web servers
        result = cross_account_finder.search_resources_by_name(all_resources, 'web-server')
        assert len(result) == 2
        assert all('web-server' in resource['name'] for resource in result)
        
        # Search for database
        result = cross_account_finder.search_resources_by_name(all_resources, 'database')
        assert len(result) == 1
        assert result[0]['name'] == 'database-prod'

    def test_generate_inventory_report(self):
        """Test generating inventory report."""
        all_resources = [
            {'resource_type': 'EC2 Instance', 'name': 'web-server-1', 'account': 'prod', 'region': 'us-east-1'},
            {'resource_type': 'EC2 Instance', 'name': 'web-server-2', 'account': 'prod', 'region': 'us-west-2'},
            {'resource_type': 'RDS Instance', 'name': 'database-prod', 'account': 'prod', 'region': 'us-east-1'},
            {'resource_type': 'S3 Bucket', 'name': 'data-bucket', 'account': 'dev', 'region': 'us-east-1'}
        ]
        
        result = cross_account_finder.generate_inventory_report(all_resources)
        
        assert 'summary' in result
        assert 'by_type' in result
        assert 'by_account' in result
        assert 'by_region' in result
        assert 'timestamp' in result
        assert result['total_resources'] == 4
        assert result['by_type']['EC2 Instance'] == 2
        assert result['by_type']['RDS Instance'] == 1
        assert result['by_account']['prod']['EC2 Instance'] == 2
        assert result['by_account']['prod']['RDS Instance'] == 1
        assert result['by_region']['us-east-1']['EC2 Instance'] == 1
        assert result['by_region']['us-east-1']['RDS Instance'] == 1

    @patch('P67_awstools.cross_account_finder.boto3.Session')
    def test_load_account_profiles(self, mock_session_class):
        """Test loading account profiles."""
        # Test with single profile (should return default profile)
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.available_profiles = ['default']
        
        result = cross_account_finder.load_account_profiles()
        assert len(result) == 1
        assert result[0]['name'] == 'default'
        assert result[0]['profile'] is None