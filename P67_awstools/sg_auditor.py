#!/usr/bin/env python3

import boto3
import json
from datetime import datetime
from collections import defaultdict

def get_all_security_groups():
    """Get all security groups across all regions"""
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    all_security_groups = []
    for region in regions:
        try:
            regional_client = boto3.client('ec2', region_name=region)
            response = regional_client.describe_security_groups()
            for sg in response['SecurityGroups']:
                sg['Region'] = region
                all_security_groups.append(sg)
        except Exception as e:
            print(f"Warning: Could not access region {region}: {e}")
    
    return all_security_groups

def find_overly_permissive_rules(security_groups):
    """Find security groups with overly permissive rules (0.0.0.0/0)"""
    permissive_groups = []
    
    for sg in security_groups:
        issues = []
        
        # Check inbound rules
        for rule in sg.get('IpPermissions', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_range.get('CidrIp') == '0.0.0.0/0':
                    port_info = get_port_info(rule)
                    issues.append({
                        'type': 'inbound',
                        'protocol': rule.get('IpProtocol', 'unknown'),
                        'port': port_info,
                        'description': ip_range.get('Description', 'No description')
                    })
        
        # Check outbound rules
        for rule in sg.get('IpPermissionsEgress', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_range.get('CidrIp') == '0.0.0.0/0':
                    port_info = get_port_info(rule)
                    issues.append({
                        'type': 'outbound',
                        'protocol': rule.get('IpProtocol', 'unknown'),
                        'port': port_info,
                        'description': ip_range.get('Description', 'No description')
                    })
        
        if issues:
            permissive_groups.append({
                'security_group': sg,
                'issues': issues
            })
    
    return permissive_groups

def get_port_info(rule):
    """Extract port information from a security group rule"""
    if rule.get('IpProtocol') == '-1':
        return 'All ports'
    elif rule.get('FromPort') == rule.get('ToPort'):
        return str(rule.get('FromPort', 'unknown'))
    else:
        return f"{rule.get('FromPort', 'unknown')}-{rule.get('ToPort', 'unknown')}"

def find_unused_security_groups(security_groups):
    """Find security groups that are not attached to any resources"""
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    # Get all network interfaces across all regions
    used_sg_ids = set()
    
    for region in regions:
        try:
            regional_client = boto3.client('ec2', region_name=region)
            
            # Check network interfaces
            response = regional_client.describe_network_interfaces()
            for eni in response['NetworkInterfaces']:
                for sg in eni.get('Groups', []):
                    used_sg_ids.add(f"{region}:{sg['GroupId']}")
            
            # Check instances
            response = regional_client.describe_instances()
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    for sg in instance.get('SecurityGroups', []):
                        used_sg_ids.add(f"{region}:{sg['GroupId']}")
            
        except Exception as e:
            print(f"Warning: Could not check resources in region {region}: {e}")
    
    # Find unused security groups
    unused_groups = []
    for sg in security_groups:
        sg_key = f"{sg['Region']}:{sg['GroupId']}"
        if sg_key not in used_sg_ids and sg['GroupName'] != 'default':
            unused_groups.append(sg)
    
    return unused_groups

def check_dangerous_ports(security_groups):
    """Check for commonly dangerous ports that are open to the internet"""
    dangerous_ports = {
        22: 'SSH',
        23: 'Telnet',
        3389: 'RDP',
        1433: 'SQL Server',
        3306: 'MySQL',
        5432: 'PostgreSQL',
        6379: 'Redis',
        27017: 'MongoDB',
        9200: 'Elasticsearch'
    }
    
    dangerous_groups = []
    
    for sg in security_groups:
        issues = []
        
        for rule in sg.get('IpPermissions', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_range.get('CidrIp') == '0.0.0.0/0':
                    from_port = rule.get('FromPort')
                    to_port = rule.get('ToPort')
                    
                    if from_port and to_port:
                        for port, service in dangerous_ports.items():
                            if from_port <= port <= to_port:
                                issues.append({
                                    'port': port,
                                    'service': service,
                                    'protocol': rule.get('IpProtocol', 'unknown')
                                })
        
        if issues:
            dangerous_groups.append({
                'security_group': sg,
                'dangerous_ports': issues
            })
    
    return dangerous_groups

def generate_security_report(security_groups):
    """Generate a comprehensive security report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_security_groups': len(security_groups),
        'regions_scanned': len(set(sg['Region'] for sg in security_groups)),
        'findings': {}
    }
    
    # Find overly permissive rules
    permissive = find_overly_permissive_rules(security_groups)
    report['findings']['overly_permissive'] = {
        'count': len(permissive),
        'groups': permissive
    }
    
    # Find unused security groups
    unused = find_unused_security_groups(security_groups)
    report['findings']['unused'] = {
        'count': len(unused),
        'groups': [{'id': sg['GroupId'], 'name': sg['GroupName'], 'region': sg['Region']} for sg in unused]
    }
    
    # Find dangerous ports
    dangerous = check_dangerous_ports(security_groups)
    report['findings']['dangerous_ports'] = {
        'count': len(dangerous),
        'groups': dangerous
    }
    
    return report

def print_summary_report(report):
    """Print a human-readable summary of the security report"""
    print("=" * 60)
    print("AWS SECURITY GROUP AUDIT REPORT")
    print("=" * 60)
    print(f"Generated: {report['timestamp']}")
    print(f"Total Security Groups Scanned: {report['total_security_groups']}")
    print(f"Regions Scanned: {report['regions_scanned']}")
    print()
    
    # Overly permissive rules
    permissive_count = report['findings']['overly_permissive']['count']
    print(f"🚨 OVERLY PERMISSIVE RULES: {permissive_count} security groups")
    if permissive_count > 0:
        for item in report['findings']['overly_permissive']['groups'][:5]:  # Show first 5
            sg = item['security_group']
            print(f"  • {sg['GroupName']} ({sg['GroupId']}) in {sg['Region']}")
            for issue in item['issues']:
                print(f"    - {issue['type'].title()}: {issue['protocol']} port {issue['port']} open to 0.0.0.0/0")
        if permissive_count > 5:
            print(f"    ... and {permissive_count - 5} more")
    print()
    
    # Unused security groups
    unused_count = report['findings']['unused']['count']
    print(f"💰 UNUSED SECURITY GROUPS: {unused_count} groups")
    if unused_count > 0:
        for sg in report['findings']['unused']['groups'][:10]:  # Show first 10
            print(f"  • {sg['name']} ({sg['id']}) in {sg['region']}")
        if unused_count > 10:
            print(f"    ... and {unused_count - 10} more")
    print()
    
    # Dangerous ports
    dangerous_count = report['findings']['dangerous_ports']['count']
    print(f"⚠️  DANGEROUS PORTS EXPOSED: {dangerous_count} security groups")
    if dangerous_count > 0:
        for item in report['findings']['dangerous_ports']['groups'][:5]:  # Show first 5
            sg = item['security_group']
            print(f"  • {sg['GroupName']} ({sg['GroupId']}) in {sg['Region']}")
            for port_info in item['dangerous_ports']:
                print(f"    - {port_info['service']} (port {port_info['port']}) exposed to internet")
        if dangerous_count > 5:
            print(f"    ... and {dangerous_count - 5} more")
    print()
    
    # Summary
    total_issues = permissive_count + unused_count + dangerous_count
    if total_issues == 0:
        print("✅ No security issues found! Your security groups look good.")
    else:
        print(f"📊 SUMMARY: {total_issues} total security issues found")
        print("   Consider reviewing and fixing these issues to improve your AWS security posture.")

def main():
    """Main function to run the security group auditor"""
    print("AWS Security Group Auditor")
    print("=" * 30)
    print("Scanning all regions for security groups...")
    
    try:
        # Get all security groups
        security_groups = get_all_security_groups()
        print(f"Found {len(security_groups)} security groups across all regions")
        print()
        
        # Generate report
        report = generate_security_report(security_groups)
        
        # Print summary
        print_summary_report(report)
        
        # Ask if user wants detailed report
        print()
        save_detailed = input("Save detailed report to file? (y/n): ").lower().strip()
        if save_detailed == 'y':
            filename = f"sg_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Detailed report saved to: {filename}")
        
    except Exception as e:
        print(f"Error during security group audit: {e}")
        print("Please ensure you have the necessary AWS permissions:")
        print("- ec2:DescribeSecurityGroups")
        print("- ec2:DescribeRegions")
        print("- ec2:DescribeNetworkInterfaces")
        print("- ec2:DescribeInstances")

if __name__ == '__main__':
    main()