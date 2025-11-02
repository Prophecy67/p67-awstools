# P67-awstools

A collection of helpful Python tools for common AWS activities. This project is currently in active development and provides two main functionalities to simplify AWS management tasks.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Tools](#tools)
  - [1. Autoscaling Group Management](#1-autoscaling-group-management-cli_scale_ec2_asg)
  - [2. IAM User Password and Access Key Management](#2-iam-user-password-and-access-key-management-aws_passwd_rotate)
- [License](#license)

## Prerequisites

- Python 3.9 or higher
- AWS CLI configured with appropriate credentials
- Boto3 library

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

```bash
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
- The tool currently supports up to 100 Auto Scaling Groups. If you have more, modify the `MaxRecords` parameter in the [`get_autoscaling_groups`](P67_awstools/cli_scale_ec2_asg.py) function.

### 2. IAM User Password and Access Key Management (`aws_passwd_rotate`)

The [`aws_passwd_rotate`](P67_awstools/password_rotate.py) tool provides a secure way to rotate IAM user passwords and access keys. This is essential for maintaining good security hygiene in your AWS environment.

#### Usage

Run the tool from the command line:

```bash
aws_passwd_rotate
```

#### What it does

1. **Password Rotation**: Changes your IAM user password
2. **Access Key Management**: Disables all existing access keys and creates a new one
3. **Secure Output**: Displays the new access key credentials (save them immediately!)

#### Example Usage

```bash
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
- **Regular rotation**: Consider automating this process for enhanced security

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
