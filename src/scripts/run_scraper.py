from flask_app import create_app
from scripts.imageCollector import ImageCollector

def run_scraper(limit):
    app = create_app()
    with app.app_context():
        scraper = ImageCollector(limit)
        scraper.launch_archive_page()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python run_scraper.py <limit>")
        sys.exit(1)
    
    try:
        limit = int(sys.argv[1])
    except ValueError:
        print("The limit must be an integer.")
        sys.exit(1)

    run_scraper(limit)
