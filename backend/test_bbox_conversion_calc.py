#!/usr/bin/env python3
"""Calculate bbox conversion from Unstructured pixels to PDF points."""

import fitz

# Test file
test_file = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/mole-scannable.pdf"

# From the test output
image_width = 1654
image_height = 2339

# Sample coordinate from Element 0
pixel_bbox = [244.0, 116.0, 369.0, 148.0]  # x0, y0, x1, y1

print("=" * 60)
print("BBOX CONVERSION CALCULATION")
print("=" * 60)

# Get PDF dimensions
doc = fitz.open(test_file)
page = doc[0]  # First page
pdf_width = page.rect.width  # in points
pdf_height = page.rect.height  # in points
doc.close()

print(f"\nImage dimensions: {image_width}x{image_height} pixels")
print(f"PDF dimensions: {pdf_width:.2f}x{pdf_height:.2f} points")

# Calculate scale factors
scale_x = pdf_width / image_width
scale_y = pdf_height / image_height

print(f"\nScale factors:")
print(f"  X: {scale_x:.6f} (PDF width / image width)")
print(f"  Y: {scale_y:.6f} (PDF height / image height)")

# Calculate DPI
dpi_x = image_width / (pdf_width / 72)  # 72 points per inch
dpi_y = image_height / (pdf_height / 72)

print(f"\nEffective DPI:")
print(f"  X: {dpi_x:.1f}")
print(f"  Y: {dpi_y:.1f}")

# Convert sample bbox
print(f"\nSample conversion:")
print(f"  Original pixel bbox: {pixel_bbox}")

converted_bbox = [
    pixel_bbox[0] * scale_x,
    pixel_bbox[1] * scale_y,
    pixel_bbox[2] * scale_x,
    pixel_bbox[3] * scale_y
]

print(f"  Converted PDF bbox: [{converted_bbox[0]:.2f}, {converted_bbox[1]:.2f}, {converted_bbox[2]:.2f}, {converted_bbox[3]:.2f}]")

# Calculate dimensions
orig_width = pixel_bbox[2] - pixel_bbox[0]
orig_height = pixel_bbox[3] - pixel_bbox[1]
conv_width = converted_bbox[2] - converted_bbox[0]
conv_height = converted_bbox[3] - converted_bbox[1]

print(f"\nDimensions:")
print(f"  Original: {orig_width:.1f} x {orig_height:.1f} pixels")
print(f"  Converted: {conv_width:.2f} x {conv_height:.2f} points")

# Check if reasonable
if converted_bbox[0] >= 0 and converted_bbox[1] >= 0 and converted_bbox[2] <= pdf_width and converted_bbox[3] <= pdf_height:
    print("\n✅ Converted bbox is within page bounds!")
else:
    print("\n❌ Converted bbox is outside page bounds!")
    if converted_bbox[2] > pdf_width:
        print(f"  X exceeds page: {converted_bbox[2]:.2f} > {pdf_width:.2f}")
    if converted_bbox[3] > pdf_height:
        print(f"  Y exceeds page: {converted_bbox[3]:.2f} > {pdf_height:.2f}")