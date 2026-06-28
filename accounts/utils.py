import random
import string
import qrcode
import os
from django.conf import settings

def generate_password(length=None):
    if length is None:
        length = random.randint(8, 16)
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def generate_student_login(school_id, grade, count):
    # Format: {school_id}_{grade}_{порядковый_номер}
    return f"{school_id}_{grade}_{count:03d}"

def generate_teacher_login(school_id, count):
    # Format: {school_id}_t_{порядковый_номер}
    return f"{school_id}_t_{count:03d}"

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    path = os.path.join(settings.MEDIA_ROOT, 'qr', filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return os.path.join('qr', filename)

import hmac
import hashlib
import time

def generate_dynamic_token(prefix, obj_id):
    secret = settings.SECRET_KEY.encode()
    # Time window of 120 seconds (2 minutes)
    window = int(time.time() / 120)
    message = f"{obj_id}{window}".encode()
    h = hmac.new(secret, message, hashlib.sha256).hexdigest()[:8].upper()
    return f"{prefix}_{obj_id}_{h}"

def verify_dynamic_token(token, expected_prefix):
    if not token:
        return None
    parts = token.split('_')
    if len(parts) < 3 or parts[0] != expected_prefix:
        return None
    
    obj_id = parts[1]
    received_hash = parts[2]
    
    secret = settings.SECRET_KEY.encode()
    window = int(time.time() / 120)
    
    # Check current and previous window (to allow for slight time drift or delay)
    for w in [window, window - 1]:
        message = f"{obj_id}{w}".encode()
        expected_hash = hmac.new(secret, message, hashlib.sha256).hexdigest()[:8].upper()
        if hmac.compare_digest(received_hash.upper(), expected_hash):
            return obj_id
    return None
