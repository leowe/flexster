import qrcode
from qrcode.main import GenericImage


def generate(data, box_size=20, border=10) -> GenericImage:
    qr = qrcode.QRCode(
        version=3,
        box_size=box_size,
        border=border,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
    )

    # Add the data to the QR code object
    qr.add_data(data)

    # Make the QR code
    qr.make(fit=True)

    # Create an image from the QR code with a black fill color and white background
    return qr.make_image(fill_color="black", back_color="white")


class QRGenerator:
    def __init__(self, url: str):
        self.url = url
        self.qr_code = generate(self.url)

    def save(self, file_name: str) -> None:
        # Save the QR code image
        self.qr_code.save(file_name)


if __name__ == "__main__":
    url = "https://music.apple.com/de/album/rolling-in-the-deep/403037872?i=403037877"
    box_size = 20
    border = 10
    QRGenerator(url).save("rolling-in-the-deep-qr.png")
