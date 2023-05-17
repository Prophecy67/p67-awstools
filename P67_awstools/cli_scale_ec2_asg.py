#!/usr/bin/env python3

import boto3
from datetime import datetime

client = boto3.client('autoscaling')
ec2_client = boto3.client('ec2')

def get_autoscaling_groups():
    response = client.describe_auto_scaling_groups(MaxRecords=100)
    autoscalinggroups = response['AutoScalingGroups']
    return autoscalinggroups

def get_instance_ids(autoscalinggroup):
    instance_ids = []
    for instance in autoscalinggroup['Instances']:
        instance_ids.append(instance['InstanceId'])
    return instance_ids

def get_instance_uptime(instance_id):
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    launch_time_str = response['Reservations'][0]['Instances'][0]['LaunchTime']
    launch_time = datetime.strptime(str(launch_time_str), '%Y-%m-%d %H:%M:%S+00:00')
    uptime = datetime.utcnow() - launch_time
    return uptime

def show_instance_uptimes(autoscalinggroups):
    for group in autoscalinggroups:
        print(f"Instances in autoscaling group {group['AutoScalingGroupName']}:")
        instance_ids = get_instance_ids(group)
        for instance_id in instance_ids:
            uptime = get_instance_uptime(instance_id)
            print(f"Instance {instance_id} has been running for {uptime}")

def scale_ec2_asg(autoscalinggroups, requested_size):
    for group in autoscalinggroups:
        asg_name = group['AutoScalingGroupName']
        client.update_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            MinSize=requested_size,
            MaxSize=requested_size,
            DesiredCapacity=requested_size
        )
        print(f"Scaled auto scaling group {asg_name} size to {requested_size} instances")

def main():
    autoscalinggroups = get_autoscaling_groups()
    print("Select an action:")
    print("1. Show instance uptimes")
    print("2. Scale autoscaling group")
    choice = input("Enter your choice (1/2): ")
    if choice == '1':
        show_instance_uptimes(autoscalinggroups)
    elif choice == '2':
        autoscalinggroups_selected = []
        for i, group in enumerate(autoscalinggroups):
            print(f"{i+1}. {group['AutoScalingGroupName']}")
        choices = input("Enter the numbers of the autoscaling groups to scale (separated by commas): ")
        choices = [int(choice.strip()) for choice in choices.split(',')]
        autoscalinggroups_selected = [autoscalinggroups[i-1] for i in choices]
        size = input("Enter the desired size: ")
        scale_ec2_asg(autoscalinggroups_selected, int(size))
    else:
        print("Invalid choice")

if __name__ == '__main__':
    main()

