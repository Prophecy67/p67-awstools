#!/usr/bin/env python3

import boto3
import json
from datetime import datetime
from collections import defaultdict
import concurrent.futures
from threading import Lock

# Thread-safe printing
print_lock = Lock()

def safe_print(message):
    """Thread-safe print function"""
    with print_lock:
        print(message)

def get_account_id():
    """Get current AWS account ID"""
    try:
        sts_client = boto3.client('sts')
        return sts_client.get_caller_identity()['Account']
    except Exception as e:
        safe_print(f"Warning: Could not get account ID: {e}")
        return "unknown"

def get_all_regions():
    """Get all available AWS regions"""
    try:
        ec2_client = boto3.client('ec2')
        return [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    except Exception as e:
        safe_print(f"Warning: Could not get regions: {e}")
        return ['us-east-1', 'us-west-2', 'eu-west-1']  # Fallback to common regions

def scan_ec2_instances(region, account_profiles=None):
    """Scan EC2 instances in a region across multiple accounts"""
    instances = []
    
    # If no profiles specified, use default credentials
    if not account_profiles:
        account_profiles = [{'name': 'default', 'profile': None}]
    
    for account in account_profiles:
        try:
            if account['profile']:
                session = boto3.Session(profile_name=account['profile'])
                ec2_client = session.client('ec2', region_name=region)
            else:
                ec2_client = boto3.client('ec2', region_name=region)
            
            response = ec2_client.describe_instances()
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'account': account['name'],
                        'region': region,
                        'resource_type': 'EC2 Instance',
                        'resource_id': instance['InstanceId'],
                        'name': get_resource_name(instance.get('Tags', [])),
                        'state': instance['State']['Name'],
                        'instance_type': instance['InstanceType'],
                        'launch_time': instance.get('LaunchTime'),
                        'vpc_id': instance.get('VpcId'),
                        'subnet_id': instance.get('SubnetId')
                    })
        
        except Exception as e:
            safe_print(f"Warning: Could not scan EC2 in {region} for account {account['name']}: {e}")
    
    return instances

def scan_s3_buckets(account_profiles=None):
    """Scan S3 buckets across multiple accounts"""
    buckets = []
    
    if not account_profiles:
        account_profiles = [{'name': 'default', 'profile': None}]
    
    for account in account_profiles:
        try:
            if account['profile']:
                session = boto3.Session(profile_name=account['profile'])
                s3_client = session.client('s3')
            else:
                s3_client = boto3.client('s3')
            
            response = s3_client.list_buckets()
            
            for bucket in response['Buckets']:
                # Get bucket region
                try:
                    location = s3_client.get_bucket_location(Bucket=bucket['Name'])
                    region = location['LocationConstraint'] or 'us-east-1'
                except Exception:
                    region = 'unknown'
                
                buckets.append({
                    'account': account['name'],
                    'region': region,
                    'resource_type': 'S3 Bucket',
                    'resource_id': bucket['Name'],
                    'name': bucket['Name'],
                    'creation_date': bucket['CreationDate']
                })
        
        except Exception as e:
            safe_print(f"Warning: Could not scan S3 for account {account['name']}: {e}")
    
    return buckets

def scan_rds_instances(region, account_profiles=None):
    """Scan RDS instances in a region across multiple accounts"""
    instances = []
    
    if not account_profiles:
        account_profiles = [{'name': 'default', 'profile': None}]
    
    for account in account_profiles:
        try:
            if account['profile']:
                session = boto3.Session(profile_name=account['profile'])
                rds_client = session.client('rds', region_name=region)
            else:
                rds_client = boto3.client('rds', region_name=region)
            
            response = rds_client.describe_db_instances()
            
            for instance in response['DBInstances']:
                instances.append({
                    'account': account['name'],
                    'region': region,
                    'resource_type': 'RDS Instance',
                    'resource_id': instance['DBInstanceIdentifier'],
                    'name': instance['DBInstanceIdentifier'],
                    'engine': instance['Engine'],
                    'instance_class': instance['DBInstanceClass'],
                    'status': instance['DBInstanceStatus'],
                    'creation_time': instance.get('InstanceCreateTime')
                })
        
        except Exception as e:
            safe_print(f"Warning: Could not scan RDS in {region} for account {account['name']}: {e}")
    
    return instances

def scan_lambda_functions(region, account_profiles=None):
    """Scan Lambda functions in a region across multiple accounts"""
    functions = []
    
    if not account_profiles:
        account_profiles = [{'name': 'default', 'profile': None}]
    
    for account in account_profiles:
        try:
            if account['profile']:
                session = boto3.Session(profile_name=account['profile'])
                lambda_client = session.client('lambda', region_name=region)
            else:
                lambda_client = boto3.client('lambda', region_name=region)
            
            response = lambda_client.list_functions()
            
            for function in response['Functions']:
                functions.append({
                    'account': account['name'],
                    'region': region,
                    'resource_type': 'Lambda Function',
                    'resource_id': function['FunctionName'],
                    'name': function['FunctionName'],
                    'runtime': function['Runtime'],
                    'last_modified': function['LastModified']
                })
        
        except Exception as e:
            safe_print(f"Warning: Could not scan Lambda in {region} for account {account['name']}: {e}")
    
    return functions

def get_resource_name(tags):
    """Extract name from resource tags"""
    for tag in tags:
        if tag['Key'].lower() == 'name':
            return tag['Value']
    return 'N/A'

def search_resources_by_name(all_resources, search_term):
    """Search resources by name or ID"""
    search_term = search_term.lower()
    matching_resources = []
    
    for resource in all_resources:
        if (search_term in resource.get('name', '').lower() or 
            search_term in resource.get('resource_id', '').lower()):
            matching_resources.append(resource)
    
    return matching_resources

def generate_inventory_report(all_resources):
    """Generate comprehensive inventory report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_resources': len(all_resources),
        'summary': {},
        'by_account': defaultdict(lambda: defaultdict(int)),
        'by_region': defaultdict(lambda: defaultdict(int)),
        'by_type': defaultdict(int)
    }
    
    # Analyze resources
    for resource in all_resources:
        account = resource['account']
        region = resource['region']
        resource_type = resource['resource_type']
        
        report['by_account'][account][resource_type] += 1
        report['by_region'][region][resource_type] += 1
        report['by_type'][resource_type] += 1
    
    # Convert defaultdicts to regular dicts for JSON serialization
    report['by_account'] = dict(report['by_account'])
    report['by_region'] = dict(report['by_region'])
    report['by_type'] = dict(report['by_type'])
    
    return report

def scan_region_resources(region, account_profiles, resource_types):
    """Scan all specified resource types in a region"""
    safe_print(f"Scanning {region}...")
    region_resources = []
    
    if 'ec2' in resource_types:
        region_resources.extend(scan_ec2_instances(region, account_profiles))
    
    if 'rds' in resource_types:
        region_resources.extend(scan_rds_instances(region, account_profiles))
    
    if 'lambda' in resource_types:
        region_resources.extend(scan_lambda_functions(region, account_profiles))
    
    return region_resources

def print_inventory_summary(report):
    """Print human-readable inventory summary"""
    print("=" * 60)
    print("AWS CROSS-ACCOUNT RESOURCE INVENTORY")
    print("=" * 60)
    print(f"Generated: {report['timestamp']}")
    print(f"Total Resources Found: {report['total_resources']}")
    print()
    
    # By resource type
    print("📊 RESOURCES BY TYPE:")
    for resource_type, count in sorted(report['by_type'].items()):
        print(f"  • {resource_type}: {count}")
    print()
    
    # By account
    print("🏢 RESOURCES BY ACCOUNT:")
    for account, types in report['by_account'].items():
        total = sum(types.values())
        print(f"  • {account}: {total} resources")
        for resource_type, count in sorted(types.items()):
            print(f"    - {resource_type}: {count}")
    print()
    
    # By region
    print("🌍 RESOURCES BY REGION:")
    region_totals = {region: sum(types.values()) for region, types in report['by_region'].items()}
    for region, total in sorted(region_totals.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {region}: {total} resources")
        types = report['by_region'][region]
        for resource_type, count in sorted(types.items()):
            print(f"    - {resource_type}: {count}")
    
    if len(region_totals) > 10:
        print(f"    ... and {len(region_totals) - 10} more regions")

def load_account_profiles():
    """Load account profiles from configuration"""
    # This is a simple implementation - in practice, you might load from a config file
    profiles = []
    
    # Try to get available profiles
    try:
        session = boto3.Session()
        available_profiles = session.available_profiles
        
        if len(available_profiles) > 1:
            print("Available AWS profiles:")
            for i, profile in enumerate(available_profiles):
                print(f"  {i+1}. {profile}")
            
            selection = input("\nEnter profile numbers to scan (comma-separated, or 'all' for all profiles): ").strip()
            
            if selection.lower() == 'all':
                for profile in available_profiles:
                    profiles.append({'name': profile, 'profile': profile})
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    for i in indices:
                        if 0 <= i < len(available_profiles):
                            profile = available_profiles[i]
                            profiles.append({'name': profile, 'profile': profile})
                except ValueError:
                    print("Invalid selection, using default profile only")
                    profiles = [{'name': 'default', 'profile': None}]
        else:
            profiles = [{'name': 'default', 'profile': None}]
    
    except Exception as e:
        safe_print(f"Warning: Could not load profiles: {e}")
        profiles = [{'name': 'default', 'profile': None}]
    
    return profiles

def main():
    """Main function for cross-account resource finder"""
    print("AWS Cross-Account Resource Finder")
    print("=" * 35)
    print("1. Full inventory scan")
    print("2. Search resources by name/ID")
    print("3. Quick scan (limited regions)")
    
    choice = input("\nSelect an option (1-3): ").strip()
    
    try:
        # Load account profiles
        account_profiles = load_account_profiles()
        safe_print(f"Scanning {len(account_profiles)} account(s)")
        
        if choice == '1':
            # Full inventory scan
            print("\nSelect resource types to scan:")
            print("1. EC2 instances")
            print("2. S3 buckets")
            print("3. RDS instances")
            print("4. Lambda functions")
            print("5. All of the above")
            
            type_choice = input("Enter choice (1-5): ").strip()
            
            resource_types = []
            if type_choice in ['1', '5']:
                resource_types.append('ec2')
            if type_choice in ['2', '5']:
                resource_types.append('s3')
            if type_choice in ['3', '5']:
                resource_types.append('rds')
            if type_choice in ['4', '5']:
                resource_types.append('lambda')
            
            if not resource_types:
                print("No resource types selected.")
                return
            
            # Get regions to scan
            all_regions = get_all_regions()
            print(f"\nFound {len(all_regions)} regions. Scanning all regions...")
            
            all_resources = []
            
            # Scan S3 buckets (global service)
            if 's3' in resource_types:
                safe_print("Scanning S3 buckets...")
                all_resources.extend(scan_s3_buckets(account_profiles))
            
            # Scan regional services
            regional_types = [t for t in resource_types if t != 's3']
            if regional_types:
                # Use threading for faster scanning
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_region = {
                        executor.submit(scan_region_resources, region, account_profiles, regional_types): region
                        for region in all_regions
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_region):
                        region = future_to_region[future]
                        try:
                            region_resources = future.result()
                            all_resources.extend(region_resources)
                        except Exception as e:
                            safe_print(f"Error scanning {region}: {e}")
            
            # Generate and display report
            report = generate_inventory_report(all_resources)
            print_inventory_summary(report)
            
            # Save detailed report
            save_detailed = input("\nSave detailed inventory to file? (y/n): ").lower().strip()
            if save_detailed == 'y':
                filename = f"resource_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump({
                        'report': report,
                        'resources': all_resources
                    }, f, indent=2, default=str)
                print(f"Detailed inventory saved to: {filename}")
        
        elif choice == '2':
            # Search resources
            search_term = input("Enter search term (name or ID): ").strip()
            if not search_term:
                print("No search term provided.")
                return
            
            print("Performing quick scan to search resources...")
            
            # Quick scan of common regions
            common_regions = ['us-east-1', 'us-west-2', 'eu-west-1']
            all_resources = []
            
            # Scan S3
            all_resources.extend(scan_s3_buckets(account_profiles))
            
            # Scan common regions
            for region in common_regions:
                safe_print(f"Scanning {region}...")
                all_resources.extend(scan_region_resources(region, account_profiles, ['ec2', 'rds', 'lambda']))
            
            # Search for matching resources
            matching = search_resources_by_name(all_resources, search_term)
            
            print(f"\n🔍 SEARCH RESULTS for '{search_term}':")
            print(f"Found {len(matching)} matching resources:")
            
            for resource in matching:
                print(f"  • {resource['resource_type']}: {resource['resource_id']}")
                print(f"    Name: {resource.get('name', 'N/A')}")
                print(f"    Account: {resource['account']}, Region: {resource['region']}")
                print()
        
        elif choice == '3':
            # Quick scan
            common_regions = ['us-east-1', 'us-west-2', 'eu-west-1']
            print(f"Performing quick scan of {len(common_regions)} common regions...")
            
            all_resources = []
            
            # Scan S3
            all_resources.extend(scan_s3_buckets(account_profiles))
            
            # Scan common regions
            for region in common_regions:
                all_resources.extend(scan_region_resources(region, account_profiles, ['ec2', 'rds', 'lambda']))
            
            # Generate and display report
            report = generate_inventory_report(all_resources)
            print_inventory_summary(report)
        
        else:
            print("Invalid choice. Please select 1-3.")
    
    except Exception as e:
        print(f"Error during resource scanning: {e}")
        print("Please ensure you have the necessary AWS permissions for all accounts:")
        print("- ec2:DescribeInstances")
        print("- ec2:DescribeRegions")
        print("- s3:ListAllMyBuckets")
        print("- s3:GetBucketLocation")
        print("- rds:DescribeDBInstances")
        print("- lambda:ListFunctions")

if __name__ == '__main__':
    main()