# P67-awstools

Helper tools for common AWS activities. Currently still in heavy development. For now, it provides two functionalities:

## 1. Autoscaling Group Management (`cli_scale_ec2_asg`)

This Python script provides functionalities to manage autoscaling groups in AWS. It utilizes the Boto3 library to interact with the AWS Autoscaling and EC2 services.

### Prerequisites

- Python 3.x
- Boto3 library

### `cli_scale_ec2_asg` usage

1. Run the script and select an action:
   - Enter `1` to show instance uptimes for all autoscaling groups.
   - Enter `2` to scale an autoscaling group to a desired size.

2. If you choose to show instance uptimes, the script will display the running duration of each instance in each autoscaling group.

3. If you choose to scale an autoscaling group, you will be prompted to enter the numbers of the autoscaling groups you want to scale, separated by commas. Then, enter the desired size for the autoscaling group.

4. The script will update the specified autoscaling groups with the desired size, and display a confirmation message.

**Note:**

- Ensure that the AWS credentials used by the script have appropriate permissions to describe and update autoscaling groups.
- The script currently supports a maximum of 100 autoscaling groups due to the default value used in the `describe_auto_scaling_groups` function. Modify the `MaxRecords` parameter in the `get_autoscaling_groups` function if you have more than 100 autoscaling groups.

## 2. IAM User Password and Access Key Management (`aws_passwd_rotate`)

This Python script provides a way to change the password of an IAM user in AWS and manage their access keys. It utilizes the Boto3 library to interact with the AWS IAM service.

### `aws_passwd_rotate` Usage

1. Run the script and enter the following information:
   - Enter your current password: Enter the current password of the IAM user.
   - Enter your new password: Enter the desired new password for the IAM user.

2. The script will change the IAM user's password to the new password provided.

3. All existing access keys for the IAM user will be disabled.

4. A new access key will be created for the IAM user.

5. The script will print the new access key information, including the Access Key ID and Secret Access Key. Make sure to save this information securely as it will not be accessible again.

**Note:**

- Ensure that the AWS credentials used by the script have appropriate permissions to manage IAM users, change passwords, and create/delete access keys.
- The IAM user specified in the script must have sufficient permissions to change their own password and access key.
- Review and modify the script as necessary to meet your specific requirements and security practices.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
