import boto3
import subprocess
import json
import uuid
import time
from datetime import datetime, timedelta, timezone

# Handle unexpected errors during AWS automation.
try:
    # Steps 1-3: Create EC2 and configure Apache.
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    new_instances = ec2.create_instances(
        ImageId='ami-0fef201115eefe936',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.nano',
        KeyName='ytstudentkey',
        SecurityGroupIds=['sg-028db8e4bd4181b8d'],
        # User Data installs Apache and displays EC2 metadata.
        UserData="""#!/bin/bash
        yum update -y
        yum install httpd -y
        systemctl enable httpd
        systemctl start httpd

        TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
        INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
        PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
        AMI_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/ami-id)
        AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)

        echo "<html><body>" > /var/www/html/index.html
        echo "<h1>DevOps Assignment 1</h1>" >> /var/www/html/index.html
        echo "<p>Instance ID: $INSTANCE_ID</p>" >> /var/www/html/index.html
        echo "<p>Public IP: $PUBLIC_IP</p>" >> /var/www/html/index.html
        echo "<p>AMI ID: $AMI_ID</p>" >> /var/www/html/index.html
        echo "<p>Availability Zone: $AZ</p>" >> /var/www/html/index.html
        echo "<p>Web server created using Python and Boto3.</p>" >> /var/www/html/index.html
        echo "</body></html>" >> /var/www/html/index.html
        """,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': 'Web server'}]
            }
        ]
    )

    instance = new_instances[0]
    print('Instance created:', instance.id)
    print('Waiting for instance to start...')
    instance.wait_until_running()
    instance.reload()
    ip_address = instance.public_ip_address
    if not ip_address:
        raise RuntimeError('Instance does not have a public IP address.')

    ec2_url = 'http://' + ip_address
    print('EC2 website:', ec2_url)
    print('Availability Zone:', instance.placement['AvailabilityZone'])

    # Step 4: Create S3 static website.
    print('Downloading image...')
    subprocess.run([
        'curl', '-L', '-f', '-o', 'logo.jpg',
        'http://devops.setudemo.net/logo.jpg'
    ], check=True)

    s3 = boto3.resource('s3', region_name='us-east-1')
    random_id = uuid.uuid4().hex[:6]
    bucket_name = f'{random_id}-ytereshchenko'
    s3.create_bucket(Bucket=bucket_name)
    print('Bucket created:', bucket_name)

    # Allow public access to website files using an S3 bucket policy.
    s3.meta.client.delete_public_access_block(Bucket=bucket_name)
    bucket_policy = {
        'Version': '2012-10-17',
        'Statement': [{
            'Sid': 'PublicReadGetObject',
            'Effect': 'Allow',
            'Principal': '*',
            'Action': ['s3:GetObject'],
            'Resource': f'arn:aws:s3:::{bucket_name}/*'
        }]
    }
    s3.Bucket(bucket_name).Policy().put(Policy=json.dumps(bucket_policy))

    with open('logo.jpg', 'rb') as image_file:
        s3.Object(bucket_name, 'logo.jpg').put(
            Body=image_file, ContentType='image/jpeg'
        )

    with open('index.html', 'w') as html_file:
        html_file.write('<html><body>\n')
        html_file.write('<h1>DevOps Assignment 1 - S3 Website</h1>\n')
        html_file.write('<img src="logo.jpg" alt="DevOps logo">\n')
        html_file.write('</body></html>\n')

    with open('index.html', 'rb') as html_file:
        s3.Object(bucket_name, 'index.html').put(
            Body=html_file, ContentType='text/html'
        )

    website_configuration = {
        'IndexDocument': {'Suffix': 'index.html'}
    }
    bucket_website = s3.BucketWebsite(bucket_name)
    bucket_website.put(WebsiteConfiguration=website_configuration)
    s3_url = f'http://{bucket_name}.s3-website-us-east-1.amazonaws.com'
    print('S3 website:', s3_url)

    # Step 5: Save both website addresses.
    with open('ytereshchenko-websites.txt', 'w') as urls_file:
        urls_file.write('EC2 website: ' + ec2_url + '\n')
        urls_file.write('S3 website: ' + s3_url + '\n')
    print('Website URLs saved.')

    # Step 6: Copy and run monitoring.sh through SCP/SSH.
    print('Waiting for the EC2 startup script...')
    time.sleep(60)

    print('Copying monitoring.sh...')
    subprocess.run([
        'scp', '-o', 'StrictHostKeyChecking=no',
        '-i', 'ytstudentkey.pem', 'monitoring.sh',
        'ec2-user@' + ip_address + ':.'
    ], check=True)

    print('Setting permissions and running monitoring.sh...')
    subprocess.run([
        'ssh', '-o', 'StrictHostKeyChecking=no',
        '-i', 'ytstudentkey.pem', 'ec2-user@' + ip_address,
        'chmod 700 monitoring.sh && ./monitoring.sh'
    ], check=True)

    # Step 7: Check Apache before creating an AMI.
    subprocess.run([
        'ssh', '-o', 'StrictHostKeyChecking=no',
        '-i', 'ytstudentkey.pem', 'ec2-user@' + ip_address,
        'systemctl is-active --quiet httpd'
    ], check=True)

    image_name = 'YT-' + datetime.now().strftime('%Y-%m-%d-%f')
    image = instance.create_image(Name=image_name)
    print('AMI creation started:', image.id)
    print('AMI name:', image_name)

    # Additional functionality: CloudWatch CPU metrics.
    print('Checking EC2 CPU utilisation with CloudWatch...')
    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=30)

    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=300,
        Statistics=['Average']
    )

    if response['Datapoints']:
        for datapoint in sorted(response['Datapoints'], key=lambda point: point['Timestamp']):
            print('CPU utilisation:', round(datapoint['Average'], 2), '%')
    else:
        print('No CPU data available yet. CloudWatch may need more time.')

    instance.reload()
    print('Instance state:', instance.state['Name'])
    print('Instance availability zone:', instance.placement['AvailabilityZone'])
    print('Assignment steps completed. Remember to clean up AWS resources.')

except Exception as error:
    print('Error:', error)
    print('Check your AWS console: resources may already have been created.')
