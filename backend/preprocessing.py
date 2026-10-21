"""Bounded PDF/image decoding and conservative scan cleanup."""
import io
import os
import numpy as np
import cv2
from PIL import Image, ImageOps, ImageSequence
from pdf2image import convert_from_bytes, pdfinfo_from_bytes

MAX_PAGES = int(os.getenv('MAX_PAGES', '20'))
MAX_PIXELS = int(os.getenv('MAX_IMAGE_PIXELS', '25000000'))
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

def load_pages(file_bytes, filename):
    if not file_bytes:
        raise ValueError('The uploaded file is empty')
    if filename.lower().endswith('.pdf'):
        if not file_bytes.lstrip().startswith(b'%PDF-'):
            raise ValueError('File contents are not a PDF')
        info = pdfinfo_from_bytes(file_bytes, timeout=20)
        count = int(info['Pages'])
        if count > MAX_PAGES:
            raise ValueError(f'Document exceeds {MAX_PAGES} pages')
        return convert_from_bytes(file_bytes, dpi=180, first_page=1, last_page=count,
                                  timeout=90, thread_count=1, size=2200)
    pages = []
    with Image.open(io.BytesIO(file_bytes)) as image:
        if getattr(image, 'n_frames', 1) > MAX_PAGES:
            raise ValueError(f'Document exceeds {MAX_PAGES} pages')
        for frame in ImageSequence.Iterator(image):
            if frame.width * frame.height > MAX_PIXELS:
                raise ValueError('Image exceeds pixel limit')
            pages.append(ImageOps.exif_transpose(frame).convert('RGB'))
    return pages

def deskew(pil_img):
    gray = np.asarray(pil_img.convert('L'))
    mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    points = cv2.findNonZero(mask)
    if points is None or len(points) < 20:
        return pil_img
    angle = cv2.minAreaRect(points)[-1]
    if angle > 45:
        angle -= 90
    if abs(angle) < .5 or abs(angle) > 12:
        return pil_img
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
    return Image.fromarray(cv2.warpAffine(np.asarray(pil_img), matrix, (w, h),
                           flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255)))

def denoise(pil_img):
    gray = np.asarray(pil_img.convert('L'))
    gray = cv2.fastNlMeansDenoising(gray, None, 5, 7, 21)
    return Image.fromarray(cv2.createCLAHE(clipLimit=2, tileGridSize=(8,8)).apply(gray)).convert('RGB')

def preprocess_page(pil_img, max_dim=2200):
    image = pil_img.copy()
    image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    return deskew(denoise(image))
