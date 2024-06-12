import sys
import os
import shutil
from pathlib import Path


# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask_app import create_app
from flask_app.models import Image

# Create an instance of the Flask application
app = create_app()

def save_files(filtered_images, keywords, storage_folder):
    merged_keyword_name = keywords.replace(' ', '_')
    new_folder_name = 'midjourney_' + merged_keyword_name
    new_folder_path = os.path.join(storage_folder, new_folder_name)
    os.makedirs(new_folder_path, exist_ok=True)

    for image in filtered_images:
        stored_file = image.download_path
        new_file_name = Path(stored_file).stem + '-' + merged_keyword_name + Path(stored_file).suffix
        new_file_path = os.path.join(new_folder_path, new_file_name)
        shutil.copy(stored_file, new_file_path)
    print(f"Images saved to {new_folder_path}")

def query_keywords(keywords):
    keywords_list = keywords.split(' ')
    query = Image.query

    # Apply a filter for each keyword
    for keyword in keywords_list:
        query = query.filter(Image.prompt_text.ilike(f'%{keyword}%'))

    filtered_images = query.all()
    return filtered_images

if __name__ == '__main__':
    keywords = sys.argv[1]
    storage_folder = sys.argv[2]

    with app.app_context():
        filtered_images = query_keywords(keywords)
        save_files(filtered_images, keywords, storage_folder)