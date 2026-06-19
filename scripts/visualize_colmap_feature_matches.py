#!/usr/bin/env python3
"""
Visualize feature matches between image pairs from COLMAP.

For each matched pair of images in a COLMAP project, draws lines connecting
matched keypoints between the two images. Shows:
  - Features in left image with ID numbers (green circles)
  - Features in right image with ID numbers (cyan circles)
  - Lines connecting matched keypoints (colored by match ID)
  - Saves side-by-side comparison images

Usage:
  python scripts/visualize_feature_matches.py \
    --colmap-dir data/intermediates/test_4s \
    --output-dir data/intermediates/test_4s/match_visualizations
"""

import argparse
import sqlite3
from pathlib import Path
import numpy as np
import cv2


def load_keypoints_from_db(db_path: Path, image_id: int) -> np.ndarray:
    """
    Load keypoints for a specific image from COLMAP database.
    Returns array of shape (num_keypoints, 6).
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


def get_image_info(db_path: Path) -> dict:
    """Get mapping of image_id to image_name."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT image_id, name FROM images;")
    images = {img_id: name for img_id, name in cursor.fetchall()}
    conn.close()

    return images


def get_image_pairs_with_matches(db_path: Path) -> list:
    """
    Get all image pairs that have matches.
    COLMAP encodes pair_id as: pair_id = (image_id1 << 31) + (image_id2 - 1)
    Returns list of (image_id1, image_id2) tuples.
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT pair_id FROM matches ORDER BY pair_id;")
    pair_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Decode pair_ids
    pairs = []
    for pair_id in pair_ids:
        # Decode: pair_id = (image_id1 << 31) + (image_id2 - 1)
        image_id1 = pair_id >> 31
        image_id2 = (pair_id & 0x7FFFFFFF) + 1
        pairs.append((image_id1, image_id2))

    return pairs


def load_matches(db_path: Path, image_id1: int, image_id2: int) -> np.ndarray:
    """
    Load feature matches between two images.
    Returns array of shape (num_matches, 2) with columns [kp_idx1, kp_idx2].
    """
    # Encode pair_id
    pair_id = (image_id1 << 31) + (image_id2 - 1)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        "SELECT data FROM matches WHERE pair_id = ?",
        (pair_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return np.empty((0, 2), dtype=np.uint32)

    blob_data = row[0]
    matches = np.frombuffer(blob_data, dtype=np.uint32).reshape(-1, 2)
    return matches


def draw_match_lines(
    img1: np.ndarray,
    img2: np.ndarray,
    kp1: np.ndarray,
    kp2: np.ndarray,
    matches: np.ndarray,
    max_matches: int = None,
) -> np.ndarray:
    """
    Create side-by-side visualization of matched features.

    Args:
        img1: First image
        img2: Second image
        kp1: Keypoints in first image (array of shape (N, 6))
        kp2: Keypoints in second image (array of shape (M, 6))
        matches: Match indices (array of shape (num_matches, 2))
        max_matches: If set, select the strongest matches

    Returns:
        Side-by-side image with match lines drawn and bounding boxes
    """
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    h_max = max(h1, h2)

    # Create side-by-side canvas
    canvas = np.zeros((h_max, w1 + w2, 3), dtype=np.uint8)

    # Place images with partial transparency (blend with background)
    img_alpha = 0.5  # Images at 50% opacity
    canvas[0:h1, 0:w1] = cv2.addWeighted(img1, img_alpha, canvas[0:h1, 0:w1], 1 - img_alpha, 0)
    canvas[0:h2, w1:w1+w2] = cv2.addWeighted(img2, img_alpha, canvas[0:h2, w1:w1+w2], 1 - img_alpha, 0)

    # Colors for bounding boxes
    box_color1 = (255, 0, 0)         # Blue for first image box
    box_color2 = (0, 165, 255)       # Orange for second image box
    box_thickness = 10
    box_alpha = 0.5
    half_thickness = box_thickness // 2

    # Create overlay for transparent boxes
    # Offset by half thickness to ensure both box edges are visible where they touch
    overlay = canvas.copy()
    cv2.rectangle(overlay, (half_thickness, half_thickness), (w1 - 1 - half_thickness, h1 - 1 - half_thickness), box_color1, thickness=box_thickness)
    cv2.rectangle(overlay, (w1 + half_thickness, half_thickness), (w1 + w2 - 1 - half_thickness, h2 - 1 - half_thickness), box_color2, thickness=box_thickness)

    # Blend overlay with canvas for transparency
    cv2.addWeighted(overlay, box_alpha, canvas, 1 - box_alpha, 0, canvas)

    # Select strongest matches if requested
    matches_to_draw = matches
    if max_matches is not None and len(matches) > max_matches:
        # Score matches by the combined response strength of both keypoints
        match_strengths = []
        for idx1, idx2 in matches:
            if idx1 < len(kp1) and idx2 < len(kp2):
                # Column 2 contains the response strength
                strength = kp1[idx1][2] + kp2[idx2][2]
                match_strengths.append(strength)
            else:
                match_strengths.append(0)

        # Get indices of strongest matches
        match_strengths = np.array(match_strengths)
        strongest_indices = np.argsort(-match_strengths)[:max_matches]
        matches_to_draw = matches[strongest_indices]

    # Draw match lines with random colors and transparency
    line_alpha = 0.65
    for idx1, idx2 in matches_to_draw:
        if idx1 >= len(kp1) or idx2 >= len(kp2):
            continue

        x1, y1 = int(round(kp1[idx1][0])), int(round(kp1[idx1][1]))
        x2, y2 = int(round(kp2[idx2][0])), int(round(kp2[idx2][1]))

        # Check bounds
        if not (0 <= x1 < w1 and 0 <= y1 < h1):
            continue
        if not (0 <= x2 < w2 and 0 <= y2 < h2):
            continue

        # Generate random color for this match
        color = tuple(np.random.randint(0, 256, 3).tolist())

        # Create line overlay
        line_overlay = canvas.copy()
        cv2.line(line_overlay, (x1, y1), (w1 + x2, y2), color, thickness=5)

        # Blend line with canvas for transparency
        cv2.addWeighted(line_overlay, line_alpha, canvas, 1 - line_alpha, 0, canvas)

    return canvas


def main():
    parser = argparse.ArgumentParser(
        description="Visualize COLMAP feature matches between image pairs"
    )
    parser.add_argument(
        "--colmap-dir",
        type=Path,
        required=True,
        help="Path to COLMAP project directory"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for match visualizations"
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=None,
        help="Maximum number of image pairs to visualize (for testing)"
    )
    parser.add_argument(
        "--max-matches",
        type=int,
        default=5,
        help="Number of strongest matches to show per pair (default: 5)"
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

    # Get image info
    image_info = get_image_info(db_path)
    print(f"Found {len(image_info)} images in database")

    # Get image pairs with matches
    pairs = get_image_pairs_with_matches(db_path)
    print(f"Found {len(pairs)} image pairs with matches")

    if args.max_pairs:
        pairs = pairs[:args.max_pairs]
        print(f"Limiting to first {args.max_pairs} pairs")

    # Process each pair
    for pair_idx, (image_id1, image_id2) in enumerate(pairs):
        image_name1 = image_info[image_id1]
        image_name2 = image_info[image_id2]

        # Load images
        img1_path = images_dir / image_name1
        img2_path = images_dir / image_name2

        if not img1_path.exists() or not img2_path.exists():
            print(f"  Warning: Image files not found for pair {pair_idx}")
            continue

        img1 = cv2.imread(str(img1_path))
        img2 = cv2.imread(str(img2_path))

        if img1 is None or img2 is None:
            print(f"  Warning: Could not load images for pair {pair_idx}")
            continue

        # Load keypoints and matches
        kp1 = load_keypoints_from_db(db_path, image_id1)
        kp2 = load_keypoints_from_db(db_path, image_id2)
        matches = load_matches(db_path, image_id1, image_id2)

        print(
            f"  Pair {pair_idx}: {image_name1} <-> {image_name2} "
            f"({len(matches)} matches)"
        )

        # Draw visualization
        canvas = draw_match_lines(img1, img2, kp1, kp2, matches, max_matches=args.max_matches)

        # Save result
        output_name = f"match_{pair_idx:04d}_{image_id1:02d}-{image_id2:02d}.jpg"
        output_path = output_dir / output_name
        cv2.imwrite(str(output_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"    Saved: {output_name}")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())
