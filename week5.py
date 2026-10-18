import boto3
import subprocess
import json
import uuid

# Download image using curl
print("Downloading image...")

result = subprocess.run(
    [
        "curl",
        "-L",
        "-f",
        "-o",
        "logo.jpg",
        "http://devops.setudemo.net/logo.jpg"
    ],
    check=True
)

print("Image downloaded successfully!")

# Connect to S3
s3 = boto3.resource("s3", region_name="us-east-1")

# Generate unique bucket name
random_id = uuid.uuid4().hex[:6]
bucket_name = f"{random_id}-ytereshchenko"

print("Creating bucket:", bucket_name)

s3.create_bucket(Bucket=bucket_name)

print("Bucket created successfully!")

# Disable block public access
s3.meta.client.delete_public_access_block(
    Bucket=bucket_name
)

# Create bucket policy
bucket_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": f"arn:aws:s3:::{bucket_name}/*"
        }
    ]
}

# Apply bucket policy
s3.Bucket(bucket_name).Policy().put(
    Policy=json.dumps(bucket_policy)
)

print("Public access configured!")

# Upload image
print("Uploading image...")

s3.Object(bucket_name, "logo.jpg").put(
    Body=open("logo.jpg", "rb"),
    ContentType="image/jpeg"
)

print("Image uploaded successfully!")

# Upload HTML file
print("Uploading index.html...")

s3.Object(bucket_name, "index.html").put(
    Body=open("index.html", "rb"),
    ContentType="text/html"
)

print("HTML uploaded successfully!")

# Enable static website hosting
website_configuration = {
    "IndexDocument": {
        "Suffix": "index.html"
    }
}

bucket_website = s3.BucketWebsite(bucket_name)

bucket_website.put(
    WebsiteConfiguration=website_configuration
)

print("Static website hosting enabled!")

# Generate website URL
website_url = (
    f"http://{bucket_name}."
    "s3-website-us-east-1.amazonaws.com"
)

print("\nWebsite URL:")
print(website_url)