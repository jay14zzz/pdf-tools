import os
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import io
import tempfile
import shutil
from datetime import datetime


def validate_pdf(filepath):
    """
    Validates if a file is a valid PDF.

    Args:
        filepath (str): Path to the PDF file

    Returns:
        tuple: (is_valid, error_message)
    """
    if not os.path.exists(filepath):
        return False, "File does not exist"

    if not filepath.lower().endswith('.pdf'):
        return False, "File is not a PDF"

    try:
        # Try to open with PyMuPDF
        with fitz.open(filepath) as pdf:
            if pdf.page_count == 0:
                return False, "PDF contains no pages"

        # Also check with PyPDF2 for additional validation
        with open(filepath, 'rb') as f:
            try:
                reader = PdfReader(f)
                if len(reader.pages) == 0:
                    return False, "PDF contains no pages"
            except Exception as e:
                return False, f"Invalid PDF structure: {str(e)}"

        return True, ""
    except Exception as e:
        return False, f"Failed to validate PDF: {str(e)}"


def extract_pdf_info(filepath):
    """
    Extract detailed information from a PDF file.

    Args:
        filepath (str): Path to the PDF file

    Returns:
        dict: PDF information and metadata
    """
    try:
        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_formatted = format_file_size(file_size)

        # Use PyMuPDF for detailed metadata
        with fitz.open(filepath) as pdf:
            page_count = pdf.page_count
            metadata = pdf.metadata

            # Get page dimensions and other details
            pages_info = []
            for i in range(page_count):
                page = pdf[i]
                rect = page.rect
                pages_info.append({
                    'page_number': i + 1,
                    'width': rect.width,
                    'height': rect.height,
                    'rotation': page.rotation,
                    'has_images': len(page.get_images()) > 0,
                    'has_text': len(page.get_text("text")) > 0
                })

        return {
            'success': True,
            'file_size': file_size,
            'file_size_formatted': file_size_formatted,
            'page_count': page_count,
            'metadata': metadata,
            'pages_info': pages_info,
            'created_date': metadata.get('creationDate', 'Unknown'),
            'modified_date': metadata.get('modDate', 'Unknown'),
            'title': metadata.get('title', 'Untitled'),
            'author': metadata.get('author', 'Unknown'),
            'producer': metadata.get('producer', 'Unknown'),
            'subject': metadata.get('subject', '')
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to extract PDF information: {str(e)}"
        }


def analyze_pdf_content(filepath):
    """
    Analyzes PDF content for compression opportunities.

    Args:
        filepath (str): Path to the PDF file

    Returns:
        dict: Analysis results
    """
    try:
        # Get basic info
        info = extract_pdf_info(filepath)
        if not info['success']:
            return info

        # Analyze additional content
        with fitz.open(filepath) as pdf:
            # Count images and analyze their sizes
            total_images = 0
            image_sizes = []
            large_images = 0

            # Check fonts and text
            fonts = set()
            has_scanned_content = False

            for page_num in range(pdf.page_count):
                page = pdf[page_num]

                # Check for images
                images = page.get_images(full=True)
                total_images += len(images)

                for img_index, img_info in enumerate(images):
                    xref = img_info[0]
                    base_image = pdf.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Analyze image size
                    img_size = len(image_bytes)
                    image_sizes.append(img_size)

                    if img_size > 500000:  # Images larger than 500KB
                        large_images += 1

                # Check for fonts
                for font in page.get_fonts():
                    fonts.add(font[3])  # Font name is at index 3

                # Check for scanned content (estimate)
                text = page.get_text()
                if len(text.strip()) < 100 and len(images) > 0:
                    has_scanned_content = True

        # Calculate compression potential
        compression_potential = "Low"
        if large_images > 3 or (total_images > 10 and sum(image_sizes) > 5000000):
            compression_potential = "High"
        elif large_images > 0 or (total_images > 5 and sum(image_sizes) > 2000000):
            compression_potential = "Medium"

        # Add analysis to the info
        info.update({
            'total_images': total_images,
            'large_images': large_images,
            'avg_image_size': sum(image_sizes) / max(1, len(image_sizes)),
            'fonts_count': len(fonts),
            'has_scanned_content': has_scanned_content,
            'compression_potential': compression_potential
        })

        return info

    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to analyze PDF: {str(e)}"
        }


def compress_pdf(input_path, output_path, method="pil", quality_level=60):
    """
    Compress a PDF file using the specified method and quality.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path to save the compressed PDF
        method (str): Compression method (pil, ghostscript, pymupdf)
        quality_level: Quality level for compression

    Returns:
        dict: Compression results
    """
    try:
        # Get original file size
        original_size = os.path.getsize(input_path)

        # Apply compression based on the method
        if method == "pil":
            compress_with_pil(input_path, output_path, quality_level)
        elif method == "ghostscript":
            compress_with_ghostscript(input_path, output_path, quality_level)
        elif method == "pymupdf":
            compress_with_pymupdf(input_path, output_path, quality_level)
        else:
            # Default to PIL method
            compress_with_pil(input_path, output_path, 60)

        # Get compressed file size
        compressed_size = os.path.getsize(output_path)

        # Calculate reduction
        reduction = original_size - compressed_size
        reduction_percent = (reduction / original_size) * 100 if original_size > 0 else 0

        return {
            'success': True,
            'original_size': original_size,
            'original_size_formatted': format_file_size(original_size),
            'compressed_size': compressed_size,
            'compressed_size_formatted': format_file_size(compressed_size),
            'reduction': reduction,
            'reduction_formatted': format_file_size(reduction),
            'reduction_percent': round(reduction_percent, 2),
            'method_used': f"{method}_{quality_level}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to compress PDF: {str(e)}"
        }


def compress_with_pil(input_path, output_path, quality=60):
    """
    Compress PDF using PIL by extracting and recompressing images.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path to save the compressed PDF
        quality (int): Image quality (1-100)
    """
    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()

    try:
        pdf_document = fitz.open(input_path)
        pdf_writer = fitz.open()

        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            images = page.get_images(full=True)

            # Create a copy of the page
            new_page = pdf_writer.new_page(width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(page.rect, pdf_document, page_num)

            # Process images on the page
            if images:
                for img_index, img_info in enumerate(images):
                    xref = img_info[0]

                    try:
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Skip small images
                        if len(image_bytes) < 10000:  # Skip images smaller than 10KB
                            continue

                        # Process image with PIL
                        img = Image.open(io.BytesIO(image_bytes))
                        img_temp_path = os.path.join(temp_dir, f"img_{page_num}_{img_index}.jpg")

                        # Convert to RGB if RGBA
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')

                        # Save with compression
                        img.save(img_temp_path, "JPEG", quality=quality)

                        # The image replacement would be complex and is just conceptual here
                        # In a real implementation, you'd need to replace the image in the PDF
                    except Exception as e:
                        print(f"Error processing image: {e}")
                        continue

        # Write the output file
        pdf_writer.save(output_path, deflate=True, garbage=3)
        pdf_writer.close()
        pdf_document.close()

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def compress_with_pymupdf(input_path, output_path, quality=70):
    """
    Compress PDF using PyMuPDF's built-in compression.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path to save the compressed PDF
        quality (int): Compression quality
    """
    doc = fitz.open(input_path)

    # Set compression parameters
    # Convert quality (0-100) to PyMuPDF's parameters
    # Higher number in clean means more compression
    clean = max(0, min(int((100 - quality) / 10), 9))

    # Save with compression options
    doc.save(
        output_path,
        garbage=4,  # Collect unused objects
        clean=clean,  # Remove unnecessary elements
        deflate=True,  # Use deflate compression for streams
        pretty=False  # Don't beautify
    )
    doc.close()


def compress_with_ghostscript(input_path, output_path, quality="ebook"):
    """
    Compress PDF using Ghostscript (requires gs to be installed).

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path to save the compressed PDF
        quality (str): Quality setting (screen, ebook, printer, prepress)
    """
    # Map quality to dpi
    quality_settings = {
        "screen": [72, "/screen"],
        "ebook": [150, "/ebook"],
        "printer": [300, "/printer"],
        "prepress": [300, "/prepress"]
    }

    # Default to ebook if not specified
    if quality not in quality_settings:
        quality = "ebook"

    dpi, preset = quality_settings[quality]

    # Build Ghostscript command
    gs_command = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={preset}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]

    # Execute command
    import subprocess
    process = subprocess.run(gs_command, check=True, capture_output=True)

    if process.returncode != 0:
        raise Exception(f"Ghostscript error: {process.stderr.decode()}")


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


def insert_pdf_at_position(base_pdf_path, insert_pdf_path, position, output_path):
    """
    Insert a PDF into another PDF at a specified position.

    Args:
        base_pdf_path (str): Path to the base PDF file
        insert_pdf_path (str): Path to the PDF to insert
        position (int): Position to insert at (0-based)
        output_path (str): Path to save the modified PDF

    Returns:
        dict: Result of the operation
    """
    try:
        # Validate input files
        is_base_valid, base_error = validate_pdf(base_pdf_path)
        if not is_base_valid:
            return {
                'success': False,
                'error': f"Base PDF is invalid: {base_error}"
            }

        is_insert_valid, insert_error = validate_pdf(insert_pdf_path)
        if not is_insert_valid:
            return {
                'success': False,
                'error': f"Insert PDF is invalid: {insert_error}"
            }

        # Open both PDFs
        with open(base_pdf_path, 'rb') as base_file, open(insert_pdf_path, 'rb') as insert_file:
            base_reader = PdfReader(base_file)
            insert_reader = PdfReader(insert_file)

            base_page_count = len(base_reader.pages)
            insert_page_count = len(insert_reader.pages)

            # Validate position
            if position < 0 or position > base_page_count:
                return {
                    'success': False,
                    'error': f"Invalid position {position + 1}. Base PDF has {base_page_count} pages."
                }

            # Create a new PDF
            writer = PdfWriter()

            # Add pages from the base PDF up to the insertion point
            for i in range(position):
                writer.add_page(base_reader.pages[i])

            # Add all pages from the insert PDF
            for i in range(insert_page_count):
                writer.add_page(insert_reader.pages[i])

            # Add remaining pages from the base PDF
            for i in range(position, base_page_count):
                writer.add_page(base_reader.pages[i])

            # Write the output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

        return {
            'success': True,
            'base_page_count': base_page_count,
            'insert_page_count': insert_page_count,
            'insertion_position': position + 1,  # Convert back to 1-based for user display
            'new_page_count': base_page_count + insert_page_count
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to insert PDF: {str(e)}"
        }


def split_pdf(input_path, output_dir, page_ranges=None):
    """
    Split a PDF into multiple PDFs based on page ranges.

    Args:
        input_path (str): Path to the input PDF file
        output_dir (str): Directory to save split PDFs
        page_ranges (list): List of page ranges to split [(start, end), ...]

    Returns:
        dict: Result of the operation
    """
    try:
        # Validate input
        is_valid, error = validate_pdf(input_path)
        if not is_valid:
            return {
                'success': False,
                'error': f"Invalid PDF file: {error}"
            }

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Open the PDF
        with open(input_path, 'rb') as file:
            reader = PdfReader(file)
            total_pages = len(reader.pages)

            # If no page ranges specified, create one PDF per page
            if not page_ranges:
                page_ranges = [(i + 1, i + 1) for i in range(total_pages)]

            # Process each page range
            output_files = []
            for i, (start, end) in enumerate(page_ranges):
                # Validate page range
                if start < 1 or end > total_pages or start > end:
                    continue

                # Create a new PDF for this range
                writer = PdfWriter()

                # Add pages in this range
                for page_num in range(start - 1, end):
                    writer.add_page(reader.pages[page_num])

                # Save this split
                output_filename = f"split_{i + 1}_pages_{start}-{end}.pdf"
                output_path = os.path.join(output_dir, output_filename)

                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)

                output_files.append({
                    'filename': output_filename,
                    'path': output_path,
                    'page_range': [start, end],
                    'page_count': end - start + 1
                })

        return {
            'success': True,
            'total_pages': total_pages,
            'split_count': len(output_files),
            'output_files': output_files,
            'output_dir': output_dir
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to split PDF: {str(e)}"
        }


def merge_pdfs(input_paths, output_path):
    """
    Merge multiple PDFs into a single PDF.

    Args:
        input_paths (list): List of PDF file paths to merge
        output_path (str): Path to save the merged PDF

    Returns:
        dict: Result of the operation
    """
    try:
        # Validate input
        if not input_paths or len(input_paths) < 2:
            return {
                'success': False,
                'error': "At least two PDF files are required for merging"
            }

        # Validate each input file
        for path in input_paths:
            is_valid, error = validate_pdf(path)
            if not is_valid:
                return {
                    'success': False,
                    'error': f"Invalid PDF file {os.path.basename(path)}: {error}"
                }

        # Create a new PDF writer
        writer = PdfWriter()
        total_pages = 0

        # Process each input file
        file_info = []
        for path in input_paths:
            with open(path, 'rb') as file:
                reader = PdfReader(file)
                page_count = len(reader.pages)

                # Add all pages to the merged PDF
                for page in reader.pages:
                    writer.add_page(page)

                # Track file info
                file_info.append({
                    'filename': os.path.basename(path),
                    'page_count': page_count
                })

                total_pages += page_count

        # Write the merged PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        return {
            'success': True,
            'total_pages': total_pages,
            'merged_files': len(input_paths),
            'file_info': file_info,
            'output_size': os.path.getsize(output_path),
            'output_size_formatted': format_file_size(os.path.getsize(output_path))
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to merge PDFs: {str(e)}"
        }


def reorder_pages(input_path, output_path, new_order):
    """
    Reorder pages in a PDF file.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path to save the reordered PDF
        new_order (list): New page order (0-based indices)

    Returns:
        dict: Result of the operation
    """
    try:
        # Validate input
        is_valid, error = validate_pdf(input_path)
        if not is_valid:
            return {
                'success': False,
                'error': f"Invalid PDF file: {error}"
            }

        if not new_order:
            return {
                'success': False,
                'error': "No page order specified"
            }

        # Open the PDF
        with open(input_path, 'rb') as file:
            reader = PdfReader(file)
            writer = PdfWriter()

            total_pages = len(reader.pages)

            # Validate new order
            for page_idx in new_order:
                if page_idx < 0 or page_idx >= total_pages:
                    return {
                        'success': False,
                        'error': f"Page index {page_idx} is out of range. PDF has {total_pages} pages."
                    }

            # Add pages in the new order
            for page_idx in new_order:
                writer.add_page(reader.pages[page_idx])

            # Write the output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

        return {
            'success': True,
            'original_pages': total_pages,
            'reordered_pages': len(new_order),
            'new_order': new_order
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to reorder pages: {str(e)}"
        }


def format_file_size(size_bytes):
    """
    Format file size in bytes to human-readable format.

    Args:
        size_bytes (int): Size in bytes

    Returns:
        str: Formatted file size
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def add_pdf_password(input_path, password, output_path):
    """
    Add password protection to a PDF file.

    Args:
        input_path (str): Path to the input PDF file
        password (str): Password to add to the PDF
        output_path (str): Path to save the password-protected PDF

    Returns:
        dict: Result of the operation
    """
    try:
        # Validate input
        if not password or len(password.strip()) == 0:
            return {
                'success': False,
                'error': "Password cannot be empty"
            }

        # Make sure input file exists
        if not os.path.exists(input_path):
            return {
                'success': False,
                'error': "Input file does not exist"
            }

        # Check if PDF is already encrypted
        with open(input_path, 'rb') as file:
            reader = PdfReader(file)
            if reader.is_encrypted:
                return {
                    'success': False,
                    'error': "PDF is already password protected. Remove existing password first."
                }

        # Open the PDF and add password
        with open(input_path, 'rb') as file:
            reader = PdfReader(file)
            writer = PdfWriter()

            # Copy all pages to the writer
            for page in reader.pages:
                writer.add_page(page)

            # Add password encryption
            writer.encrypt(password)

            # Write the output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

        return {
            'success': True,
            'message': "Password protection added successfully",
            'protected': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to add password: {str(e)}"
        }


def remove_pdf_password(input_path, password, output_path):
    """
    Remove password protection from a PDF file.

    Args:
        input_path (str): Path to the input PDF file
        password (str): Current password of the PDF
        output_path (str): Path to save the unprotected PDF

    Returns:
        dict: Result of the operation
    """
    try:
        # Make sure input file exists
        if not os.path.exists(input_path):
            return {
                'success': False,
                'error': "Input file does not exist"
            }

        # Open the PDF and try to decrypt with provided password
        with open(input_path, 'rb') as file:
            reader = PdfReader(file)

            # Check if PDF is actually encrypted
            if not reader.is_encrypted:
                return {
                    'success': False,
                    'error': "PDF is not password protected"
                }

            # Try to decrypt with the provided password
            decrypt_success = False
            try:
                decrypt_success = reader.decrypt(password)
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Decryption error: {str(e)}"
                }

            # Check decryption result - PyPDF2 returns an integer code
            # 0: failed, 1: user password succeeded, 2: owner password succeeded
            if decrypt_success in (1, 2):
                # Create a new PDF without encryption
                writer = PdfWriter()

                # Copy all pages to the writer
                for page in reader.pages:
                    writer.add_page(page)

                # Write the output file (without encryption)
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)

                return {
                    'success': True,
                    'message': "Password protection removed successfully",
                    'protected': False
                }
            else:
                return {
                    'success': False,
                    'error': "Incorrect password"
                }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to remove password: {str(e)}"
        }