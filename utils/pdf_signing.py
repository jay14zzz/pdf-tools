import io
import base64
import numpy as np
import cv2
import fitz
from PIL import Image
import os


def crop_signature(image_data):
    """Crop the signature by detecting its bounding box."""
    # Convert image data to PIL Image
    image = Image.open(io.BytesIO(image_data)).convert("L")
    np_image = np.array(image)

    # Detect non-white pixels
    non_white_pixels = np.where(np_image < 200)

    if non_white_pixels[0].size and non_white_pixels[1].size:
        x_min, x_max = non_white_pixels[1].min(), non_white_pixels[1].max()
        y_min, y_max = non_white_pixels[0].min(), non_white_pixels[0].max()

        # Add padding
        padding = 5
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(np_image.shape[1] - 1, x_max + padding)
        y_max = min(np_image.shape[0] - 1, y_max + padding)

        # Crop
        cropped_image = image.crop((x_min, y_min, x_max + 1, y_max + 1))
        output = io.BytesIO()
        cropped_image.save(output, format='PNG', dpi=(600, 600))
        return output.getvalue()
    else:
        return None


def extract_signature(image_data):
    """Extracts ink from signature, making background transparent."""
    image = Image.open(io.BytesIO(image_data)).convert("RGBA")
    np_image = np.array(image)

    # Convert to grayscale
    gray = cv2.cvtColor(np_image, cv2.COLOR_RGBA2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Create alpha channel
    alpha_channel = binary.copy()
    alpha_channel[alpha_channel > 0] = 255
    alpha_channel[alpha_channel == 0] = 0

    # Merge back into RGBA image
    final_image = np.dstack([np_image[:, :, 0], np_image[:, :, 1], np_image[:, :, 2], alpha_channel])
    extracted_signature = Image.fromarray(final_image)

    output = io.BytesIO()
    extracted_signature.save(output, format='PNG', dpi=(600, 600))
    return output.getvalue()


def process_signature_image(signature_data):
    """Process the signature image by cropping and extracting it."""
    # Step 1: Crop the signature
    cropped_data = crop_signature(signature_data)
    if not cropped_data:
        return False, {'error': 'No signature detected'}, None

    # Step 2: Extract the signature
    extracted_data = extract_signature(cropped_data)

    # Convert to base64 for displaying in HTML
    extracted_base64 = base64.b64encode(extracted_data).decode('utf-8')

    return True, extracted_data, extracted_base64


def get_pdf_info(pdf_path):
    """Get PDF dimensions and preview image."""
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        width, height = page.rect.width, page.rect.height

        # Convert first page to image for preview
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
        img_data = pix.tobytes("png")
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        doc.close()

        return True, {
            'pdf_width': width,
            'pdf_height': height,
            'pdf_image': f'data:image/png;base64,{img_base64}'
        }
    except Exception as e:
        return False, {'error': f'Failed to process PDF: {str(e)}'}


def sign_pdf_document(pdf_path, sig_path, output_path, coords, page_num=0):
    """
    Sign a PDF document by inserting a signature image

    Args:
        pdf_path: Path to the PDF file
        sig_path: Path to the signature image
        output_path: Path to save the signed PDF
        coords: Dict containing x, y, width, height
        page_num: Page number to add signature (0-indexed)

    Returns:
        Dict containing success status and message
    """
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        page = doc[page_num]

        # Extract coordinates
        x = float(coords.get('x', 0))
        y = float(coords.get('y', 0))
        width = float(coords.get('width', 150))
        height = float(coords.get('height', 80))

        # Add signature to PDF
        sig_rect = fitz.Rect(x, y, x + width, y + height)
        page.insert_image(sig_rect, filename=sig_path)

        # Save the modified PDF
        doc.save(output_path)
        doc.close()

        return True, {
            'message': 'PDF signed successfully'
        }
    except Exception as e:
        return False, {'error': f'Failed to sign PDF: {str(e)}'}


