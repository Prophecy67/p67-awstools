# P67-awstools

Welcome to P67-awstools! 🚀 

A comprehensive collection of Python tools for AWS management, security auditing, and operational tasks. This toolkit provides six powerful utilities designed to simplify common AWS activities and strengthen your cloud security posture. Whether you're managing autoscaling groups, auditing security configurations, or performing cross-account resource discovery, these tools will help streamline your AWS operations.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Tools](#tools)
  - [1. Autoscaling Group Management](#1-autoscaling-group-management-cli_scale_ec2_asg)
  - [2. IAM User Password and Access Key Management](#2-iam-user-password-and-access-key-management-aws_passwd_rotate)
  - [3. Security Group Auditor](#3-security-group-auditor-sg_auditor)
  - [4. IAM Policy Analyzer](#4-iam-policy-analyzer-iam_analyzer)
  - [5. Backup Manager](#5-backup-manager-backup_manager)
  - [6. Cross-Account Resource Finder](#6-cross-account-resource-finder-cross_account_finder)
- [License](#license)

## Quick Start

Ready to get started? Here's the fastest way to begin using P67-awstools:

1. **Install the package:**
   ```bash
   pip install p67-awstools
   ```

2. **Ensure your AWS credentials are configured:**
   ```bash
   aws configure
   ```

3. **Run your first security audit:**
   ```bash
   sg_auditor
   ```

That's it! You'll get a comprehensive security analysis of your AWS Security Groups across all regions.

## Prerequisites

- Python 3.9 or higher
- [AWS CLI configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html) with appropriate credentials
- Boto3 library (automatically installed with the package)

## Installation

Install the package using pip:

```bash
pip install p67-awstools
```

Or install from source:

```bash
git clone https://github.com/Prophecy67/p67-awstools.git
cd p67-awstools
pip install .
```

## Tools

### 1. Autoscaling Group Management (`cli_scale_ec2_asg`)

The [`cli_scale_ec2_asg`](P67_awstools/cli_scale_ec2_asg.py) tool provides functionality to manage AWS Auto Scaling Groups. It allows you to view instance uptimes and scale groups to desired sizes.

#### Usage

Run the tool from the command line:

```bash
cli_scale_ec2_asg
```

#### Features

1. **Show Instance Uptimes** (Option 1)
   - Displays the running duration of each instance in all Auto Scaling Groups
   - Helps identify long-running instances that may need attention

2. **Scale Auto Scaling Groups** (Option 2)
   - Select one or more Auto Scaling Groups to scale (enter numbers separated by commas)
   - Specify the desired capacity for the selected groups
   - Confirms the scaling operation with a success message

#### Example Usage

```text
$ cli_scale_ec2_asg
Select an action:
1. Show instance uptimes
2. Scale autoscaling group
Enter your choice (1 or 2): 1

Auto Scaling Group: my-web-servers
  Instance i-1234567890abcdef0: Running for 2 days, 3 hours, 45 minutes
  Instance i-0987654321fedcba0: Running for 1 day, 12 hours, 30 minutes
```

#### Important Notes

- Ensure your AWS credentials have the following permissions:
  - `autoscaling:DescribeAutoScalingGroups`
  - `autoscaling:UpdateAutoScalingGroup`
  - `ec2:DescribeInstances`
- The tool currently supports up to 100 Auto Scaling Groups. If you have more, modify the `MaxRecords` parameter in the [`get_autoscaling_groups`](P67_awstools/cli_scale_ec2_asg.py#L8) function.

### 2. IAM User Password and Access Key Management (`aws_passwd_rotate`)

The [`aws_passwd_rotate`](P67_awstools/password_rotate.py) tool provides a secure way to rotate IAM user passwords and access keys. This is essential for maintaining good security hygiene in your AWS environment.

#### Usage

Run the tool from the command line:

```bash
aws_passwd_rotate
```

#### What it does

1. **Password Rotation**: Securely changes your IAM user password
2. **Access Key Management**: Disables all existing access keys and creates a new one
3. **Secure Output**: Displays the new access key credentials (save them immediately!)

#### Example Usage

```text
$ aws_passwd_rotate
Enter your current password: ********
Enter your new password: ********

Password changed successfully!
All existing access keys have been disabled.
New access key created:

Access Key ID: AKIAIOSFODNN7EXAMPLE
Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

⚠️  IMPORTANT: Save these credentials securely! They will not be shown again.
```

#### Required Permissions

Your AWS credentials must have the following IAM permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:ChangePassword",
                "iam:ListAccessKeys",
                "iam:CreateAccessKey",
                "iam:UpdateAccessKey"
            ],
            "Resource": "arn:aws:iam::*:user/${aws:username}"
        }
    ]
}
```

#### Security Considerations

- **Save credentials immediately**: The new access key will only be displayed once
- **Update applications**: Remember to update any applications using the old access keys
- **Test thoroughly**: Verify that the new credentials work before discarding the old ones
- **Regular rotation**: Consider automating this process for enhanced security compliance

### 3. Security Group Auditor (`sg_auditor`)

The [`sg_auditor`](P67_awstools/sg_auditor.py) tool performs comprehensive security analysis of your AWS Security Groups across all regions, identifying potential security risks and helping ensure compliance with security best practices.

#### Usage

```bash
sg_auditor
```

#### Features

1. **Overly Permissive Rules Detection**
   - Identifies security groups with rules allowing access from 0.0.0.0/0
   - Flags both inbound and outbound overly broad permissions
   - Provides detailed port and protocol information

2. **Unused Security Groups**
   - Finds security groups not attached to any resources
   - Helps reduce clutter and potential security risks
   - Excludes default security groups from unused list

3. **Dangerous Port Analysis**
   - Detects commonly dangerous ports exposed to the internet
   - Includes SSH (22), RDP (3389), database ports, and more
   - Provides service identification for flagged ports

4. **Comprehensive Reporting**
   - Scans all AWS regions automatically
   - Generates both summary and detailed JSON reports
   - Provides actionable security recommendations

#### Example Output

```text
$ sg_auditor
AWS Security Group Auditor
==========================
Scanning all regions for security groups...
Found 45 security groups across all regions

🚨 OVERLY PERMISSIVE RULES: 3 security groups
  • web-servers-sg (sg-1234567890abcdef0) in us-east-1
    - Inbound: tcp port 80 open to 0.0.0.0/0
    - Inbound: tcp port 443 open to 0.0.0.0/0

💰 UNUSED SECURITY GROUPS: 7 groups
  • old-test-sg (sg-0987654321fedcba0) in us-west-2
  • legacy-app-sg (sg-abcdef1234567890) in eu-west-1

⚠️  DANGEROUS PORTS EXPOSED: 1 security groups
  • admin-access-sg (sg-fedcba0987654321) in us-east-1
    - SSH (port 22) exposed to internet
```

#### Required Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeRegions",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeInstances"
            ],
            "Resource": "*"
        }
    ]
}
```

### 4. IAM Policy Analyzer (`iam_analyzer`)

The [`iam_analyzer`](P67_awstools/iam_analyzer.py) tool provides comprehensive analysis of your IAM configuration, identifying security risks, unused resources, and policy compliance issues.

#### Usage

```bash
iam_analyzer
```

#### Features

1. **Unused User Detection**
   - Identifies users inactive for 90+ days
   - Checks both console and programmatic access
   - Analyzes password and access key usage patterns

2. **Unused Role Analysis**
   - Finds roles not used in the last 90 days
   - Excludes AWS service-linked roles
   - Helps reduce attack surface

3. **Overly Permissive Policy Detection**
   - Identifies policies with dangerous wildcard permissions
   - Flags broad resource access patterns
   - Analyzes custom managed policies

4. **MFA Compliance Checking**
   - Finds console users without MFA enabled
   - Critical for security compliance
   - Provides user-specific recommendations

5. **Password Policy Analysis**
   - Evaluates account password policy strength
   - Compares against security best practices
   - Provides specific improvement recommendations

6. **Root Account Usage Monitoring**
   - Detects recent root account activity (requires CloudTrail)
   - Flags potential security concerns
   - Recommends IAM user alternatives

#### Example Output

```text
$ iam_analyzer
AWS IAM Policy Analyzer
=======================
Analyzing IAM configuration...

👤 UNUSED USERS (90+ days): 5
  • old-developer (last used: 2023-08-15)
  • test-account (last used: Never)

🎭 UNUSED ROLES (90+ days): 3
  • legacy-lambda-role (last used: 2023-07-20)
  • old-ec2-role (last used: Never)

🚨 OVERLY PERMISSIVE POLICIES: 2
  • AdminAccessPolicy
    - Dangerous action: *
    - Overly broad resource: *

🔐 USERS WITHOUT MFA: 4
  • developer1
  • contractor-access

🔑 PASSWORD POLICY: 3 recommendations
  • Consider increasing minimum password length to 14+ characters
  • Require symbols in passwords
  • Consider preventing reuse of last 12+ passwords
```

#### Required Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:ListUsers",
                "iam:ListRoles",
                "iam:ListPolicies",
                "iam:GetPolicy",
                "iam:GetPolicyVersion",
                "iam:GetAccountPasswordPolicy",
                "iam:ListMFADevices",
                "iam:GetLoginProfile",
                "iam:ListAccessKeys",
                "iam:GetAccessKeyLastUsed",
                "cloudtrail:LookupEvents"
            ],
            "Resource": "*"
        }
    ]
}
```

### 5. Backup Manager (`backup_manager`)

The [`backup_manager`](P67_awstools/backup_manager.py) tool provides comprehensive backup management for EBS volumes and RDS instances, helping ensure your data protection strategy is both robust and cost-effective.

#### Usage

```bash
backup_manager
```

#### Features

1. **Backup Status Analysis**
   - Identifies EBS volumes without recent snapshots (7+ days)
   - Verifies RDS backup configuration
   - Provides comprehensive backup coverage reports

2. **Automated Snapshot Creation**
   - Creates EBS snapshots for specified volumes
   - Adds descriptive metadata and timestamps
   - Supports batch operations across multiple volumes

3. **Cross-Region Backup Copying**
   - Copies snapshots to different regions for disaster recovery
   - Supports selective copying of most recent snapshots
   - Provides progress tracking and error handling

4. **Old Snapshot Identification**
   - Finds snapshots older than specified thresholds
   - Calculates storage costs for cleanup planning
   - Helps optimize backup retention costs

5. **RDS Backup Verification**
   - Checks automated backup configuration
   - Verifies backup retention periods
   - Identifies missing deletion protection

#### Interactive Menu Options

```text
$ backup_manager
AWS Backup Manager
==================
1. Generate backup report
2. Create EBS snapshots
3. Copy snapshots to another region
4. Clean up old snapshots (interactive)

Select an option (1-4):
```

#### Example Report Output

```text
💾 VOLUMES NEEDING BACKUP (7+ days): 8
  • vol-1234567890abcdef0 in us-east-1 (last backup: 2023-10-15)
  • vol-0987654321fedcba0 in us-west-2 (last backup: Never)

🗑️  OLD SNAPSHOTS (30+ days): 23 (Est. cost: $45.60/month)
  • snap-abcdef1234567890 (45 days old, $2.50/month)
  • snap-fedcba0987654321 (67 days old, $4.20/month)

🗄️  RDS BACKUP ISSUES: 2 instances
  • production-db in us-east-1
    - Backup retention period is only 1 day (recommend 7+)
    - Deletion protection is disabled
```

#### Required Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeVolumes",
                "ec2:DescribeSnapshots",
                "ec2:CreateSnapshot",
                "ec2:CopySnapshot",
                "ec2:DescribeRegions",
                "rds:DescribeDBInstances",
                "rds:DescribeDBSnapshots",
                "rds:DescribeDBClusterSnapshots"
            ],
            "Resource": "*"
        }
    ]
}
```

### 6. Cross-Account Resource Finder (`cross_account_finder`)

The [`cross_account_finder`](P67_awstools/cross_account_finder.py) tool provides powerful multi-account resource discovery and comprehensive inventory management across your AWS organization.

#### Usage

```bash
cross_account_finder
```

#### Features

1. **Multi-Account Scanning**
   - Automatically detects available AWS profiles
   - Scans resources across multiple AWS accounts
   - Supports both single and multi-account environments

2. **Comprehensive Resource Discovery**
   - EC2 instances across all regions
   - S3 buckets (global service)
   - RDS instances and clusters
   - Lambda functions
   - Extensible architecture for additional services

3. **Advanced Search Capabilities**
   - Search resources by name or ID across accounts
   - Quick scan of common regions for faster results
   - Full inventory scan for comprehensive coverage

4. **Detailed Inventory Reporting**
   - Resources grouped by account, region, and type
   - JSON export for further analysis
   - Cost optimization insights

5. **Concurrent Processing**
   - Multi-threaded scanning for improved performance
   - Handles large-scale environments efficiently
   - Progress tracking across regions

#### Interactive Menu Options

```text
$ cross_account_finder
AWS Cross-Account Resource Finder
=================================
1. Full inventory scan
2. Search resources by name/ID
3. Quick scan (limited regions)

Select an option (1-3):
```

#### Example Output

```text
📊 RESOURCES BY TYPE:
  • EC2 Instance: 45
  • S3 Bucket: 23
  • RDS Instance: 12
  • Lambda Function: 67

🏢 RESOURCES BY ACCOUNT:
  • production: 89 resources
    - EC2 Instance: 25
    - S3 Bucket: 15
    - RDS Instance: 8
    - Lambda Function: 41
  • development: 58 resources
    - EC2 Instance: 20
    - S3 Bucket: 8
    - RDS Instance: 4
    - Lambda Function: 26

🌍 RESOURCES BY REGION:
  • us-east-1: 67 resources
  • us-west-2: 45 resources
  • eu-west-1: 35 resources
```

#### Multi-Account Setup

The tool automatically detects AWS profiles configured in your `~/.aws/credentials` file:

```text
Available AWS profiles:
  1. default
  2. production
  3. development
  4. staging

Enter profile numbers to scan (comma-separated, or 'all' for all profiles): all
```

#### Required Permissions

Each account needs the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "rds:DescribeDBInstances",
                "lambda:ListFunctions"
            ],
            "Resource": "*"
        }
    ]
}
```

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
