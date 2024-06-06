from . import db

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.String(255), unique=True, nullable=False)
    prompt_date = db.Column(db.DateTime)
    prompt_text = db.Column(db.Text, nullable=True) 
    url = db.Column(db.Text)
    download_path = db.Column(db.Text)
    enhancement_level = db.Column(db.Text)