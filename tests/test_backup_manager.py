"""Tests for the Backup Manager module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from P67_awstools import backup_manager


class TestBackupManager:
    """Test cases for Backup Manager functionality."""

    @patch('P67_awstools.backup_manager.boto3.client')
    def test_get_all_volumes(self, mock_boto_client):
        """Test retrieving all EBS volumes across regions."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock regions
        mock_client.describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}]
        }
        
        # Mock volumes
        mock_client.describe_volumes.return_value = {
            'Volumes': [
                {
                    'VolumeId': 'vol-12345',
                    'State': 'in-use',
                    'Size': 100
                },
                {
                    'VolumeId': 'vol-67890',
                    'State': 'available',
                    'Size': 50
                }
            ]
        }
        
        result = backup_manager.get_all_ebs_volumes()
        
        # Should have 2 volumes from 1 region
        assert len(result) == 2
        assert all('Region' in vol for vol in result)
        assert all(vol['Region'] == 'us-east-1' for vol in result)

    @patch('P67_awstools.backup_manager.boto3.client')
    def test_get_all_snapshots(self, mock_boto_client):
        """Test retrieving all EBS snapshots."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock regions
        mock_client.describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}]
        }
        
        # Mock snapshots
        mock_client.describe_snapshots.return_value = {
            'Snapshots': [
                {
                    'SnapshotId': 'snap-12345',
                    'VolumeId': 'vol-12345',
                    'StartTime': datetime.now() - timedelta(days=1),
                    'State': 'completed'
                }
            ]
        }
        
        result = backup_manager.get_all_snapshots()
        
        assert len(result) == 1
        assert result[0]['SnapshotId'] == 'snap-12345'
        assert 'Region' in result[0]

    def test_find_volumes_needing_backup_recent_snapshots(self):
        """Test finding volumes that need backup when recent snapshots exist."""
        from datetime import timezone
        volumes = [
            {
                'VolumeId': 'vol-12345',
                'Region': 'us-east-1',
                'State': 'in-use'
            }
        ]
        
        recent_snapshot = datetime.now(timezone.utc) - timedelta(days=3)
        snapshots = [
            {
                'VolumeId': 'vol-12345',
                'StartTime': recent_snapshot,
                'Region': 'us-east-1'
            }
        ]
        
        result = backup_manager.find_volumes_without_recent_snapshots(volumes, snapshots, days_threshold=7)
        
        # Volume has recent backup, should not need backup
        assert len(result) == 0

    def test_find_volumes_needing_backup_old_snapshots(self):
        """Test finding volumes that need backup when snapshots are old."""
        from datetime import timezone
        volumes = [
            {
                'VolumeId': 'vol-12345',
                'Region': 'us-east-1',
                'State': 'in-use'
            }
        ]
        
        old_snapshot = datetime.now(timezone.utc) - timedelta(days=10)
        snapshots = [
            {
                'VolumeId': 'vol-12345',
                'StartTime': old_snapshot,
                'Region': 'us-east-1'
            }
        ]
        
        result = backup_manager.find_volumes_without_recent_snapshots(volumes, snapshots, days_threshold=7)
        
        # Volume has old backup, should need backup
        assert len(result) == 1
        assert result[0]['volume']['VolumeId'] == 'vol-12345'
        assert result[0]['latest_snapshot']['StartTime'] == old_snapshot

    def test_find_volumes_needing_backup_no_snapshots(self):
        """Test finding volumes that need backup when no snapshots exist."""
        volumes = [
            {
                'VolumeId': 'vol-12345',
                'Region': 'us-east-1',
                'State': 'in-use'
            }
        ]
        
        snapshots = []  # No snapshots
        
        result = backup_manager.find_volumes_without_recent_snapshots(volumes, snapshots, days_threshold=7)
        
        # Volume has no backup, should need backup
        assert len(result) == 1
        assert result[0]['volume']['VolumeId'] == 'vol-12345'
        assert result[0]['latest_snapshot'] is None

    def test_find_old_snapshots(self):
        """Test finding old snapshots."""
        from datetime import timezone
        old_date = datetime.now(timezone.utc) - timedelta(days=35)
        recent_date = datetime.now(timezone.utc) - timedelta(days=5)
        
        snapshots = [
            {
                'SnapshotId': 'snap-old',
                'StartTime': old_date,
                'VolumeSize': 100,
                'Region': 'us-east-1'
            },
            {
                'SnapshotId': 'snap-recent',
                'StartTime': recent_date,
                'VolumeSize': 50,
                'Region': 'us-east-1'
            }
        ]
        
        result = backup_manager.find_old_snapshots(snapshots, days_threshold=30)
        
        # Should only find the old snapshot
        assert len(result) == 1
        assert result[0]['snapshot']['SnapshotId'] == 'snap-old'
        assert result[0]['age_days'] == 35
        assert result[0]['estimated_monthly_cost'] == 5.0  # 100GB * $0.05

    @patch('P67_awstools.backup_manager.boto3.client')
    def test_get_rds_instances(self, mock_boto_client):
        """Test retrieving RDS instances."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock regions
        mock_client.describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}]
        }
        
        # Mock RDS instances
        mock_client.describe_db_instances.return_value = {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-db',
                    'DBInstanceStatus': 'available',
                    'BackupRetentionPeriod': 7,
                    'DeletionProtection': True
                }
            ]
        }
        
        result = backup_manager.get_all_rds_instances()
        
        assert len(result) == 1
        assert result[0]['DBInstanceIdentifier'] == 'test-db'
        assert 'Region' in result[0]

    def test_analyze_rds_backup_configuration_good(self):
        """Test analyzing RDS backup configuration with good settings."""
        instances = [
            {
                'DBInstanceIdentifier': 'good-db',
                'BackupRetentionPeriod': 7,
                'DeletionProtection': True,
                'PreferredBackupWindow': '03:00-04:00',
                'PreferredMaintenanceWindow': 'sun:04:00-sun:05:00',
                'Region': 'us-east-1'
            }
        ]
        
        result = backup_manager.verify_rds_backups(instances)
        
        # Good configuration, no issues
        assert len(result) == 0

    def test_analyze_rds_backup_configuration_issues(self):
        """Test analyzing RDS backup configuration with issues."""
        instances = [
            {
                'DBInstanceIdentifier': 'bad-db',
                'BackupRetentionPeriod': 1,  # Too short
                'DeletionProtection': False,  # Not protected
                'Region': 'us-east-1'
            }
        ]
        
        result = backup_manager.verify_rds_backups(instances)
        
        # Should find issues
        assert len(result) == 1
        assert result[0]['instance']['DBInstanceIdentifier'] == 'bad-db'
        assert len(result[0]['issues']) >= 2
        
        issues = result[0]['issues']
        assert any('retention period' in issue for issue in issues)
        assert any('Deletion protection is disabled' in issue for issue in issues)

    @patch('P67_awstools.backup_manager.boto3.client')
    def test_create_ebs_snapshot_success(self, mock_boto_client):
        """Test successful EBS snapshot creation."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock describe_volumes call
        mock_client.describe_volumes.return_value = {
            'Volumes': [{'VolumeId': 'vol-12345', 'Size': 100}]
        }
        
        mock_client.create_snapshot.return_value = {
            'SnapshotId': 'snap-new123',
            'State': 'pending'
        }
        
        result = backup_manager.create_ebs_snapshots(['vol-12345'], 'us-east-1')
        
        assert len(result) == 1
        assert result[0]['volume_id'] == 'vol-12345'
        assert result[0]['snapshot_id'] == 'snap-new123'
        assert result[0]['region'] == 'us-east-1'

    @patch('P67_awstools.backup_manager.boto3.client')
    def test_create_ebs_snapshot_failure(self, mock_boto_client):
        """Test EBS snapshot creation failure."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.describe_volumes.side_effect = Exception("Volume not found")
        
        result = backup_manager.create_ebs_snapshots(['vol-invalid'], 'us-east-1')
        
        # Function continues on error, so result should be empty list
        assert len(result) == 0

    @patch('P67_awstools.backup_manager.boto3.client')
    def test_copy_snapshot_to_region_success(self, mock_boto_client):
        """Test successful snapshot copying to another region."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.copy_snapshot.return_value = {
            'SnapshotId': 'snap-copy123'
        }
        
        # Format snapshots as expected by the function (with 'snapshot' key)
        snapshots = [{'snapshot': {'SnapshotId': 'snap-12345'}}]
        result = backup_manager.copy_snapshots_cross_region(
            snapshots, 'us-east-1', 'us-west-2', max_copies=1
        )
        
        assert len(result) == 1
        assert result[0]['source_snapshot_id'] == 'snap-12345'
        assert result[0]['target_snapshot_id'] == 'snap-copy123'
        assert result[0]['source_region'] == 'us-east-1'
        assert result[0]['target_region'] == 'us-west-2'

    @patch('P67_awstools.backup_manager.get_all_ebs_volumes')
    @patch('P67_awstools.backup_manager.get_all_snapshots')
    @patch('P67_awstools.backup_manager.find_volumes_without_recent_snapshots')
    @patch('P67_awstools.backup_manager.find_old_snapshots')
    @patch('P67_awstools.backup_manager.get_all_rds_instances')
    @patch('P67_awstools.backup_manager.get_all_rds_snapshots')
    @patch('P67_awstools.backup_manager.verify_rds_backups')
    def test_generate_backup_report(self, mock_rds_config, mock_rds_snapshots, mock_rds_instances, 
                                  mock_old_snapshots, mock_volumes_needing_backup,
                                  mock_snapshots, mock_volumes):
        """Test the main backup report generation function."""
        # Mock all the data
        mock_volumes.return_value = [{'VolumeId': 'vol-123'}]
        mock_snapshots.return_value = [{'SnapshotId': 'snap-123'}]
        mock_volumes_needing_backup.return_value = []
        mock_old_snapshots.return_value = []
        mock_rds_instances.return_value = [{'DBInstanceIdentifier': 'test-db'}]
        mock_rds_snapshots.return_value = [{'DBSnapshotIdentifier': 'rds-snap-123'}]
        mock_rds_config.return_value = []
        
        result = backup_manager.generate_backup_report()
        
        # Verify structure
        assert 'timestamp' in result
        assert 'summary' in result
        assert 'findings' in result
        
        # Verify summary structure
        assert 'total_ebs_volumes' in result['summary']
        assert 'total_ebs_snapshots' in result['summary']
        assert 'total_rds_instances' in result['summary']
        assert 'total_rds_snapshots' in result['summary']
        
        # Verify findings structure
        assert 'volumes_needing_backup' in result['findings']
        assert 'old_snapshots' in result['findings']
        assert 'rds_backup_issues' in result['findings']
        
        # Verify all functions were called
        mock_volumes.assert_called_once()
        mock_snapshots.assert_called_once()
        mock_rds_instances.assert_called_once()

    @patch('P67_awstools.backup_manager.generate_backup_report')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_main_function_report_option(self, mock_print, mock_input, mock_generate_report):
        """Test the main function with report generation option."""
        mock_input.return_value = '1'  # Select report option
        mock_report = {
            'total_volumes': 10,
            'volumes_needing_backup': [],
            'old_snapshots': [],
            'rds_backup_issues': []
        }
        mock_generate_report.return_value = mock_report
        
        backup_manager.main()
        
        mock_generate_report.assert_called_once()
        
        # Verify some output was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("AWS Backup Manager" in call for call in print_calls)

    def test_empty_lists_handling(self):
        """Test functions handle empty lists gracefully."""
        assert backup_manager.find_volumes_without_recent_snapshots([], []) == []
        assert backup_manager.find_old_snapshots([]) == []