from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Basic configuration
    app.config['SECRET_KEY'] = 'dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://postgres:{os.getenv('DB_PASSWORD')}@midjourney-db.crusowko6eee.us-east-2.rds.amazonaws.com/midjourney-db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    return app
