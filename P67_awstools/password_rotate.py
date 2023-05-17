import boto3

def main():
# create an IAM client
    iam_client = boto3.client('iam')

    # prompt the user to enter their current password
    current_password = input('Enter your current password: ')

    # prompt the user to enter their new password
    new_password = input('Enter your new password: ')

    # change the user's password
    iam_client.change_password(
        OldPassword=current_password,
        NewPassword=new_password
    )

    # disable all access keys for the user
    response = iam_client.list_access_keys()
    for access_key in response['AccessKeyMetadata']:
        iam_client.delete_access_key(
            UserName=access_key['UserName'],
            AccessKeyId=access_key['AccessKeyId'],
            # Status='Inactive'
        )

    # create a new access key for the user
    new_access_key = iam_client.create_access_key(UserName=access_key['UserName'])['AccessKey']

    # print the new access key information for the user to save
    print('New Access Key:')
    print(f'Access Key ID: {new_access_key["AccessKeyId"]}')
    print(f'Secret Access Key: {new_access_key["SecretAccessKey"]}')

if __name__ == '__main__':
    main() 

