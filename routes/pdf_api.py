import os
import uuid
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import fitz
import base64
from flask import Blueprint, request, jsonify, send_file, current_app
pdf_api_bp = Blueprint('pdf_api', __name__)


# Import the PDF operations module
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

# Import the PDF signing module
from utils.pdf_signing import (
    process_signature_image,
    get_pdf_info,
    sign_pdf_document
)


def generate_result_filepath(original_filename, prefix=""):
    """Generate a filepath for processed results"""
    output_filename = f"{prefix}_{uuid.uuid4()}_{original_filename}"
    output_filepath = os.path.join(current_app.config['RESULT_FOLDER'], output_filename)
    return output_filepath, output_filename

# Helper Functions
def save_uploaded_file(file):
    """Saves an uploaded file and returns the filepath"""
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    return filepath, unique_filename, filename


def handle_file_upload(request, required_file_key='file', allowed_extensions=None):
    """
    Handle file upload with validation

    Args:
        request: Flask request object
        required_file_key: Form field name for the file
        allowed_extensions: List of allowed file extensions (e.g., ['.pdf', '.png'])
                          If None, defaults to ['.pdf']

    Returns:
        tuple: (file_data, error_response, status_code)
    """
    # Set default allowed extensions if none provided
    if allowed_extensions is None:
        allowed_extensions = ['.pdf']

    # Convert to lowercase for case-insensitive comparison
    allowed_extensions = [ext.lower() for ext in allowed_extensions]

    if required_file_key not in request.files:
        return None, {'error': f'No {required_file_key} provided'}, 400

    file = request.files[required_file_key]

    if file.filename == '':
        return None, {'error': 'No selected file'}, 400

    # Check file extension
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in allowed_extensions:
        allowed_ext_str = ', '.join(allowed_extensions)
        return None, {'error': f'Invalid file type. Allowed types: {allowed_ext_str}'}, 400

    filepath, unique_filename, original_filename = save_uploaded_file(file)

    return {
        'filepath': filepath,
        'unique_filename': unique_filename,
        'original_filename': original_filename
    }, None, 200


###################################################################################################

# API Endpoints
@pdf_api_bp.route('/analyze', methods=['POST'])
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


@pdf_api_bp.route('/compress', methods=['POST'])
def compress_pdf_api():
    """Compress a PDF file with the selected method"""
    data = request.json
    filename = data.get('filename')
    method_id = data.get('method', 'pil_60')  # Default to medium quality

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
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


@pdf_api_bp.route('/delete_pages', methods=['POST'])
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


@pdf_api_bp.route('/insert_pdf', methods=['POST'])
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


def serve_pdf_content(filename):
    """
    Internal function to serve PDF content securely
    Returns file content or None if file not found
    """
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    try:
        with open(full_path, 'rb') as file:
            return file.read()
    except FileNotFoundError:
        return None


@pdf_api_bp.route('/extract-info', methods=['POST'])
def extract_info_api():
    """
    Extract and return detailed PDF information
    Optional parameter 'include_pdf_content' to retrieve PDF file content
    """

    # Debug print to understand incoming request
    # print(f"Request Content Type: {request.content_type}")
    # print(f"Request Files: {request.files}")

    # Check if PDF content should be included
    # include_pdf_content = (
    #     request.args.get('include_pdf_content') or
    #     request.form.get('include_pdf_content') or
    #     request.json.get('include_pdf_content') if request.json else False
    # )

    include_pdf_content = request.args.get('include_pdf_content') or \
                          request.form.get('include_pdf_content') or \
                          (request.json.get('include_pdf_content') if request.is_json else False)

    # Ensure file is present in different request types
    if not request.files and not request.form.get('file'):
        return jsonify({
            'success': False,
            'error': 'No file uploaded',
            'details': {
                'content_type': request.content_type,
                'method': request.method
            }
        }), 400

    file_data, error_response, status_code = handle_file_upload(request)

    if error_response:
        return jsonify(error_response), status_code

    # Extract PDF information
    info = extract_pdf_info(file_data['filepath'])
    if info['success']:
        info['filename'] = file_data['unique_filename']
        info['original_name'] = file_data['original_filename']

        # Add PDF content only if explicitly requested
        if include_pdf_content:
            pdf_content = serve_pdf_content(file_data['unique_filename'])
            if pdf_content:
                info['pdf_base64'] = base64.b64encode(pdf_content).decode('utf-8')

        return jsonify({
            'success': True,
            'info': info
        })
    else:
        return jsonify({
            'success': False,
            'error': info.get('error', 'Failed to extract PDF information')
        }), 500


@pdf_api_bp.route('/split', methods=['POST'])
def split_pdf_api():
    """Split a PDF into multiple PDFs"""
    data = request.json
    filename = data.get('filename')
    page_ranges = data.get('page_ranges')  # Example: [[1,3], [5,7]]

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(input_path):
        return jsonify({'error': 'File not found'}), 404

    # Create a unique output directory for splits
    output_dir = os.path.join(current_app.config['RESULT_FOLDER'], f"split_{uuid.uuid4().hex[:8]}")
    os.makedirs(output_dir, exist_ok=True)

    # Convert page ranges to the expected format
    formatted_ranges = None
    if page_ranges:
        formatted_ranges = [(r[0], r[1]) for r in page_ranges if len(r) == 2]

    # Perform the split operation
    result = split_pdf(input_path, output_dir, formatted_ranges)
    return jsonify(result)


@pdf_api_bp.route('/merge', methods=['POST'])
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


@pdf_api_bp.route('/reorder-pages', methods=['POST'])
def reorder_pages_api():
    """Reorder pages in a PDF"""
    data = request.json
    filename = data.get('filename')
    new_order = data.get('new_order', [])  # Example: [3, 2, 1, 4] to reverse pages 1-3

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(input_path):
        return jsonify({'error': 'File not found'}), 404

    # Generate output filename
    output_filepath, output_filename = generate_result_filepath(filename, prefix="reordered")

    # Perform the reordering
    result = reorder_pages(input_path, output_filepath, new_order)

    if result['success']:
        result['output_filename'] = output_filename

    return jsonify(result)

COMPRESSION_QUALITY = [
    {'id': 'pil_30', 'name': 'Low'},
    {'id': 'pil_60', 'name': 'Medium'},
    {'id': 'pil_80', 'name': 'High'},
]
@pdf_api_bp.route('/methods')
def get_methods():
    """Return available compression methods"""
    return jsonify(COMPRESSION_QUALITY)


# Routes needed for PDF signing with PDF.js frontend
@pdf_api_bp.route('/process-signature', methods=['POST'])
def process_signature_api():
    """Process a signature image for use in PDF signing"""
    # Use enhanced file upload handler with image extensions
    file_data, error_response, status_code = handle_file_upload(
        request,
        required_file_key='signature',
        allowed_extensions=['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    )

    if error_response:
        return jsonify(error_response), status_code

    # Process the signature image
    with open(file_data['filepath'], 'rb') as f:
        signature_data = f.read()

    # from pdf_signing import process_signature_image
    success, processed_data, base64_data = process_signature_image(signature_data)
    if not success:
        return jsonify(processed_data), 400

    # Save the processed signature
    processed_sig_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f'sig_{file_data["unique_filename"]}')
    with open(processed_sig_path, 'wb') as f:
        f.write(processed_data)

    return jsonify({
        'success': True,
        'signature_image': f'data:image/png;base64,{base64_data}',
        'signature_filename': f'sig_{file_data["unique_filename"]}',
        'message': 'Signature processed successfully'
    })


@pdf_api_bp.route('/sign-pdf', methods=['POST'])
def sign_pdf_api():
    """Sign a PDF with a processed signature"""
    data = request.json

    # Get filenames from request
    pdf_filename = data.get('pdf_filename')
    signature_filename = data.get('signature_filename')

    if not pdf_filename or not signature_filename:
        return jsonify({'error': 'Missing filename parameters'}), 400

    # Get file paths
    pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_filename)
    sig_path = os.path.join(current_app.config['UPLOAD_FOLDER'], signature_filename)

    if not os.path.exists(pdf_path) or not os.path.exists(sig_path):
        return jsonify({'error': 'PDF or signature file not found'}), 404

    # Generate output filename
    output_filepath, output_filename = generate_result_filepath(pdf_filename, prefix="signed")

    # Get placement coordinates
    coords = {
        'x': float(data.get('x', 0)),
        'y': float(data.get('y', 0)),
        'width': float(data.get('width', 150)),
        'height': float(data.get('height', 80)),
        'page': int(data.get('page', 0))
    }

    # Sign the PDF
    # from pdf_signing import sign_pdf_document
    success, result = sign_pdf_document(
        pdf_path,
        sig_path,
        output_filepath,
        coords,
        page_num=coords['page']
    )

    if not success:
        return jsonify(result), 500

    return jsonify({
        'success': True,
        'output_filename': output_filename,
        **result,
        # 'download_url': f'/api/download/{output_filename}'
    })


# # commented & modified extract_info_api to serve pdf optionally
# # Add a route to serve the original PDF for PDF.js to render
# @pdf_api_bp.route('/serve-pdf/<filename>')
# def serve_pdf(filename):
#     """Serve PDF for browser rendering"""
#     return send_file(
#         os.path.join(current_app.config['UPLOAD_FOLDER'], filename),
#         mimetype='application/pdf'
#     )


# Download routes
@pdf_api_bp.route('/download/<filename>')
def download_file(filename):
    """Download a processed PDF file"""
    return send_file(
        os.path.join(current_app.config['RESULT_FOLDER'], filename),
        as_attachment=True
    )


# Clean up temporary files periodically
def cleanup_old_files():
    """Remove files older than 1 hour"""
    # Implementation for periodic cleanup
    pass
