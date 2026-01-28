#!/usr/bin/env python3
"""
Script to create an "uncheck all" icon from the "check all" icon.
Replaces green checkmarks with black empty checkboxes.

This script analyzes the original image to find positions and generates
multiple versions for comparison.

Usage:
    python3 create_uncheckall_icon.py [--analyze] [--generate] [--final]

    --analyze  : Analyze the original image and print positions
    --generate : Generate multiple test versions with different parameters
    --final    : Generate the final icon with current parameters (edit FINAL_PARAMS below)

    No args    : Run all steps
"""

from PIL import Image, ImageDraw
import os
import sys

# Paths
SRC_PATH = "/home/user/Downloads/taskcoach/icon ideas/list2.png"
OUTPUT_DIR = "/home/user/Downloads/taskcoach/icon ideas"
ICONS_DIR = "/home/user/Downloads/taskcoach/taskcoachlib/gui/icons"

# Final parameters - edit these after reviewing test versions
# Use line centers for Y alignment (visually aligns checkboxes with lines)
FINAL_PARAMS = {
    'checkbox_size': 0.14,      # As fraction of image width
    'line_thickness': 0.025,    # As fraction of image width
    'left_margin': 0.158,       # X position for checkbox
    'y_positions': [0.217, 0.498, 0.779],  # Line center positions from analysis
    'corner_radius': 0.025,     # Rounded corner radius as fraction of image width
}


def analyze_image():
    """Analyze the original image to find checkmark and line positions."""
    img = Image.open(SRC_PATH).convert('RGBA')
    width, height = img.size
    pixels = img.load()

    print(f"Image size: {width}x{height}")
    print("\n" + "="*50)
    print("ANALYZING GREEN PIXELS (CHECKMARKS)")
    print("="*50)

    # Find green pixel regions (checkmarks)
    green_pixels = []
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if g > 100 and g > r * 1.5 and g > b * 1.5 and a > 50:
                green_pixels.append((x, y))

    if green_pixels:
        min_x = min(p[0] for p in green_pixels)
        max_x = max(p[0] for p in green_pixels)
        min_y = min(p[1] for p in green_pixels)
        max_y = max(p[1] for p in green_pixels)
        print(f"Green area X: {min_x} to {max_x} (width: {max_x - min_x})")
        print(f"Green area Y: {min_y} to {max_y}")
        print(f"As fractions: X {min_x/width:.3f} to {max_x/width:.3f}")

    # Find individual checkmark Y centers
    print("\nIndividual checkmark positions:")
    y_ranges = []
    in_green = False
    start_y = 0
    for y in range(height):
        has_green = any(pixels[x, y][1] > 100 and pixels[x, y][1] > pixels[x, y][0] * 1.5
                        and pixels[x, y][3] > 50 for x in range(width))
        if has_green and not in_green:
            start_y = y
            in_green = True
        elif not has_green and in_green:
            y_ranges.append((start_y, y - 1))
            in_green = False
    if in_green:
        y_ranges.append((start_y, height - 1))

    checkmark_centers = []
    for i, (y1, y2) in enumerate(y_ranges):
        center_y = (y1 + y2) // 2
        checkmark_centers.append(center_y)
        print(f"  Checkmark {i+1}: Y range {y1}-{y2}, center at {center_y} ({center_y/height:.3f})")

    print("\n" + "="*50)
    print("ANALYZING BLACK PIXELS (LINES)")
    print("="*50)

    # Find black line positions (right side only)
    print("\nIndividual line positions:")
    y_ranges_black = []
    in_black = False
    start_y = 0
    for y in range(height):
        has_black = any(pixels[x, y][0] < 50 and pixels[x, y][1] < 50 and pixels[x, y][2] < 50
                        and pixels[x, y][3] > 200 for x in range(width//2, width))
        if has_black and not in_black:
            start_y = y
            in_black = True
        elif not has_black and in_black:
            y_ranges_black.append((start_y, y - 1))
            in_black = False
    if in_black:
        y_ranges_black.append((start_y, height - 1))

    line_centers = []
    for i, (y1, y2) in enumerate(y_ranges_black):
        center_y = (y1 + y2) // 2
        line_centers.append(center_y)
        print(f"  Line {i+1}: Y range {y1}-{y2}, center at {center_y} ({center_y/height:.3f})")

    print("\n" + "="*50)
    print("SUGGESTED PARAMETERS")
    print("="*50)
    if line_centers:
        print(f"y_positions = {[round(y/height, 3) for y in line_centers]}")
    if green_pixels:
        # Estimate checkbox size from checkmark width
        checkmark_width = max_x - min_x
        print(f"checkbox_size = {checkmark_width/width:.3f}  # based on checkmark width")
        print(f"left_margin = {min_x/width:.3f}  # based on checkmark left edge")

    return line_centers, checkmark_centers


def create_uncheckall_icon(params, output_name):
    """Create an uncheckall icon with given parameters."""
    img = Image.open(SRC_PATH).convert('RGBA')
    width, height = img.size
    pixels = img.load()

    # Create result image - start by copying and removing green
    result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    result_pixels = result.load()

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # Remove green pixels (checkmarks)
            if g > 100 and g > r * 1.5 and g > b * 1.5 and a > 50:
                result_pixels[x, y] = (0, 0, 0, 0)
            else:
                result_pixels[x, y] = (r, g, b, a)

    # Draw empty checkboxes with rounded corners
    draw = ImageDraw.Draw(result)

    checkbox_size = int(width * params['checkbox_size'])
    line_thickness = max(int(width * params['line_thickness']), 2)
    left_margin = int(width * params['left_margin'])
    corner_radius = int(width * params.get('corner_radius', 0.03))

    for y_frac in params['y_positions']:
        y_center = int(height * y_frac)
        x1 = left_margin
        y1 = y_center - checkbox_size // 2
        x2 = left_margin + checkbox_size
        y2 = y_center + checkbox_size // 2

        # Draw rounded checkbox with solid black border
        # First draw filled black rounded rectangle, then white interior
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=corner_radius,
            outline=None,
            fill=(0, 0, 0, 255)
        )
        # Draw white interior (smaller by line_thickness)
        inner_radius = max(corner_radius - line_thickness, 1)
        draw.rounded_rectangle(
            [x1 + line_thickness, y1 + line_thickness,
             x2 - line_thickness, y2 - line_thickness],
            radius=inner_radius,
            outline=None,
            fill=(255, 255, 255, 0)  # Transparent interior
        )

    output_path = os.path.join(OUTPUT_DIR, output_name)
    result.save(output_path, "PNG")
    print(f"Created: {output_path}")
    return result


def generate_test_versions():
    """Generate multiple test versions with different parameters."""
    print("\n" + "="*50)
    print("GENERATING TEST VERSIONS")
    print("="*50)

    # Line centers from analysis for Y alignment
    line_y = [0.217, 0.498, 0.779]

    test_configs = [
        # (name, checkbox_size, line_thickness, left_margin, y_positions, corner_radius)
        ("test_size_22", 0.22, 0.035, 0.118, line_y, 0.045),
        ("test_size_24", 0.24, 0.04, 0.108, line_y, 0.05),
        ("test_size_26", 0.26, 0.04, 0.098, line_y, 0.055),
    ]

    for name, cb_size, thickness, margin, y_pos, radius in test_configs:
        params = {
            'checkbox_size': cb_size,
            'line_thickness': thickness,
            'left_margin': margin,
            'y_positions': y_pos,
            'corner_radius': radius,
        }
        print(f"\n{name}: size={cb_size}, thick={thickness}, radius={radius}")
        create_uncheckall_icon(params, f"{name}.png")


def generate_final():
    """Generate the final icon with FINAL_PARAMS and all sizes."""
    print("\n" + "="*50)
    print("GENERATING FINAL ICON")
    print("="*50)
    print(f"Parameters: {FINAL_PARAMS}")

    result = create_uncheckall_icon(FINAL_PARAMS, "list2_uncheckall.png")

    # Create all required sizes
    sizes = [16, 22, 32, 48]
    for size in sizes:
        resized = result.resize((size, size), Image.Resampling.LANCZOS)
        dest = os.path.join(ICONS_DIR, f"uncheckall{size}x{size}.png")
        resized.save(dest, "PNG")
        print(f"Created: uncheckall{size}x{size}.png")

    print("\nFinal icons installed to TaskCoach icons directory.")


def main():
    args = sys.argv[1:]

    if not args:
        # Run all steps
        analyze_image()
        generate_test_versions()
        print("\n" + "="*50)
        print("Review the test versions in:")
        print(f"  {OUTPUT_DIR}")
        print("Then edit FINAL_PARAMS in this script and run with --final")
        return

    if '--analyze' in args:
        analyze_image()

    if '--generate' in args:
        generate_test_versions()

    if '--final' in args:
        generate_final()


if __name__ == "__main__":
    main()
