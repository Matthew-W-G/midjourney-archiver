import sys
import os
import boto3
from pathlib import Path
from botocore.exceptions import NoCredentialsError
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from flask_app import db
from flask_app import create_app
from flask_app.models import Image
app = create_app()

BUCKET_NAME = 'conformist-midjourney-bucket'
BUCKET_REGION = 'us-east-2'

# Load environment variables from .env file
load_dotenv()

# Get AWS credentials from environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_default_region = os.getenv('AWS_DEFAULT_REGION')

# Create an S3 client using the credentials from environment variables
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_default_region
)

def upload_to_s3(image):
    local_filename = image.download_path
    try:
        s3_filename = Path(local_filename).name
        s3_client.upload_file(local_filename, BUCKET_NAME, s3_filename)
        image.s3_url = f'https://{BUCKET_NAME}.s3.{BUCKET_REGION}.amazonaws.com/{quote_plus(s3_filename)}'
        db.session.commit()
        print(f'The URL of the image will be: {image.s3_url}')
    except FileNotFoundError:
        print(f"The file {local_filename} was not found")
    except NoCredentialsError:
        print("Credentials not available")

def s3Migration():
    all_images = db.session.query(Image).all()
    for img in all_images:
        print(img)
        upload_to_s3(img)

if __name__ == '__main__':
    with app.app_context():
        s3Migration()