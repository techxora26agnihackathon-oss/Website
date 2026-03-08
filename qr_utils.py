import io
import os
import qrcode
from qrcode.image.pil import PilImage


def generate_qr(unique_id: str, save_dir: str) -> str:
    """
    Generate a QR code PNG for the given unique_id.
    Returns the relative path (for use in url_for / static serving).
    """
    filename = f"{unique_id}.png"
    filepath = os.path.join(save_dir, filename)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(unique_id)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#00f5ff", back_color="#0d0d1a")
    img.save(filepath)

    return f"qrcodes/{filename}"
