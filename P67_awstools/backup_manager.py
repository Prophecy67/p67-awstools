#!/usr/bin/env python3

import boto3
import json
from datetime import datetime, timedelta
from collections import defaultdict

def get_all_ebs_volumes():
    """Get all EBS volumes across all regions"""
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    all_volumes = []
    for region in regions:
        try:
            regional_client = boto3.client('ec2', region_name=region)
            response = regional_client.describe_volumes()
            for volume in response['Volumes']:
                volume['Region'] = region
                all_volumes.append(volume)
        except Exception as e:
            print(f"Warning: Could not access region {region}: {e}")
    
    return all_volumes

def get_all_snapshots():
    """Get all EBS snapshots owned by the account"""
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    all_snapshots = []
    for region in regions:
        try:
            regional_client = boto3.client('ec2', region_name=region)
            response = regional_client.describe_snapshots(OwnerIds=['self'])
            for snapshot in response['Snapshots']:
                snapshot['Region'] = region
                all_snapshots.append(snapshot)
        except Exception as e:
            print(f"Warning: Could not access region {region}: {e}")
    
    return all_snapshots

def get_all_rds_instances():
    """Get all RDS instances across all regions"""
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    all_instances = []
    for region in regions:
        try:
            regional_client = boto3.client('rds', region_name=region)
            response = regional_client.describe_db_instances()
            for instance in response['DBInstances']:
                instance['Region'] = region
                all_instances.append(instance)
        except Exception as e:
            print(f"Warning: Could not access RDS in region {region}: {e}")
    
    return all_instances

def get_all_rds_snapshots():
    """Get all RDS snapshots across all regions"""
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    all_snapshots = []
    for region in regions:
        try:
            regional_client = boto3.client('rds', region_name=region)
            
            # Get DB snapshots
            response = regional_client.describe_db_snapshots(SnapshotType='manual')
            for snapshot in response['DBSnapshots']:
                snapshot['Region'] = region
                snapshot['Type'] = 'DB'
                all_snapshots.append(snapshot)
            
            # Get cluster snapshots
            try:
                response = regional_client.describe_db_cluster_snapshots(SnapshotType='manual')
                for snapshot in response['DBClusterSnapshots']:
                    snapshot['Region'] = region
                    snapshot['Type'] = 'Cluster'
                    all_snapshots.append(snapshot)
            except Exception:
                pass  # Not all regions support clusters
            
        except Exception as e:
            print(f"Warning: Could not access RDS snapshots in region {region}: {e}")
    
    return all_snapshots

def find_volumes_without_recent_snapshots(volumes, snapshots, days_threshold=7):
    """Find volumes that don't have recent snapshots"""
    cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days_threshold)
    
    # Group snapshots by volume ID
    volume_snapshots = defaultdict(list)
    for snapshot in snapshots:
        if snapshot.get('VolumeId'):
            volume_snapshots[snapshot['VolumeId']].append(snapshot)
    
    volumes_needing_backup = []
    
    for volume in volumes:
        volume_id = volume['VolumeId']
        region = volume['Region']
        
        # Get snapshots for this volume
        vol_snapshots = volume_snapshots.get(volume_id, [])
        
        # Check if any recent snapshots exist
        has_recent_snapshot = False
        latest_snapshot = None
        
        for snapshot in vol_snapshots:
            if snapshot['StartTime'] >= cutoff_date:
                has_recent_snapshot = True
                break
            if not latest_snapshot or snapshot['StartTime'] > latest_snapshot['StartTime']:
                latest_snapshot = snapshot
        
        if not has_recent_snapshot:
            volumes_needing_backup.append({
                'volume': volume,
                'latest_snapshot': latest_snapshot,
                'snapshot_count': len(vol_snapshots)
            })
    
    return volumes_needing_backup

def find_old_snapshots(snapshots, days_threshold=30):
    """Find snapshots older than threshold that might be candidates for deletion"""
    cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days_threshold)
    
    old_snapshots = []
    for snapshot in snapshots:
        if snapshot['StartTime'] < cutoff_date:
            # Calculate age and size for cost estimation
            age_days = (datetime.now(datetime.now().astimezone().tzinfo) - snapshot['StartTime']).days
            size_gb = snapshot.get('VolumeSize', 0)
            
            old_snapshots.append({
                'snapshot': snapshot,
                'age_days': age_days,
                'size_gb': size_gb,
                'estimated_monthly_cost': size_gb * 0.05  # Rough estimate: $0.05 per GB per month
            })
    
    return sorted(old_snapshots, key=lambda x: x['age_days'], reverse=True)

def create_ebs_snapshots(volume_ids, region):
    """Create snapshots for specified EBS volumes"""
    ec2_client = boto3.client('ec2', region_name=region)
    created_snapshots = []
    
    for volume_id in volume_ids:
        try:
            # Get volume info for description
            volume_info = ec2_client.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
            
            # Create snapshot
            response = ec2_client.create_snapshot(
                VolumeId=volume_id,
                Description=f"Backup of {volume_id} created by p67-awstools on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            created_snapshots.append({
                'volume_id': volume_id,
                'snapshot_id': response['SnapshotId'],
                'region': region
            })
            
            print(f"✅ Created snapshot {response['SnapshotId']} for volume {volume_id}")
            
        except Exception as e:
            print(f"❌ Failed to create snapshot for volume {volume_id}: {e}")
    
    return created_snapshots

def verify_rds_backups(rds_instances):
    """Verify RDS backup configuration"""
    backup_issues = []
    
    for instance in rds_instances:
        issues = []
        
        # Check if automated backups are enabled
        if not instance.get('BackupRetentionPeriod', 0):
            issues.append("Automated backups are disabled")
        elif instance.get('BackupRetentionPeriod', 0) < 7:
            issues.append(f"Backup retention period is only {instance.get('BackupRetentionPeriod')} days (recommend 7+)")
        
        # Check backup window
        if not instance.get('PreferredBackupWindow'):
            issues.append("No preferred backup window configured")
        
        # Check maintenance window
        if not instance.get('PreferredMaintenanceWindow'):
            issues.append("No preferred maintenance window configured")
        
        # Check if deletion protection is enabled
        if not instance.get('DeletionProtection', False):
            issues.append("Deletion protection is disabled")
        
        if issues:
            backup_issues.append({
                'instance': instance,
                'issues': issues
            })
    
    return backup_issues

def copy_snapshots_cross_region(snapshots, source_region, target_region, max_copies=5):
    """Copy snapshots to another region for disaster recovery"""
    source_client = boto3.client('ec2', region_name=source_region)
    target_client = boto3.client('ec2', region_name=target_region)
    
    copied_snapshots = []
    
    for i, snapshot_info in enumerate(snapshots[:max_copies]):
        snapshot = snapshot_info['snapshot']
        try:
            # Copy snapshot to target region
            response = target_client.copy_snapshot(
                SourceRegion=source_region,
                SourceSnapshotId=snapshot['SnapshotId'],
                Description=f"Cross-region copy of {snapshot['SnapshotId']} from {source_region}"
            )
            
            copied_snapshots.append({
                'source_snapshot_id': snapshot['SnapshotId'],
                'target_snapshot_id': response['SnapshotId'],
                'source_region': source_region,
                'target_region': target_region
            })
            
            print(f"✅ Copying snapshot {snapshot['SnapshotId']} to {target_region} as {response['SnapshotId']}")
            
        except Exception as e:
            print(f"❌ Failed to copy snapshot {snapshot['SnapshotId']}: {e}")
    
    return copied_snapshots

def generate_backup_report():
    """Generate comprehensive backup status report"""
    print("Analyzing backup configuration across all regions...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'findings': {}
    }
    
    # Get all resources
    print("Gathering EBS volumes and snapshots...")
    volumes = get_all_ebs_volumes()
    snapshots = get_all_snapshots()
    
    print("Gathering RDS instances and snapshots...")
    rds_instances = get_all_rds_instances()
    rds_snapshots = get_all_rds_snapshots()
    
    report['summary'] = {
        'total_ebs_volumes': len(volumes),
        'total_ebs_snapshots': len(snapshots),
        'total_rds_instances': len(rds_instances),
        'total_rds_snapshots': len(rds_snapshots)
    }
    
    # Find volumes without recent backups
    print("Checking for volumes without recent snapshots...")
    volumes_needing_backup = find_volumes_without_recent_snapshots(volumes, snapshots)
    report['findings']['volumes_needing_backup'] = {
        'count': len(volumes_needing_backup),
        'volumes': volumes_needing_backup
    }
    
    # Find old snapshots
    print("Identifying old snapshots...")
    old_snapshots = find_old_snapshots(snapshots)
    report['findings']['old_snapshots'] = {
        'count': len(old_snapshots),
        'snapshots': old_snapshots,
        'total_estimated_cost': sum(s['estimated_monthly_cost'] for s in old_snapshots)
    }
    
    # Verify RDS backup configuration
    print("Verifying RDS backup configuration...")
    rds_backup_issues = verify_rds_backups(rds_instances)
    report['findings']['rds_backup_issues'] = {
        'count': len(rds_backup_issues),
        'instances': rds_backup_issues
    }
    
    return report

def print_backup_summary(report):
    """Print human-readable backup report summary"""
    print("=" * 60)
    print("AWS BACKUP MANAGEMENT REPORT")
    print("=" * 60)
    print(f"Generated: {report['timestamp']}")
    print(f"EBS Volumes: {report['summary']['total_ebs_volumes']}")
    print(f"EBS Snapshots: {report['summary']['total_ebs_snapshots']}")
    print(f"RDS Instances: {report['summary']['total_rds_instances']}")
    print(f"RDS Snapshots: {report['summary']['total_rds_snapshots']}")
    print()
    
    # Volumes needing backup
    volumes_needing_count = report['findings']['volumes_needing_backup']['count']
    print(f"💾 VOLUMES NEEDING BACKUP (7+ days): {volumes_needing_count}")
    if volumes_needing_count > 0:
        for item in report['findings']['volumes_needing_backup']['volumes'][:5]:
            volume = item['volume']
            latest = item['latest_snapshot']
            latest_str = latest['StartTime'].strftime('%Y-%m-%d') if latest else 'Never'
            print(f"  • {volume['VolumeId']} in {volume['Region']} (last backup: {latest_str})")
        if volumes_needing_count > 5:
            print(f"    ... and {volumes_needing_count - 5} more")
    print()
    
    # Old snapshots
    old_snapshots_count = report['findings']['old_snapshots']['count']
    total_cost = report['findings']['old_snapshots']['total_estimated_cost']
    print(f"🗑️  OLD SNAPSHOTS (30+ days): {old_snapshots_count} (Est. cost: ${total_cost:.2f}/month)")
    if old_snapshots_count > 0:
        for item in report['findings']['old_snapshots']['snapshots'][:5]:
            snapshot = item['snapshot']
            age = item['age_days']
            cost = item['estimated_monthly_cost']
            print(f"  • {snapshot['SnapshotId']} ({age} days old, ${cost:.2f}/month)")
        if old_snapshots_count > 5:
            print(f"    ... and {old_snapshots_count - 5} more")
    print()
    
    # RDS backup issues
    rds_issues_count = report['findings']['rds_backup_issues']['count']
    print(f"🗄️  RDS BACKUP ISSUES: {rds_issues_count} instances")
    if rds_issues_count > 0:
        for item in report['findings']['rds_backup_issues']['instances'][:3]:
            instance = item['instance']
            print(f"  • {instance['DBInstanceIdentifier']} in {instance['Region']}")
            for issue in item['issues'][:2]:
                print(f"    - {issue}")
        if rds_issues_count > 3:
            print(f"    ... and {rds_issues_count - 3} more")
    print()
    
    # Summary
    total_issues = volumes_needing_count + rds_issues_count
    if total_issues == 0:
        print("✅ No backup issues found! Your backup strategy looks good.")
    else:
        print(f"📊 SUMMARY: {total_issues} backup issues found")
        print("   Consider addressing these issues to improve your backup coverage.")

def main():
    """Main function for backup management"""
    print("AWS Backup Manager")
    print("=" * 20)
    print("1. Generate backup report")
    print("2. Create EBS snapshots")
    print("3. Copy snapshots to another region")
    print("4. Clean up old snapshots (interactive)")
    
    choice = input("\nSelect an option (1-4): ").strip()
    
    try:
        if choice == '1':
            # Generate backup report
            report = generate_backup_report()
            print_backup_summary(report)
            
            # Ask if user wants detailed report
            save_detailed = input("\nSave detailed report to file? (y/n): ").lower().strip()
            if save_detailed == 'y':
                filename = f"backup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"Detailed report saved to: {filename}")
        
        elif choice == '2':
            # Create EBS snapshots
            region = input("Enter region (e.g., us-east-1): ").strip()
            volume_ids = input("Enter volume IDs (comma-separated): ").strip().split(',')
            volume_ids = [v.strip() for v in volume_ids if v.strip()]
            
            if volume_ids:
                created = create_ebs_snapshots(volume_ids, region)
                print(f"\nCreated {len(created)} snapshots successfully!")
            else:
                print("No volume IDs provided.")
        
        elif choice == '3':
            # Copy snapshots cross-region
            source_region = input("Enter source region: ").strip()
            target_region = input("Enter target region: ").strip()
            
            # Get recent snapshots from source region
            ec2_client = boto3.client('ec2', region_name=source_region)
            snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']
            
            # Sort by start time, get most recent
            recent_snapshots = sorted(snapshots, key=lambda x: x['StartTime'], reverse=True)[:10]
            snapshot_data = [{'snapshot': s} for s in recent_snapshots]
            
            print(f"\nFound {len(recent_snapshots)} recent snapshots in {source_region}")
            max_copies = int(input("How many to copy? (max 10): ") or "5")
            
            copied = copy_snapshots_cross_region(snapshot_data, source_region, target_region, max_copies)
            print(f"\nInitiated copying of {len(copied)} snapshots to {target_region}")
        
        elif choice == '4':
            print("Old snapshot cleanup feature coming soon!")
            print("For now, use the backup report to identify old snapshots,")
            print("then manually delete them through the AWS console.")
        
        else:
            print("Invalid choice. Please select 1-4.")
    
    except Exception as e:
        print(f"Error during backup management: {e}")
        print("Please ensure you have the necessary AWS permissions:")
        print("- ec2:DescribeVolumes")
        print("- ec2:DescribeSnapshots")
        print("- ec2:CreateSnapshot")
        print("- ec2:CopySnapshot")
        print("- ec2:DescribeRegions")
        print("- rds:DescribeDBInstances")
        print("- rds:DescribeDBSnapshots")
        print("- rds:DescribeDBClusterSnapshots")

if __name__ == '__main__':
    main()