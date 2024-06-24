import sys
import os
import boto3
import requests
from pathlib import Path
from botocore.exceptions import NoCredentialsError, ClientError
from urllib.parse import quote_plus
from dotenv import load_dotenv
from flask_app import db, create_app
from flask_app.models import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = create_app()

# Get AWS credentials from environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_default_region = os.getenv('AWS_DEFAULT_REGION')

# S3 bucket details
BUCKET_NAME = 'conformist-midjourney-bucket'
BUCKET_REGION = 'us-east-2'

# Download folder from environment variable
DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER')

# Create an S3 client using the credentials from environment variables
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_default_region
)

def download_image(image_url, save_path):
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        logger.info(f"Image downloaded and saved to: {save_path}")
        return save_path
    except requests.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logger.error(f"An error occurred: {err}")
    return None

def upload_to_s3(image):
    local_filename = image.download_path
    if not local_filename:
        logger.warning(f"Image {image.id} has no download path, attempting to download from URL.")
        local_filename = download_image(image.url, Path(DOWNLOAD_FOLDER) / Path(image.url).name)
        if not local_filename:
            logger.error(f"Failed to download image {image.id} from URL.")
            return

    try:
        s3_filename = Path(local_filename).name  # Use filename instead of stem to keep the extension
        s3_client.upload_file(local_filename, BUCKET_NAME, s3_filename, ExtraArgs={'ACL': 'public-read'})
        image.s3_url = f'https://{BUCKET_NAME}.s3.{BUCKET_REGION}.amazonaws.com/{quote_plus(s3_filename)}'
        db.session.commit()
        logger.info(f'The URL of the image will be: {image.s3_url}')
    except FileNotFoundError:
        logger.error(f"The file {local_filename} was not found")
    except NoCredentialsError:
        logger.error("Credentials not available")
    except ClientError as e:
        logger.error(f"Failed to upload {local_filename} to S3: {e}")

def s3Migration():
    all_images = db.session.query(Image).filter(Image.id >= 730).all()
    for img in all_images:
        logger.info(f'Processing Image ID: {img.id}')
        upload_to_s3(img)

if __name__ == '__main__':
    with app.app_context():
        s3Migration()
