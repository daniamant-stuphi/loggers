"""Build icon/app.ico from the hand-drawn icon/icon_<size>.png images.

The PNGs are not square (e.g. 16x14), so each one is centred on a
transparent square of its nominal size rather than stretched. Sizes with
no PNG of their own (48 px, which Explorer uses for medium icons) are
scaled down from the largest image.

Usage:  python make_icon.py
"""
import os

from PIL import Image

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon")
ICO_PATH = os.path.join(ICON_DIR, "app.ico")
PNG_SIZES = [16, 32, 48, 64, 128, 256]
ICO_SIZES = [16, 32, 48, 64, 128, 256]


def square(image: Image.Image, size: int) -> Image.Image:
    """Fit the image inside a transparent size x size square, centred."""
    image = image.convert("RGBA")
    if image.width > size or image.height > size:
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    return canvas


def main() -> None:
    images = {
        size: square(Image.open(os.path.join(ICON_DIR, f"icon_{size}.png")), size)
        for size in PNG_SIZES
    }
    largest = images[max(PNG_SIZES)]
    for size in ICO_SIZES:
        if size not in images:
            images[size] = square(largest, size)

    # Pillow takes each size from append_images when one matches exactly
    ordered = [images[size] for size in sorted(ICO_SIZES, reverse=True)]
    ordered[0].save(
        ICO_PATH,
        sizes=[(size, size) for size in ICO_SIZES],
        append_images=ordered[1:],
    )
    print("Wrote", ICO_PATH)


if __name__ == "__main__":
    main()
