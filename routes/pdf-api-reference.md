
# PDF API Reference Documentation

## Overview

This document provides detailed information about the file handling and PDF operations in the Flask application. The application is structured with separate routes for page views and API operations, with PDF operations having a `/api` prefix.

## Core File Handling Functions

### `handle_file_upload`

A utility function for handling file uploads with validation.

```python
handle_file_upload(request, required_file_key='file', allowed_extensions=None)
```

#### Parameters:
- `request`: The Flask request object
- `required_file_key` (optional): Form field name for the file (defaults to 'file')
- `allowed_extensions` (optional): List of allowed file extensions (defaults to ['.pdf'])

#### Returns:
A tuple containing:
- `file_data`: Dictionary with filepath, unique_filename, and original_filename (if successful)
- `error_response`: Error message dictionary (if failed)
- `status_code`: HTTP status code

#### Example Usage:

```python
# Basic usage with default parameters (only PDF files)
file_data, error_response, status_code = handle_file_upload(request)
if error_response:
    return jsonify(error_response), status_code

# Process the file
process_pdf(file_data['filepath'])
```

```python
# With custom file key and allowed extensions
file_data, error_response, status_code = handle_file_upload(
    request, 
    required_file_key='signature_image',
    allowed_extensions=['.png', '.jpg', '.jpeg']
)
if error_response:
    return jsonify(error_response), status_code

# Process the image
process_image(file_data['filepath'])
```

## PDF Operation Functions

### `remove_pdf_pages`

Function that removes specified pages from a PDF file.

```python
remove_pdf_pages(input_path, pages_to_remove, output_path)
```

#### Parameters:
- `input_path`: Path to the input PDF file
- `pages_to_remove`: List of page numbers to remove (1-based indexing)
- `output_path`: Path to save the modified PDF

#### Returns:
A dictionary containing the result of the operation:
```python
{
    'success': True,
    'pages_removed': [1, 3, 5],
    'total_pages': 10,
    'new_page_count': 7
}
```

Or in case of error:
```python
{
    'success': False,
    'error': "Error message"
}
```

#### Example Implementation:

```python
def remove_pdf_pages(input_path, pages_to_remove, output_path):
    """
    Remove specified pages from a PDF file.

    Args:
        input_path (str): Path to the input PDF file
        pages_to_remove (list): List of page numbers to remove (1-based)
        output_path (str): Path to save the modified PDF

    Returns:
        dict: Result of the operation
    """
    try:
        # Validate input
        if not pages_to_remove:
            return {
                'success': False,
                'error': "No pages specified to remove"
            }

        # Make sure input file exists
        if not os.path.exists(input_path):
            return {
                'success': False,
                'error': "Input file does not exist"
            }

        # Open the PDF
        with open(input_path, 'rb') as file:
            reader = PdfReader(file)
            writer = PdfWriter()

            # Get total pages
            total_pages = len(reader.pages)

            # Check if any page is out of range
            for page in pages_to_remove:
                if page < 1 or page > total_pages:
                    return {
                        'success': False,
                        'error': f"Page {page} is out of range. PDF has {total_pages} pages."
                    }

            # Convert from 1-based to 0-based page numbering
            pages_to_remove_zero_based = [p - 1 for p in pages_to_remove]

            # Add all pages except those to be removed
            for i in range(total_pages):
                if i not in pages_to_remove_zero_based:
                    writer.add_page(reader.pages[i])

            # Write the output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

        return {
            'success': True,
            'pages_removed': pages_to_remove,
            'total_pages': total_pages,
            'new_page_count': total_pages - len(pages_to_remove)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to remove pages: {str(e)}"
        }
```

## API Routes

### `/api/extract-info`

**Key API for PDF upload with information extraction.** This endpoint saves the PDF file and returns detailed information about it. Use this endpoint when you need to extract PDF information before the final submission for operations.

**Endpoint:** `POST /api/extract-info`

#### Request Parameters:
- `file`: PDF file to upload and analyze
- `include_pdf_content` (optional): If set to any value, includes the base64-encoded PDF content in the response

#### Response:
A JSON object containing:
```json
{
    "success": true,
    "info": {
        "success": true,
        "file_size": 123456,
        "file_size_formatted": "120 KB",
        "page_count": 5,
        "metadata": {
            "creationDate": "D:20230324120000+00",
            "modDate": "D:20230324150000+00",
            "title": "Sample PDF",
            "author": "John Doe",
            "producer": "Adobe Acrobat",
            "subject": "Example Subject"
        },
        "pages_info": [
            {
                "page_number": 1,
                "width": 612,
                "height": 792,
                "rotation": 0,
                "has_images": true,
                "has_text": true
            },
            // Additional pages...
        ],
        "created_date": "D:20230324120000+00",
        "modified_date": "D:20230324150000+00",
        "title": "Sample PDF",
        "author": "John Doe",
        "producer": "Adobe Acrobat",
        "subject": "Example Subject",
        "filename": "unique_filename.pdf",  // Important: Use this in subsequent API calls
        "original_name": "original_filename.pdf"
    }
}
```

If `include_pdf_content` is specified, the response will also include:
- `pdf_base64`: Base64-encoded string of the PDF content

#### Important Note:
The `filename` value (unique_filename) returned by this endpoint should be used in subsequent API calls when you need to perform operations on this PDF.

### `/api/delete_pages`

Deletes specified pages from an uploaded PDF file.

**Endpoint:** `POST /api/delete_pages`

#### Request Parameters:
- `file`: PDF file to modify
- `pages_to_remove`: Comma-separated list of page numbers to remove

#### Response:
A JSON object containing:
```json
{
    "success": true,
    "output_filename": "deleted_pages_uuid_filename.pdf",
    "original_filename": "original_filename.pdf",
    "pages_removed": [1, 3, 5],
    "total_pages": 10,
    "new_page_count": 7
}
```

#### Implementation:
This endpoint uses the `remove_pdf_pages` function to perform the page deletion:

```python
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
        result = remove_pdf_pages(file_data['filepath'], pages, output_filepath)

        if result["success"]:
            result["output_filename"] = output_filename
            result["original_filename"] = file_data['original_filename']
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### `/api/insert_pdf`

Inserts a PDF into another PDF at a specific position.

**Endpoint:** `POST /api/insert_pdf`

#### Request Parameters:
- `base_file`: Base PDF file (into which the other will be inserted)
- `insert_file`: PDF file to insert
- `position`: Page position for insertion (1-based indexing)

#### Response:
A JSON object containing:
```json
{
    "success": true,
    "output_filename": "inserted_uuid_filename.pdf",
    "total_pages": 15
}
```

## Application Flow Patterns

### Pattern 1: Direct File Upload and Processing

Used when no preview is needed before the final operation:

1. Frontend directly submits the form to the API endpoint (e.g., `/api/merge`)
2. The endpoint calls `handle_file_upload` to process the uploaded file(s)
3. The operation is performed, and results are returned

**Example:**
```python
@pdf_api_bp.route('/operation', methods=['POST'])
def pdf_operation_api():
    # Handle file upload
    file_data, error_response, status_code = handle_file_upload(request)
    if error_response:
        return jsonify(error_response), status_code
        
    # Generate output filepath
    output_filepath, output_filename = generate_result_filepath(
        file_data['original_filename'], prefix="operation_result"
    )
    
    # Perform operation
    result = perform_operation(file_data['filepath'], output_filepath)
    
    # Return result
    if result["success"]:
        result["output_filename"] = output_filename
        return jsonify(result)
    else:
        return jsonify(result), 400
```

### Pattern 2: File Upload with Preview Using `/extract-info`

Used when PDF information is needed for preview or validation before the final operation:

1. Frontend uploads the file to `/api/extract-info` to get PDF information and save the file
2. Frontend displays a preview with the extracted information and performs validations
3. When the user confirms, the frontend submits the form to the specific operation endpoint, using the unique filename returned by the `/extract-info` endpoint

**Example Frontend Flow:**
```javascript
// Step 1: Upload and get information via extract-info
async function uploadForPreview() {
    const formData = new FormData();
    formData.append('file', pdfFileInput.files[0]);
    
    const response = await fetch('/api/extract-info', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    if (data.success) {
        // Store the unique filename for later use
        document.getElementById('unique_filename').value = data.info.filename;
        
        // Display preview with data.info
        displayPreview(data.info);
        
        // Validate based on PDF info (e.g., page count)
        validatePageNumbers(data.info.page_count);
    }
}

// Example of frontend validation using the page_count from extract-info
function validatePageNumbers(totalPages) {
    const deletePageInput = document.getElementById('pages_to_remove');
    
    deletePageInput.addEventListener('change', function() {
        const pageNumbers = this.value.split(',').map(p => parseInt(p.trim()));
        
        // Check if any page number exceeds the total
        const invalidPages = pageNumbers.filter(p => p < 1 || p > totalPages);
        
        if (invalidPages.length > 0) {
            document.getElementById('page_error').textContent = 
                `Invalid page numbers: ${invalidPages.join(', ')}. PDF has ${totalPages} pages.`;
            document.getElementById('submit_button').disabled = true;
        } else {
            document.getElementById('page_error').textContent = '';
            document.getElementById('submit_button').disabled = false;
        }
    });
}

// Step 2: Submit for processing with the unique filename
async function submitOperation() {
    const formData = new FormData();
    formData.append('unique_filename', document.getElementById('unique_filename').value);
    formData.append('pages_to_remove', document.getElementById('pages_to_remove').value);
    
    const response = await fetch('/api/delete_pages', {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    if (result.success) {
        showSuccessMessage(`Pages removed. New document has ${result.new_page_count} pages.`);
        provideDownloadLink(`/api/download/${result.output_filename}`);
    } else {
        showErrorMessage(result.error);
    }
}
```

**Example Backend Processing:**
```python
@pdf_api_bp.route('/specific-operation', methods=['POST'])
def specific_operation_api():
    # Check if we have a unique filename or need to upload a new file
    unique_filename = request.form.get('unique_filename')
    
    if unique_filename:
        # File was previously uploaded via /extract-info
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
    else:
        # New file upload
        file_data, error_response, status_code = handle_file_upload(request)
        if error_response:
            return jsonify(error_response), status_code
        filepath = file_data['filepath']
        unique_filename = file_data['unique_filename']
    
    # Get other parameters
    other_param = request.form.get('other_parameter')
    
    # Generate output filepath
    output_filepath, output_filename = generate_result_filepath(
        unique_filename, prefix="operation_result"
    )
    
    # Perform operation
    result = perform_operation(filepath, other_param, output_filepath)
    
    # Return result
    if result["success"]:
        result["output_filename"] = output_filename
        return jsonify(result)
    else:
        return jsonify(result), 400
```

### Pattern 3: Multiple File Upload with Validation

Used when multiple files need to be uploaded and validated:

1. Frontend submits multiple files to the API endpoint
2. Each file is validated and processed
3. The operation is performed on all valid files

**Example:**
```python
@pdf_api_bp.route('/multi-file-operation', methods=['POST'])
def multi_file_operation_api():
    # Get files from the request
    files = request.files.getlist('files')
    
    if not files or len(files) < 2:
        return jsonify({'error': 'At least two files are required'}), 400
    
    # Process all files
    valid_filepaths = []
    for file in files:
        # Handle each file
        file_data, error, status = handle_file_upload_single_file(file)
        if not error:
            valid_filepaths.append(file_data['filepath'])
    
    if len(valid_filepaths) < 2:
        return jsonify({'error': 'At least two valid files are required'}), 400
    
    # Generate output filepath
    output_filepath, output_filename = generate_result_filepath(
        "result.pdf", prefix="multi_file_result"
    )
    
    # Perform operation
    result = perform_multi_file_operation(valid_filepaths, output_filepath)
    
    # Return result
    if result["success"]:
        result["output_filename"] = output_filename
        return jsonify(result)
    else:
        return jsonify(result), 400
```

## Error Handling

All API endpoints follow a consistent error handling pattern:

1. Validate input parameters
2. Process files with proper error handling
3. Return a JSON response with:
   - Success case: `{"success": true, ...}`
   - Error case: `{"error": "Error message"}` with appropriate HTTP status code

Example error responses:
- `400 Bad Request`: Missing or invalid parameters
- `404 Not Found`: File not found
- `500 Internal Server Error`: Processing errors

## Download Result Files

After processing, result files can be downloaded using:

**Endpoint:** `GET /api/download/<filename>`

This endpoint serves the processed file as an attachment.

## Best Practices

1. **File Upload Pattern Selection:**
   - Use direct upload (Pattern 1) for simple operations that don't require preview
   - Use `/api/extract-info` (Pattern 2) when the user needs to see PDF details before proceeding or when validation is needed
   - Use multiple file upload (Pattern 3) for operations that require multiple PDFs

2. **Using `/api/extract-info` Effectively:**
   - Always save the returned `filename` (unique_filename) to use in subsequent API calls
   - Use the PDF page count and other metadata for frontend validations
   - Consider using `include_pdf_content=true` if you need to display the PDF in the frontend

3. **Error Handling in PDF Operations:**
   - All PDF operation functions like `remove_pdf_pages` should return a consistent result structure
   - Always validate input parameters before processing
   - Handle exceptions and return meaningful error messages

4. **Security Considerations:**
   - Always use `secure_filename` to prevent path traversal attacks
   - Validate file extensions before processing
   - Set appropriate file size limits in your application configuration

5. **Performance Optimization:**
   - Clean up temporary files after processing
   - Consider implementing a job queue for processing large files
   - Add caching for frequently accessed PDF information