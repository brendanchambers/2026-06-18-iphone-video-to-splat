#!/usr/bin/env python3
"""
Visualize SIFT features extracted by COLMAP.

For each image in a COLMAP project, queries the database for detected SIFT
keypoints and draws them on the image with:
  - Oriented circles showing scale and orientation
  - Feature ID numbers
  - Saves annotated images as JPEG

Usage:
  python scripts/visualize_colmap_features.py \
    --colmap-dir data/intermediates/test_4s \
    --output-dir data/intermediates/test_4s/annotated_images
"""

import argparse
import sqlite3
from pathlib import Path
import numpy as np
import cv2


def load_keypoints_from_db(db_path: Path, image_id: int) -> np.ndarray:
    """
    Load keypoints for a specific image from COLMAP database.

    Returns array of shape (num_keypoints, 6) with columns:
      [x, y, and 4 additional dimensions from COLMAP storage]
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        "SELECT rows, cols, data FROM keypoints WHERE image_id = ?",
        (image_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return np.empty((0, 6), dtype=np.float32)

    rows, cols, blob_data = row
    keypoints = np.frombuffer(blob_data, dtype=np.float32).reshape(rows, cols)
    return keypoints


def get_image_info(db_path: Path) -> list:
    """Get list of (image_id, image_name) from database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT image_id, name FROM images ORDER BY image_id;")
    images = cursor.fetchall()
    conn.close()

    return images


def draw_oriented_circles(
    image: np.ndarray,
    keypoints: np.ndarray,
    circle_radius: int = 5,
    line_length: int = 8,
    show_orientation: bool = False,
    max_features: int = None,
) -> np.ndarray:
    """
    Draw circles at keypoint locations, optionally with orientation lines.

    Args:
        image: Input image
        keypoints: Array of shape (num_keypoints, 6)
        circle_radius: Radius of circle in pixels
        line_length: Length of orientation line in pixels
        show_orientation: Whether to draw orientation lines
        max_features: If set, draw only the N strongest features (sorted by column 2)

    Returns:
        Annotated image
    """
    annotated = image.copy()
    h, w = image.shape[:2]

    # Color for circles
    circle_color = (0, 255, 0)  # Green
    line_color = (255, 0, 0)    # Blue

    # Filter to strongest features if requested
    kps_to_draw = keypoints
    if max_features is not None and len(keypoints) > max_features:
        # Sort by column 2 (assumed to be response/strength) in descending order
        sorted_indices = np.argsort(-keypoints[:, 2])[:max_features]
        kps_to_draw = keypoints[sorted_indices]

    for idx, kp in enumerate(kps_to_draw):
        x, y = kp[0], kp[1]

        # Skip if outside image bounds
        if x < 0 or y < 0 or x >= w or y >= h:
            continue

        x_int, y_int = int(round(x)), int(round(y))

        # Draw circle
        cv2.circle(
            annotated,
            (x_int, y_int),
            circle_radius,
            circle_color,
            thickness=2
        )

        # Optionally draw orientation line
        if show_orientation:
            # Use column 5 as angle (in radians)
            angle = kp[5] if len(kp) > 5 else 0

            # Draw orientation line from center outward
            end_x = int(x_int + line_length * np.cos(angle))
            end_y = int(y_int + line_length * np.sin(angle))
            cv2.line(
                annotated,
                (x_int, y_int),
                (end_x, end_y),
                line_color,
                thickness=2
            )

    return annotated


def main():
    parser = argparse.ArgumentParser(
        description="Visualize COLMAP SIFT features on images"
    )
    parser.add_argument(
        "--colmap-dir",
        type=Path,
        required=True,
        help="Path to COLMAP project directory (containing database.db and images/)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for annotated images"
    )
    parser.add_argument(
        "--circle-radius",
        type=int,
        default=5,
        help="Radius of circles around keypoints (pixels)"
    )
    parser.add_argument(
        "--line-length",
        type=int,
        default=8,
        help="Length of orientation line (pixels)"
    )
    parser.add_argument(
        "--show-orientation",
        action="store_true",
        default=False,
        help="Draw orientation lines on keypoints"
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=None,
        help="If set, draw only the N strongest features (sorted by response)"
    )

    args = parser.parse_args()

    db_path = args.colmap_dir / "database.db"
    images_dir = args.colmap_dir / "images"
    output_dir = args.output_dir

    # Validate inputs
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    if not images_dir.exists():
        print(f"Error: Images directory not found at {images_dir}")
        return 1

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Get list of images from database
    images = get_image_info(db_path)
    print(f"Found {len(images)} images in database")

    # Process each image
    for image_id, image_name in images:
        image_path = images_dir / image_name

        if not image_path.exists():
            print(f"  Warning: Image not found {image_path}, skipping")
            continue

        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"  Warning: Could not load image {image_path}, skipping")
            continue

        # Load keypoints from database
        keypoints = load_keypoints_from_db(db_path, image_id)
        num_to_draw = args.max_features if args.max_features else len(keypoints)

        print(
            f"  Image {image_id}: {image_name} "
            f"({image.shape[1]}x{image.shape[0]}) "
            f"with {len(keypoints)} keypoints ({num_to_draw} to draw)"
        )

        # Draw keypoints on image
        annotated = draw_oriented_circles(
            image,
            keypoints,
            circle_radius=args.circle_radius,
            line_length=args.line_length,
            show_orientation=args.show_orientation,
            max_features=args.max_features
        )

        # Save annotated image as JPEG
        output_path = output_dir / image_name.replace('.jpg', '_annotated.jpg')
        cv2.imwrite(str(output_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"    Saved: {output_path.name}")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())
