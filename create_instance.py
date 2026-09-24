import boto3

ec2 = boto3.resource('ec2')

new_instances = ec2.create_instances(
    ImageId='ami-0fef201115eefe936',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',

    KeyName='ytstudentkey',

    SecurityGroupIds=[
        'sg-028db8e4bd4181b8d'
    ],

    UserData="""#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd
""",

    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Web server'
                }
            ]
        }
    ]
)

print("Instance created:")
print(new_instances[0].id)