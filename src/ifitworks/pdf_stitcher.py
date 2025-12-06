#!/usr/bin/env python3
"""
Example usage:
pdf-stitcher <input> --first-page 2 --last-page 61 --dpi 72 --rows 5 --cols 12 --margin-vertical-in 0.09 --margin-horizontal-in 0.09 test.png

Or as a module:
python -m ifitworks.pdf_stitcher <input> --first-page 2 --last-page 61 --dpi 72 --rows 5 --cols 12 --margin-vertical-in 0.09 --margin-horizontal-in 0.09 test.png
"""
import math
import argparse
import io
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image


def stitch_pattern_pdf(
    pdf_path,
    output_path,
    first_page,
    last_page,
    dpi=300,
    margin_vertical_in=None,
    margin_horizontal_in=None,
    rows=None,
    cols=None,
):
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    # Set defaults and convert margins to pixels
    margin_vertical_in = margin_vertical_in or 0.0
    margin_horizontal_in = margin_horizontal_in or 0.0

    margin_top_px = margin_bottom_px = int(round(margin_vertical_in * dpi))
    margin_left_px = margin_right_px = int(round(margin_horizontal_in * dpi))

    overlap_horizontal_px = margin_left_px
    overlap_vertical_px = margin_top_px

    print(
        f"Loading pages {first_page}–{last_page} from {pdf_path} at {dpi} DPI..."
    )

    # Open PDF with PyMuPDF
    doc = fitz.open(str(pdf_path))

    if last_page > doc.page_count:
        last_page = doc.page_count
        print(
            f"Adjusting last_page to {last_page} (document has {doc.page_count} pages)"
        )

    pages = []
    for page_num in range(first_page - 1,
                          last_page):  # fitz uses 0-based indexing
        page = doc.load_page(page_num)

        # Get PDF page dimensions in points (1/72 inch)
        pdf_rect = page.rect
        pdf_width_in = pdf_rect.width / 72.0
        pdf_height_in = pdf_rect.height / 72.0

        # Calculate the exact scaling to achieve the requested DPI
        # We want: final_pixels = page_size_inches * dpi
        target_width_px = pdf_width_in * dpi
        target_height_px = pdf_height_in * dpi

        # Calculate scale factors to achieve target pixel dimensions
        scale_x = target_width_px / pdf_rect.width
        scale_y = target_height_px / pdf_rect.height

        # Create transformation matrix with exact scaling
        mat = fitz.Matrix(scale_x, scale_y)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to PIL Image
        img_data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(img_data))
        pages.append(img)

    doc.close()

    if not pages:
        raise RuntimeError("No pages were loaded. Check page range.")

    print(f"Loaded {len(pages)} pages.")

    # Crop margins
    cropped_pages = []
    for idx, im in enumerate(pages):
        w, h = im.size
        left = margin_left_px
        top = margin_top_px
        right = w - margin_right_px
        bottom = h - margin_bottom_px

        if right <= left or bottom <= top:
            raise ValueError(
                f"Margin too large for page {idx+first_page}: "
                f"page size {w}x{h}, margins: left={margin_left_px}px, right={margin_right_px}px, "
                f"top={margin_top_px}px, bottom={margin_bottom_px}px.")

        cropped = im.crop((left, top, right, bottom))
        cropped_pages.append(cropped)

    # Assume all cropped pages same size
    tile_w, tile_h = cropped_pages[0].size
    n = len(cropped_pages)

    # Determine grid layout
    if rows is not None and cols is not None:
        print(f"Using explicit grid: {rows} rows x {cols} columns")
        if rows * cols < n:
            raise ValueError(
                f"Grid too small: rows*cols={rows*cols}, but {n} tiles were loaded."
            )
    elif rows is None and cols is None:
        # auto square-ish layout
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        print(f"Auto layout grid: {rows} rows x {cols} columns")
    else:
        raise ValueError("Specify both --rows and --cols, or neither.")

    # Calculate final image size accounting for overlaps
    big_w = cols * tile_w - (cols - 1) * overlap_horizontal_px
    big_h = rows * tile_h - (rows - 1) * overlap_vertical_px

    big_img = Image.new("RGB", (big_w, big_h), (255, 255, 255))

    # Place tiles with overlap handling
    for i, tile in enumerate(cropped_pages):
        row = i // cols
        col = i % cols

        # Calculate tile position with overlap spacing
        x = col * (tile_w - overlap_horizontal_px)
        y = row * (tile_h - overlap_vertical_px)

        tile_rgb = tile.convert("RGB")
        existing_region = big_img.crop(
            (x, y, x + tile_w, y + tile_h)).convert("RGB")

        # Blend overlapping pixels (50/50) where existing content is non-white
        existing_array = np.array(existing_region)
        tile_array = np.array(tile_rgb)

        # Find non-white pixels in existing region (overlap areas)
        overlap_mask = np.any(existing_array < 250, axis=2)

        # 50/50 blend in overlap areas, keep new tile pixels elsewhere
        blended_array = tile_array.copy()
        blended_array[overlap_mask] = (existing_array[overlap_mask] * 0.5 +
                                       tile_array[overlap_mask] * 0.5).astype(
                                           np.uint8)

        blended_tile = Image.fromarray(blended_array)
        big_img.paste(blended_tile, (x, y))

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    big_img.save(output_path)
    print(f"Saved stitched image to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Stitch tiled PDF pages into one big image.")
    parser.add_argument("pdf_path", help="Path to input PDF")
    parser.add_argument("output_path",
                        help="Path to output image (e.g. stitched.png)")

    parser.add_argument("--first-page", type=int, default=1)
    parser.add_argument("--last-page", type=int, default=None)

    parser.add_argument("--dpi", type=int, default=300)

    parser.add_argument("--margin-vertical-in",
                        type=float,
                        default=None,
                        help="Vertical margin (top and bottom) in inches")
    parser.add_argument("--margin-horizontal-in",
                        type=float,
                        default=None,
                        help="Horizontal margin (left and right) in inches")

    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--cols", type=int, default=None)

    args = parser.parse_args()

    stitch_pattern_pdf(
        pdf_path=args.pdf_path,
        output_path=args.output_path,
        first_page=args.first_page,
        last_page=args.last_page
        if args.last_page is not None else args.first_page,
        dpi=args.dpi,
        margin_vertical_in=args.margin_vertical_in,
        margin_horizontal_in=args.margin_horizontal_in,
        rows=args.rows,
        cols=args.cols,
    )


if __name__ == "__main__":
    main()
