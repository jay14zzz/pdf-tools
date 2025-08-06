# PDF Operations Flask App

A Flask web application for performing various PDF operations including merge, split, compress, delete pages, and digital signing.

## Features

- **Merge PDFs** - Combine multiple PDF files into one
- **Split PDFs** - Extract specific pages or split into separate files
- **Compress PDFs** - Reduce file size while maintaining quality
- **Delete Pages** - Remove specific pages from PDF documents
- **Digital Signing** - Add digital signatures to PDF files
- **Insert PDFs** - Insert one PDF into another at a specific position
- **PDF Analysis** - Extract metadata and document information

## Architecture

The application follows a clean separation between frontend views and API operations:

- **Page Routes**: Render HTML templates for user interface
- **API Routes**: Handle PDF operations with `/api` prefix
- **Two Upload Patterns**:
  - Direct upload for simple operations
  - Upload with preview using `/api/extract-info` for operations requiring validation

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/jay14zzz/pdf-tools.git
   cd pdf-tools
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**
   ```bash
   # Create upload and result directories
   mkdir uploads results
   
   # Set Flask config in app.py
   app.config.from_object(ProductionConfig)
   # OR
   app.config.from_object(DevelopmentConfig)
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser to `http://localhost:5000`

## API Usage

### Extract PDF Information
```bash
POST /api/extract-info
# Upload PDF and get detailed information including page count, metadata, etc.
```

### Delete Pages
```bash
POST /api/delete_pages
# Remove specific pages from a PDF
```

### Merge PDFs
```bash
POST /api/merge
# Combine multiple PDFs into one file
```

### Insert PDF
```bash
POST /api/insert_pdf
# Insert one PDF into another at a specified position
```

## Dependencies

- Flask
- PyPDF2/pypdf
- PyMuPDF (fitz)
- Pillow (for image processing)
- Other dependencies listed in `requirements.txt`

## Project Structure

```
├── app.py                 # Main Flask application
├── utils/
│   ├── pdf_operations.py  # Core PDF processing functions
│   └── pdf_signing.py     # Digital signature functionality
├── templates/             # HTML templates
├── static/               # CSS, JS, and static assets
├── uploads/              # Temporary file uploads
└── results/              # Processed PDF outputs
```


## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.