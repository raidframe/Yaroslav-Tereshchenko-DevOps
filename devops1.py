import boto3

ec2 = boto3.resource('ec2')
s3 = boto3.resource('s3')

for instance in ec2.instances.all():
    print(instance.id, instance.public_ip_address)

for bucket in s3.buckets.all():
    print(bucket.name)