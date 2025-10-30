#!/usr/bin/env python3

import boto3
import json
from datetime import datetime, timedelta
from collections import defaultdict

def get_all_users():
    """Get all IAM users"""
    iam_client = boto3.client('iam')
    paginator = iam_client.get_paginator('list_users')
    users = []
    
    for page in paginator.paginate():
        users.extend(page['Users'])
    
    return users

def get_all_roles():
    """Get all IAM roles"""
    iam_client = boto3.client('iam')
    paginator = iam_client.get_paginator('list_roles')
    roles = []
    
    for page in paginator.paginate():
        roles.extend(page['Roles'])
    
    return roles

def get_all_policies():
    """Get all customer managed policies"""
    iam_client = boto3.client('iam')
    paginator = iam_client.get_paginator('list_policies')
    policies = []
    
    for page in paginator.paginate(Scope='Local'):  # Only customer managed policies
        policies.extend(page['Policies'])
    
    return policies

def find_unused_users(users, days_threshold=90):
    """Find users that haven't been used recently"""
    unused_users = []
    cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days_threshold)
    
    for user in users:
        last_used = user.get('PasswordLastUsed')
        if not last_used or last_used < cutoff_date:
            # Check access key usage
            iam_client = boto3.client('iam')
            try:
                access_keys = iam_client.list_access_keys(UserName=user['UserName'])['AccessKeyMetadata']
                key_recently_used = False
                
                for key in access_keys:
                    try:
                        key_last_used = iam_client.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
                        if key_last_used.get('AccessKeyLastUsed', {}).get('LastUsedDate'):
                            if key_last_used['AccessKeyLastUsed']['LastUsedDate'] >= cutoff_date:
                                key_recently_used = True
                                break
                    except Exception:
                        continue
                
                if not key_recently_used:
                    unused_users.append({
                        'user': user,
                        'password_last_used': last_used,
                        'access_keys_count': len(access_keys)
                    })
            except Exception as e:
                print(f"Warning: Could not check access keys for user {user['UserName']}: {e}")
    
    return unused_users

def find_overly_permissive_policies():
    """Find policies with overly broad permissions"""
    iam_client = boto3.client('iam')
    dangerous_actions = [
        '*',
        '*:*',
        'iam:*',
        's3:*',
        'ec2:*',
        'rds:*',
        'lambda:*'
    ]
    
    dangerous_resources = [
        '*',
        'arn:aws:*:*:*:*'
    ]
    
    overly_permissive = []
    policies = get_all_policies()
    
    for policy in policies:
        try:
            # Get policy document
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy['Arn'],
                VersionId=policy['DefaultVersionId']
            )
            
            policy_doc = policy_version['PolicyVersion']['Document']
            issues = []
            
            # Check statements
            statements = policy_doc.get('Statement', [])
            if not isinstance(statements, list):
                statements = [statements]
            
            for stmt in statements:
                if stmt.get('Effect') == 'Allow':
                    # Check actions
                    actions = stmt.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    for action in actions:
                        if action in dangerous_actions:
                            issues.append(f"Dangerous action: {action}")
                    
                    # Check resources
                    resources = stmt.get('Resource', [])
                    if isinstance(resources, str):
                        resources = [resources]
                    
                    for resource in resources:
                        if resource in dangerous_resources:
                            issues.append(f"Overly broad resource: {resource}")
            
            if issues:
                overly_permissive.append({
                    'policy': policy,
                    'issues': issues
                })
        
        except Exception as e:
            print(f"Warning: Could not analyze policy {policy['PolicyName']}: {e}")
    
    return overly_permissive

def find_unused_roles(roles, days_threshold=90):
    """Find roles that haven't been used recently"""
    unused_roles = []
    cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days_threshold)
    
    for role in roles:
        # Skip service-linked roles
        if role['Path'].startswith('/aws-service-role/'):
            continue
        
        last_used = role.get('RoleLastUsed', {}).get('LastUsedDate')
        if not last_used or last_used < cutoff_date:
            unused_roles.append({
                'role': role,
                'last_used': last_used
            })
    
    return unused_roles

def check_password_policy():
    """Check account password policy"""
    iam_client = boto3.client('iam')
    
    try:
        policy = iam_client.get_account_password_policy()['PasswordPolicy']
        
        recommendations = []
        
        # Check minimum length
        if policy.get('MinimumPasswordLength', 0) < 14:
            recommendations.append("Consider increasing minimum password length to 14+ characters")
        
        # Check complexity requirements
        if not policy.get('RequireUppercaseCharacters'):
            recommendations.append("Require uppercase characters in passwords")
        
        if not policy.get('RequireLowercaseCharacters'):
            recommendations.append("Require lowercase characters in passwords")
        
        if not policy.get('RequireNumbers'):
            recommendations.append("Require numbers in passwords")
        
        if not policy.get('RequireSymbols'):
            recommendations.append("Require symbols in passwords")
        
        # Check password age
        if policy.get('MaxPasswordAge', 0) == 0 or policy.get('MaxPasswordAge', 0) > 90:
            recommendations.append("Consider setting maximum password age to 90 days or less")
        
        # Check reuse prevention
        if policy.get('PasswordReusePrevention', 0) < 12:
            recommendations.append("Consider preventing reuse of last 12+ passwords")
        
        return {
            'policy': policy,
            'recommendations': recommendations
        }
    
    except iam_client.exceptions.NoSuchEntityException:
        return {
            'policy': None,
            'recommendations': ["No password policy is configured - consider creating one"]
        }

def find_users_with_console_access_but_no_mfa():
    """Find users with console access but no MFA enabled"""
    iam_client = boto3.client('iam')
    users = get_all_users()
    no_mfa_users = []
    
    for user in users:
        # Check if user has console access (login profile)
        try:
            iam_client.get_login_profile(UserName=user['UserName'])
            has_console_access = True
        except iam_client.exceptions.NoSuchEntityException:
            has_console_access = False
        
        if has_console_access:
            # Check MFA devices
            mfa_devices = iam_client.list_mfa_devices(UserName=user['UserName'])['MFADevices']
            if not mfa_devices:
                no_mfa_users.append(user)
    
    return no_mfa_users

def check_root_account_usage():
    """Check for root account usage (requires CloudTrail)"""
    try:
        cloudtrail_client = boto3.client('cloudtrail')
        
        # Look for root account usage in the last 30 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        events = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {
                    'AttributeKey': 'Username',
                    'AttributeValue': 'root'
                }
            ],
            StartTime=start_time,
            EndTime=end_time
        )
        
        root_events = events.get('Events', [])
        return {
            'events_found': len(root_events),
            'recent_events': root_events[:5]  # Show first 5 events
        }
    
    except Exception as e:
        return {
            'error': f"Could not check root account usage: {e}",
            'note': "CloudTrail access required for root account usage analysis"
        }

def generate_iam_report():
    """Generate comprehensive IAM analysis report"""
    print("Analyzing IAM configuration...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'findings': {}
    }
    
    # Get basic counts
    users = get_all_users()
    roles = get_all_roles()
    policies = get_all_policies()
    
    report['summary'] = {
        'total_users': len(users),
        'total_roles': len(roles),
        'total_custom_policies': len(policies)
    }
    
    # Find unused users
    print("Checking for unused users...")
    unused_users = find_unused_users(users)
    report['findings']['unused_users'] = {
        'count': len(unused_users),
        'users': unused_users
    }
    
    # Find unused roles
    print("Checking for unused roles...")
    unused_roles = find_unused_roles(roles)
    report['findings']['unused_roles'] = {
        'count': len(unused_roles),
        'roles': unused_roles
    }
    
    # Find overly permissive policies
    print("Analyzing policy permissions...")
    overly_permissive = find_overly_permissive_policies()
    report['findings']['overly_permissive_policies'] = {
        'count': len(overly_permissive),
        'policies': overly_permissive
    }
    
    # Check password policy
    print("Checking password policy...")
    password_policy = check_password_policy()
    report['findings']['password_policy'] = password_policy
    
    # Find users without MFA
    print("Checking MFA configuration...")
    no_mfa_users = find_users_with_console_access_but_no_mfa()
    report['findings']['users_without_mfa'] = {
        'count': len(no_mfa_users),
        'users': [{'username': u['UserName'], 'created': u['CreateDate']} for u in no_mfa_users]
    }
    
    # Check root account usage
    print("Checking root account usage...")
    root_usage = check_root_account_usage()
    report['findings']['root_account_usage'] = root_usage
    
    return report

def print_iam_summary(report):
    """Print human-readable IAM analysis summary"""
    print("=" * 60)
    print("AWS IAM SECURITY ANALYSIS REPORT")
    print("=" * 60)
    print(f"Generated: {report['timestamp']}")
    print(f"Total Users: {report['summary']['total_users']}")
    print(f"Total Roles: {report['summary']['total_roles']}")
    print(f"Total Custom Policies: {report['summary']['total_custom_policies']}")
    print()
    
    # Unused users
    unused_users_count = report['findings']['unused_users']['count']
    print(f"👤 UNUSED USERS (90+ days): {unused_users_count}")
    if unused_users_count > 0:
        for item in report['findings']['unused_users']['users'][:5]:
            user = item['user']
            last_used = item['password_last_used']
            last_used_str = last_used.strftime('%Y-%m-%d') if last_used else 'Never'
            print(f"  • {user['UserName']} (last used: {last_used_str})")
        if unused_users_count > 5:
            print(f"    ... and {unused_users_count - 5} more")
    print()
    
    # Unused roles
    unused_roles_count = report['findings']['unused_roles']['count']
    print(f"🎭 UNUSED ROLES (90+ days): {unused_roles_count}")
    if unused_roles_count > 0:
        for item in report['findings']['unused_roles']['roles'][:5]:
            role = item['role']
            last_used = item['last_used']
            last_used_str = last_used.strftime('%Y-%m-%d') if last_used else 'Never'
            print(f"  • {role['RoleName']} (last used: {last_used_str})")
        if unused_roles_count > 5:
            print(f"    ... and {unused_roles_count - 5} more")
    print()
    
    # Overly permissive policies
    permissive_count = report['findings']['overly_permissive_policies']['count']
    print(f"🚨 OVERLY PERMISSIVE POLICIES: {permissive_count}")
    if permissive_count > 0:
        for item in report['findings']['overly_permissive_policies']['policies'][:3]:
            policy = item['policy']
            print(f"  • {policy['PolicyName']}")
            for issue in item['issues'][:2]:  # Show first 2 issues
                print(f"    - {issue}")
        if permissive_count > 3:
            print(f"    ... and {permissive_count - 3} more")
    print()
    
    # Users without MFA
    no_mfa_count = report['findings']['users_without_mfa']['count']
    print(f"🔐 USERS WITHOUT MFA: {no_mfa_count}")
    if no_mfa_count > 0:
        for user in report['findings']['users_without_mfa']['users'][:5]:
            print(f"  • {user['username']}")
        if no_mfa_count > 5:
            print(f"    ... and {no_mfa_count - 5} more")
    print()
    
    # Password policy
    password_recs = report['findings']['password_policy']['recommendations']
    print(f"🔑 PASSWORD POLICY: {len(password_recs)} recommendations")
    for rec in password_recs[:3]:
        print(f"  • {rec}")
    if len(password_recs) > 3:
        print(f"    ... and {len(password_recs) - 3} more")
    print()
    
    # Root account usage
    root_usage = report['findings']['root_account_usage']
    if 'events_found' in root_usage:
        events_count = root_usage['events_found']
        print(f"👑 ROOT ACCOUNT USAGE (30 days): {events_count} events")
        if events_count > 0:
            print("  ⚠️  Root account usage detected - consider using IAM users instead")
    else:
        print("👑 ROOT ACCOUNT USAGE: Could not analyze (CloudTrail required)")
    print()
    
    # Summary
    total_issues = (unused_users_count + unused_roles_count + permissive_count + 
                   no_mfa_count + len(password_recs))
    
    if total_issues == 0:
        print("✅ No major IAM issues found! Your IAM configuration looks good.")
    else:
        print(f"📊 SUMMARY: {total_issues} total IAM issues found")
        print("   Consider reviewing and addressing these issues to improve security.")

def main():
    """Main function to run IAM analysis"""
    print("AWS IAM Policy Analyzer")
    print("=" * 25)
    
    try:
        # Generate report
        report = generate_iam_report()
        
        # Print summary
        print_iam_summary(report)
        
        # Ask if user wants detailed report
        print()
        save_detailed = input("Save detailed report to file? (y/n): ").lower().strip()
        if save_detailed == 'y':
            filename = f"iam_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Detailed report saved to: {filename}")
        
    except Exception as e:
        print(f"Error during IAM analysis: {e}")
        print("Please ensure you have the necessary AWS permissions:")
        print("- iam:ListUsers")
        print("- iam:ListRoles")
        print("- iam:ListPolicies")
        print("- iam:GetPolicy")
        print("- iam:GetPolicyVersion")
        print("- iam:GetAccountPasswordPolicy")
        print("- iam:ListMFADevices")
        print("- iam:GetLoginProfile")
        print("- iam:ListAccessKeys")
        print("- iam:GetAccessKeyLastUsed")
        print("- cloudtrail:LookupEvents (optional, for root usage analysis)")

if __name__ == '__main__':
    main()