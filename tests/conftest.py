"""Pytest configuration and fixtures for P67 AWS Tools tests."""

import pytest
import boto3
from moto import mock_ec2, mock_iam, mock_rds, mock_s3, mock_lambda
from datetime import datetime, timedelta


@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def ec2_client(mock_aws_credentials):
    """Create a mocked EC2 client."""
    with mock_ec2():
        yield boto3.client("ec2", region_name="us-east-1")


@pytest.fixture
def iam_client(mock_aws_credentials):
    """Create a mocked IAM client."""
    with mock_iam():
        yield boto3.client("iam", region_name="us-east-1")


@pytest.fixture
def rds_client(mock_aws_credentials):
    """Create a mocked RDS client."""
    with mock_rds():
        yield boto3.client("rds", region_name="us-east-1")


@pytest.fixture
def s3_client(mock_aws_credentials):
    """Create a mocked S3 client."""
    with mock_s3():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def lambda_client(mock_aws_credentials):
    """Create a mocked Lambda client."""
    with mock_lambda():
        yield boto3.client("lambda", region_name="us-east-1")


@pytest.fixture
def sample_security_group():
    """Sample security group data for testing."""
    return {
        'GroupId': 'sg-12345678',
        'GroupName': 'test-sg',
        'Description': 'Test security group',
        'VpcId': 'vpc-12345678',
        'Region': 'us-east-1',
        'IpPermissions': [
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP access'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '10.0.0.0/8', 'Description': 'SSH access'}]
            }
        ],
        'IpPermissionsEgress': [
            {
                'IpProtocol': '-1',
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    }


@pytest.fixture
def sample_iam_user():
    """Sample IAM user data for testing."""
    return {
        'UserName': 'test-user',
        'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
        'Arn': 'arn:aws:iam::123456789012:user/test-user',
        'Path': '/',
        'CreateDate': datetime.now() - timedelta(days=100),
        'PasswordLastUsed': datetime.now() - timedelta(days=95)
    }


@pytest.fixture
def sample_iam_role():
    """Sample IAM role data for testing."""
    return {
        'RoleName': 'test-role',
        'RoleId': 'AROADBQP57FF2AEXAMPLE',
        'Arn': 'arn:aws:iam::123456789012:role/test-role',
        'Path': '/',
        'CreateDate': datetime.now() - timedelta(days=50),
        'RoleLastUsed': {
            'LastUsedDate': datetime.now() - timedelta(days=95)
        }
    }