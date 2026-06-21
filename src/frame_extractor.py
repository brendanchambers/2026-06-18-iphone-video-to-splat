"""
Frame extraction utility for extracting frames from video files.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from omegaconf import DictConfig


logger = logging.getLogger(__name__)


def extract_frames(
    video_path: Path,
    output_dir: Path,
    fps: float = 2,
    quality: int = 2,
    config: Optional[DictConfig] = None,
    log_file: Optional[Path] = None,
) -> bool:
    """
    Extract frames from a video file at a constant framerate.

    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        fps: Frames per second (default: 2)
        quality: JPEG quality (1-5, where 2 is high quality)
        config: Optional OmegaConf config object
        log_file: Optional path to log file

    Returns:
        True if successful, False otherwise
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    # Validate inputs
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Extracting frames from: {video_path}")
        logger.info(f"Output directory: {output_dir}")

        # Use fps from config if provided, otherwise use parameter
        if config and hasattr(config, "frame_extraction") and hasattr(config.frame_extraction, "fps"):
            fps = config.frame_extraction.fps

        logger.info(f"Extracting frames at {fps} fps")

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", f"fps={fps}",
            "-q:v", str(quality),
            str(output_dir / "frame_%04d.jpg"),
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        # Run ffmpeg with output logging
        with open(log_file, "w") if log_file else None as log_fh:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            for line in process.stdout:
                logger.info(line.rstrip())
                if log_file:
                    log_fh.write(line)

            returncode = process.wait()

        if returncode != 0:
            logger.error(f"ffmpeg failed with return code {returncode}")
            return False

        # Count extracted frames
        frame_files = list(output_dir.glob("frame_*.jpg"))
        logger.info(f"Successfully extracted {len(frame_files)} frames")
        return True

    except Exception as e:
        logger.error(f"Error extracting frames: {e}")
        return False


if __name__ == "__main__":
    # Test with hardcoded paths
    logging.basicConfig(level=logging.INFO)
    video_path = Path("/Users/bc/brendanchambers/2026-06-18-iphone-video-to-splat/data/incoming/movies/gardenbed_2026-06-17.mov")
    output_dir = Path("/tmp/test_frames")
    log_file = Path("/tmp/frame_extraction.log")

    success = extract_frames(video_path, output_dir, log_file=log_file)
    print(f"Extraction successful: {success}")
