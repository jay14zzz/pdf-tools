import os
import uuid
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import fitz
import base64


# Import PDF utility functions from separate modules

from routes.views import views_bp
from routes.pdf_api import pdf_api_bp
app = Flask(__name__)
# Register blueprints
app.register_blueprint(views_bp)
app.register_blueprint(pdf_api_bp, url_prefix='/api')

## Config

app.secret_key = 'your_secret_key'
# Configuration to remove trailing slashes
# app.url_map.strict_slashes = False
# need to use return redirect(url_for('index') for trailing slash


app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.secret_key = os.urandom(24)  # For session management

# Create necessary directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)



if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000)
    app.run(debug=True)
    ###