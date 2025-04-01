from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for

views_bp = Blueprint('views', __name__)

# Routes
@views_bp.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


# Available compression quality levels
COMPRESSION_QUALITY = [
    {'id': 'pil_30', 'name': 'Low'},
    {'id': 'pil_60', 'name': 'Medium'},
    {'id': 'pil_80', 'name': 'High'},
]
# Routes
@views_bp.route('/compress')
def compress():
    """Render the compress page"""
    return render_template('compress.html', compression_quality=COMPRESSION_QUALITY)


@views_bp.route('/operations')
def operations():
    """Render the operations page"""
    return render_template('operations.html')


@views_bp.route('/delete')
def delete():
    """Render the delete page"""
    return render_template('delete.html')


@views_bp.route('/insert')
def insert():
    """Render the insert page"""
    return render_template('insert.html')

@views_bp.route('/merge')
def merge():
    """Render the merge page"""
    return render_template('merge.html')

@views_bp.route('/reorder')
def reorder():
    """Render the reorder page"""
    return render_template('reorder.html')

@views_bp.route('/sign')
def sign():
    """Render the sign page"""
    return render_template('sign.html')

@views_bp.route('/password')
def password():
    """Render the PDF password page"""
    return render_template('password.html')

