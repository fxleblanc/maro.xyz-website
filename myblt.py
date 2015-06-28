import os
import hashlib
import binascii
import string, random

from flask import Flask, request, send_from_directory, jsonify
from werkzeug import secure_filename, exceptions
from database import db_session, init_db
from models import Upload

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['API_URL'] = 'http://a.myb.lt/'


def hash_exists(hash):
    return Upload.query.filter(Upload.hash == hash).count() != 0

def short_url_exists(url):
    if not url:
        return True
    return Upload.query.filter(Upload.short_url == url).count() != 0

def get_random_short_url():
    """Generates a random string of 7 ascii letters and digits
    Can provide in the order or 10^12 unique strings
    """
    pool = string.ascii_letters + string.digits
    return ''.join(random.choice(pool) for _ in range(7))

def get_new_short_url():
    """Generate random urls until a new one is generated"""
    url = None
    while short_url_exists(url):
        url = get_random_short_url()
    return url

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if not file:
        return BadRequest

    # Get sha1 of uploaded file
    m = hashlib.sha1()
    m.update(file.read())
    file_hash_bin = m.digest()

    if not hash_exists(file_hash_bin):
        # Save new file to uploads folder
        filename = secure_filename(file.filename)
        file_hash_str = str(binascii.hexlify(file_hash_bin).decode('utf8'))
        abs_file = os.path.join(app.config['UPLOAD_FOLDER'], file_hash_str)

        file.stream.seek(0)
        file.save(abs_file)

        # Generate a short url
        short_id = get_new_short_url()
        short_url = app.config['API_URL'] + short_id

        # TODO add real mime type
        # Add upload in DB
        upload = Upload(file_hash_bin, short_id, 'mime')
        db_session.add(upload)
        db_session.commit()
    else:
        # Get old (identical) file's short_url from the hash
        og_upload = Upload.query.filter(Upload.hash == file_hash_bin).first()
        short_url =  app.config['API_URL'] + og_upload.short_url

    return jsonify(short_url=short_url)

@app.route('/<short_url>', methods=['GET'])
def get_upload(short_url):
    upload = Upload.query.filter(Upload.short_url == short_url).first()
    hash_str = str(binascii.hexlify(upload.hash).decode('utf8'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], hash_str)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

if __name__ == "__main__":
    init_db()
    app.run()
