"""Entry point for the incident analysis pipeline."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from src import classifier, config, csv_writer, detector, ocr, utils
from src.merge_ready_image_output import create_merge_ready_image_output

logger = logging.getLogger(__name__)


def format_objects(objects: list[tuple[str, float]]) -> str:
    """Format detected object names for CSV output."""
    return "; ".join(name for name, _ in objects)


def process_image_file(
    image_path: Path,
    id_generator: utils.ImageIdGenerator,
    csv_path: Path,
) -> bool:
    """Analyze one image and append a row to the incidents CSV.

    Returns True when a row was written, False when the image was skipped.
    """
    if not utils.is_supported_image(image_path):
        supported = ", ".join(sorted(config.SUPPORTED_IMAGE_EXTENSIONS))
        logger.warning(
            "Skipping '%s': unsupported format '%s'. Supported formats: %s",
            image_path.name,
            image_path.suffix,
            supported,
        )
        return False

    try:
        image = utils.process_image(image_path)
    except utils.ImageLoadError as exc:
        logger.warning("Skipping '%s': %s", image_path.name, exc)
        return False

    try:
        objects_with_confidence, confidence_score = (
            detector.detect_objects_with_confidence(image)
        )
    except detector.ModelError as exc:
        logger.warning("Skipping '%s': %s", image_path.name, exc)
        return False

    scene_type = classifier.classify_scene(
        [name for name, _ in objects_with_confidence]
    )
    text_extracted = ocr.extract_text(image)
    try:
        image_id = id_generator.next_id()
    except utils.ImageIdExhaustedError as exc:
        logger.warning("Skipping '%s': %s", image_path.name, exc)
        return False

    csv_writer.write_row(
        csv_path,
        image_id=image_id,
        scene_type=scene_type,
        objects_detected=format_objects(objects_with_confidence),
        text_extracted=text_extracted,
        confidence_score=confidence_score,
    )
    logger.debug(
        "Processed '%s' as %s (%s)",
        image_path.name,
        image_id,
        scene_type,
    )
    return True


def _count_csv_rows(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def process_batch(
    images_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Process every file in the input directory."""
    images_dir = images_dir or config.IMAGES_DIR
    output_dir = output_dir or config.OUTPUT_DIR
    csv_path = output_dir / config.CSV_FILENAME
    id_generator = utils.ImageIdGenerator()

    for image_path in utils.list_input_files(images_dir):
        process_image_file(image_path, id_generator, csv_path)

    return csv_path


def main() -> None:
    """Run the incident analysis application."""
    config.configure_logging()
    logger.info("Incident Analysis Module")
    ocr.check_tesseract_available()
    logger.info("Input directory: %s", config.IMAGES_DIR)
    logger.info("Output directory: %s", config.OUTPUT_DIR)

    csv_path = process_batch()
    processed_count = _count_csv_rows(csv_path)
    logger.info("Processed %s image(s)", processed_count)
    logger.info("Output written to: %s", csv_path)

    if csv_path.exists():
        merge_ready_path = create_merge_ready_image_output(config.OUTPUT_DIR)
        logger.info("Merge-ready output written to: %s", merge_ready_path)


if __name__ == "__main__":
    main()
