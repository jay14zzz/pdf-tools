import os
import uuid
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import fitz

# Import PDF utility functions from separate modules



# Config
app = Flask(__name__)
app.secret_key = 'your_secret_key'
# Configuration to remove trailing slashes
# app.url_map.strict_slashes = False
# need to use return redirect(url_for('index') for trailing slash

from utils.pdf_operations import (
    compress_pdf,
    analyze_pdf_content,
    validate_pdf,
    remove_pdf_pages,
    split_pdf,
    merge_pdfs,
    reorder_pages,
    extract_pdf_info,
    insert_pdf_at_position
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.secret_key = os.urandom(24)  # For session management

# Create necessary directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# Available compression quality levels
COMPRESSION_QUALITY = [
    {'id': 'pil_30', 'name': 'Low'},
    {'id': 'pil_60', 'name': 'Medium'},
    {'id': 'pil_80', 'name': 'High'},
]


# Helper Functions
def save_uploaded_file(file):
    """Saves an uploaded file and returns the filepath"""
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    return filepath, unique_filename, filename


def generate_result_filepath(original_filename, prefix=""):
    """Generate a filepath for processed results"""
    output_filename = f"{prefix}_{uuid.uuid4()}_{original_filename}"
    output_filepath = os.path.join(app.config['RESULT_FOLDER'], output_filename)
    return output_filepath, output_filename


def handle_file_upload(request, required_file_key='file'):
    """Handle file upload with validation"""
    if required_file_key not in request.files:
        return None, {'error': f'No {required_file_key} provided'}, 400

    file = request.files[required_file_key]
    if file.filename == '':
        return None, {'error': 'No selected file'}, 400

    if not file.filename.lower().endswith('.pdf'):
        return None, {'error': 'Invalid file type. Please upload a PDF file'}, 400

    filepath, unique_filename, original_filename = save_uploaded_file(file)

    # Validate PDF
    is_valid, error_msg = validate_pdf(filepath)
    if not is_valid:
        # Remove invalid file
        if os.path.exists(filepath):
            os.remove(filepath)
        return None, {'error': error_msg}, 400

    return {
        'filepath': filepath,
        'unique_filename': unique_filename,
        'original_filename': original_filename
    }, None, 200


# Routes
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

# Routes
@app.route('/compress')
def compress():
    """Render the compress page"""
    return render_template('compress.html', compression_quality=COMPRESSION_QUALITY)


@app.route('/operations')
def operations():
    """Render the operations page"""
    return render_template('operations.html')


@app.route('/delete')
def delete():
    """Render the delete page"""
    return render_template('delete.html')


@app.route('/insert')
def insert():
    """Render the insert page"""
    return render_template('insert.html')

@app.route('/merge')
def merge():
    """Render the merge page"""
    return render_template('merge.html')

@app.route('/reorder')
def reorder():
    """Render the reorder page"""
    return render_template('reorder.html')


# API Endpoints
@app.route('/api/analyze', methods=['POST'])
def analyze_pdf_api():
    """Analyze uploaded PDF and return information about it"""
    file_data, error_response, status_code = handle_file_upload(request)

    if error_response:
        return jsonify(error_response), status_code

    # Analyze the PDF
    analysis = analyze_pdf_content(file_data['filepath'])
    analysis['filename'] = file_data['unique_filename']
    analysis['original_name'] = file_data['original_filename']


    return jsonify({
        'success': True,
        'analysis': analysis
    })


@app.route('/api/compress', methods=['POST'])
def compress_pdf_api():
    """Compress a PDF file with the selected method"""
    data = request.json
    filename = data.get('filename')
    method_id = data.get('method', 'pil_60')  # Default to medium quality

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(input_path):
        return jsonify({'error': 'File not found'}), 404

    # Generate output filename
    output_filepath, output_filename = generate_result_filepath(filename, prefix="compressed")

    # Parse method and quality level from method_id
    if '_' in method_id:
        parts = method_id.split('_')
        method = parts[0]
        quality_level = parts[1]

        # Convert quality level to integer if it's numeric
        if quality_level.isdigit():
            quality_level = int(quality_level)
    else:
        method = method_id
        quality_level = None

    # Compress the PDF
    try:
        result = compress_pdf(input_path, output_filepath, method, quality_level)
        result['result_filename'] = output_filename
        result['original_filename'] = filename
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete_pages', methods=['POST'])
def delete_pdf_pages_api():
    """Delete specified pages from an uploaded PDF"""
    file_data, error_response, status_code = handle_file_upload(request)

    if error_response:
        return jsonify(error_response), status_code

    # Check for pages to remove
    pages_to_remove = request.form.get('pages_to_remove', '')
    if not pages_to_remove:
        return jsonify({'error': 'No pages specified to remove'}), 400

    # Convert pages_to_remove to a list of integers
    try:
        pages = [int(page.strip()) for page in pages_to_remove.split(',')]
    except ValueError:
        return jsonify({'error': 'Invalid page numbers'}), 400

    # Check total pages in the PDF
    reader = PdfReader(file_data['filepath'])
    total_pages = len(reader.pages)

    # Validate page numbers
    invalid_pages = [p for p in pages if p < 1 or p > total_pages]
    if invalid_pages:
        return jsonify({
            'error': f'Invalid page numbers: {invalid_pages}. PDF has {total_pages} pages.',
            'total_pages': total_pages
        }), 400

    # Generate output filename
    output_filepath, output_filename = generate_result_filepath(
        file_data['original_filename'],
        prefix="deleted_pages"
    )

    try:
        # Remove specified pages
        remove_pdf_pages(file_data['filepath'], pages, output_filepath)

        return jsonify({
            'success': True,
            'output_filename': output_filename,
            'original_filename': file_data['original_filename'],
            'pages_removed': pages,
            'total_pages': total_pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/insert_pdf', methods=['POST'])
def insert_pdf_api():
    """Insert a PDF into another PDF at a specific position"""
    # Check for both files
    base_file_data, base_error, base_status = handle_file_upload(request, 'base_file')
    if base_error:
        return jsonify(base_error), base_status

    insert_file_data, insert_error, insert_status = handle_file_upload(request, 'insert_file')
    if insert_error:
        return jsonify(insert_error), insert_status

    # Check if the position is provided
    position = request.form.get('position', '')
    if not position:
        return jsonify({'error': 'Insertion position is required'}), 400

    try:
        position = int(position) - 1  # Convert from 1-based (user) to 0-based (internal)
        if position < 0:
            return jsonify({'error': 'Position must be at least 1'}), 400
    except ValueError:
        return jsonify({'error': 'Position must be a valid integer'}), 400

    try:
        # Generate output filename
        output_filepath, output_filename = generate_result_filepath(
            base_file_data['original_filename'],
            prefix="inserted"
        )

        # Insert the PDF
        result = insert_pdf_at_position(
            base_file_data['filepath'],
            insert_file_data['filepath'],
            position,
            output_filepath
        )

        if result["success"]:
            result["output_filename"] = output_filename
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/extract-info', methods=['POST'])
def extract_info_api():
    """Extract and return detailed PDF information"""
    file_data, error_response, status_code = handle_file_upload(request)

    if error_response:
        return jsonify(error_response), status_code

    # Extract PDF information
    info = extract_pdf_info(file_data['filepath'])
    if info['success']:
        info['filename'] = file_data['unique_filename']
        info['original_name'] = file_data['original_filename']
        return jsonify({
            'success': True,
            'info': info
        })
    else:
        return jsonify({
            'success': False,
            'error': info.get('error', 'Failed to extract PDF information')
        }), 500


@app.route('/api/split', methods=['POST'])
def split_pdf_api():
    """Split a PDF into multiple PDFs"""
    data = request.json
    filename = data.get('filename')
    page_ranges = data.get('page_ranges')  # Example: [[1,3], [5,7]]

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(input_path):
        return jsonify({'error': 'File not found'}), 404

    # Create a unique output directory for splits
    output_dir = os.path.join(app.config['RESULT_FOLDER'], f"split_{uuid.uuid4().hex[:8]}")
    os.makedirs(output_dir, exist_ok=True)

    # Convert page ranges to the expected format
    formatted_ranges = None
    if page_ranges:
        formatted_ranges = [(r[0], r[1]) for r in page_ranges if len(r) == 2]

    # Perform the split operation
    result = split_pdf(input_path, output_dir, formatted_ranges)
    return jsonify(result)


@app.route('/api/merge', methods=['POST'])
def merge_pdfs_api():
    """Merge uploaded PDFs into a single file"""
    # Get files from the request
    files = request.files.getlist('files')

    if not files or len(files) < 2:
        return jsonify({'error': 'At least two PDF files are required for merging'}), 400

    # Save all files and validate
    filepaths = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            continue

        filepath, _, _ = save_uploaded_file(file)
        is_valid, _ = validate_pdf(filepath)

        if is_valid:
            filepaths.append(filepath)

    if len(filepaths) < 2:
        return jsonify({'error': 'At least two valid PDF files are required for merging'}), 400

    # Generate output filename
    output_filepath, output_filename = generate_result_filepath("merged.pdf", prefix="merged")

    # Perform the merge operation
    result = merge_pdfs(filepaths, output_filepath)

    if result['success']:
        result['output_filename'] = output_filename

    return jsonify(result)


@app.route('/api/reorder-pages', methods=['POST'])
def reorder_pages_api():
    """Reorder pages in a PDF"""
    data = request.json
    filename = data.get('filename')
    new_order = data.get('new_order', [])  # Example: [3, 2, 1, 4] to reverse pages 1-3

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(input_path):
        return jsonify({'error': 'File not found'}), 404

    # Generate output filename
    output_filepath, output_filename = generate_result_filepath(filename, prefix="reordered")

    # Perform the reordering
    result = reorder_pages(input_path, output_filepath, new_order)

    if result['success']:
        result['output_filename'] = output_filename

    return jsonify(result)


@app.route('/api/methods')
def get_methods():
    """Return available compression methods"""
    return jsonify(COMPRESSION_QUALITY)


# Download routes
@app.route('/api/download/<filename>')
def download_file(filename):
    """Download a processed PDF file"""
    return send_file(
        os.path.join(app.config['RESULT_FOLDER'], filename),
        as_attachment=True
    )


# Clean up temporary files periodically
def cleanup_old_files():
    """Remove files older than 1 hour"""
    # Implementation for periodic cleanup
    pass


if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000)
    app.run(debug=True)
    ##