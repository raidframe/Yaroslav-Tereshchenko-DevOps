import boto3
import uuid

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

instance = new_instances[0]

print("Waiting for instance to start...")

instance.wait_until_running()
instance.reload()

print("Instance Running.")


s3 = boto3.resource('s3')

bucket_name = 'yt-week4-' + str(uuid.uuid4())

bucket = s3.create_bucket(
    Bucket=bucket_name
)

website_configuration = {
    'ErrorDocument': {'Key': 'error.html'},
    'IndexDocument': {'Suffix': 'index.html'}
}

bucket_website = s3.BucketWebsite(bucket_name)

bucket_website.put(
    WebsiteConfiguration=website_configuration
)

print("Bucket created:")
print(bucket_name)

print("Upload an index.html file to test it works!")