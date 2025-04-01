import os
import uuid
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import fitz
import base64
from config import DevelopmentConfig, ProductionConfig

# Import PDF utility functions from separate modules

from routes.views import views_bp
from routes.pdf_api import pdf_api_bp
app = Flask(__name__)
# Register blueprints
app.register_blueprint(views_bp)
app.register_blueprint(pdf_api_bp, url_prefix='/api')



## Config
# Load the appropriate config
# app.config.from_object(ProductionConfig)
app.config.from_object(DevelopmentConfig)


# Create necessary directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)



if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000)
    app.run(debug=True)
    ###