import os
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import json
from pathlib import Path
import time

# Configuration
PDF_SOURCE_DIR = "../../documents/"
TEST_FILE = "test-with-little-variety.pdf"
FILEPATH = os.path.join(PDF_SOURCE_DIR, TEST_FILE)


class VLMOptimizedExtractor:
    def __init__(
        self,
        output_dir="vlm_ready_pages",
        high_quality_dpi=300,
        standard_dpi=200,
        min_images_threshold=1,
    ):
        """
        Simple extractor optimized for VLM processing

        Args:
            output_dir: Where to save extracted pages
            high_quality_dpi: DPI for complex pages (fragmented images)
            standard_dpi: DPI for standard pages
            min_images_threshold: Minimum images to consider a page worth extracting
        """
        self.output_dir = Path(output_dir)
        self.high_quality_dpi = high_quality_dpi
        self.standard_dpi = standard_dpi
        self.min_images_threshold = min_images_threshold

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

    def analyze_pages_for_images(self, pdf_path):
        """Quick analysis to identify which pages have images"""
        doc = fitz.open(pdf_path)

        page_analysis = {}

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images()

            # Quick fragmentation detection
            is_fragmented = False
            if len(images) > 10:
                # Sample a few images to check if they're small fragments
                small_count = 0
                for img in images[:5]:
                    try:
                        base_image = doc.extract_image(img[0])
                        if base_image["width"] * base_image["height"] < 5000:
                            small_count += 1
                    except:
                        continue

                is_fragmented = small_count >= 3

            page_analysis[page_num + 1] = {
                "has_images": len(images) >= self.min_images_threshold,
                "image_count": len(images),
                "is_fragmented": is_fragmented,
                "extraction_priority": (
                    "high"
                    if is_fragmented
                    else "standard" if len(images) > 0 else "skip"
                ),
            }

        doc.close()
        return page_analysis

    def extract_pages_with_images(self, pdf_path, page_analysis=None):
        """Extract full pages that contain images, optimized for VLM processing"""

        if page_analysis is None:
            page_analysis = self.analyze_pages_for_images(pdf_path)

        # Get pages that need extraction
        pages_to_extract = {
            page_num: info
            for page_num, info in page_analysis.items()
            if info["has_images"]
        }

        if not pages_to_extract:
            print("No pages with images found!")
            return {}

        extraction_results = {}

        print(f"Extracting {len(pages_to_extract)} pages with images...")

        for page_num, info in pages_to_extract.items():
            print(f"\nPage {page_num}: {info['image_count']} images detected")

            # Choose DPI based on complexity
            dpi = self.high_quality_dpi if info["is_fragmented"] else self.standard_dpi

            print(
                f"  Using {'high' if info['is_fragmented'] else 'standard'} quality extraction (DPI: {dpi})"
            )

            try:
                # Extract this specific page
                page_images = convert_from_path(
                    pdf_path, first_page=page_num, last_page=page_num, dpi=dpi
                )

                if page_images:
                    # Create descriptive filename
                    complexity = "complex" if info["is_fragmented"] else "standard"
                    filename = f"page_{page_num:02d}_{complexity}_{info['image_count']}imgs.png"
                    filepath = self.output_dir / filename

                    # Save with high quality
                    page_images[0].save(
                        filepath, "PNG", optimize=False, compress_level=1
                    )

                    extraction_results[page_num] = {
                        "filename": filename,
                        "width": page_images[0].width,
                        "height": page_images[0].height,
                        "dpi": dpi,
                        "original_image_count": info["image_count"],
                        "complexity": complexity,
                        "file_size_mb": filepath.stat().st_size / (1024 * 1024),
                    }

                    print(f"  ✅ Saved: {filename}")
                    print(f"     Size: {page_images[0].width}x{page_images[0].height}")
                    print(
                        f"     File: {extraction_results[page_num]['file_size_mb']:.1f} MB"
                    )

            except Exception as e:
                print(f"  ❌ Error extracting page {page_num}: {e}")
                extraction_results[page_num] = {"error": str(e)}

        return extraction_results

    def create_vlm_metadata(self, pdf_path, extraction_results):
        """Create metadata file for VLM processing"""

        metadata = {
            "source_pdf": os.path.basename(pdf_path),
            "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_pages_with_images": len(extraction_results),
            "pages": {},
        }

        for page_num, result in extraction_results.items():
            if "error" not in result:
                metadata["pages"][page_num] = {
                    "filename": result["filename"],
                    "dimensions": f"{result['width']}x{result['height']}",
                    "quality": result["complexity"],
                    "original_image_count": result["original_image_count"],
                    "vlm_prompt_suggestion": self._generate_vlm_prompt_suggestion(
                        result
                    ),
                }

        # Save metadata
        metadata_path = self.output_dir / f"{Path(pdf_path).stem}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"\n📋 Metadata saved: {metadata_path}")
        return metadata

    def _generate_vlm_prompt_suggestion(self, result):
        """Generate suggested prompts for VLM processing based on page complexity"""

        if result["complexity"] == "complex":
            return {
                "focus": "technical_drawing",
                "suggested_prompt": "This page contains a technical drawing or blueprint. Focus on the main diagram and any technical specifications, measurements, or annotations. Describe the technical content, including any visible text, symbols, measurements, and the overall purpose of the drawing.",
                "context": f"Page contains {result['original_image_count']} image fragments that have been reconstructed into one complete view.",
            }
        else:
            return {
                "focus": "mixed_content",
                "suggested_prompt": f"This page contains {result['original_image_count']} image(s) along with text. Focus on describing the visual content while noting any text annotations or labels that appear over or near the images. Describe how the images relate to the surrounding text content.",
                "context": "Page has clear image boundaries with potential text overlays or annotations.",
            }

    def print_summary(self, extraction_results, metadata):
        """Print a nice summary of the extraction"""
        print("\n" + "=" * 60)
        print("VLM-READY EXTRACTION SUMMARY")
        print("=" * 60)

        successful_extractions = {
            k: v for k, v in extraction_results.items() if "error" not in v
        }

        if successful_extractions:
            print(f"✅ Successfully extracted: {len(successful_extractions)} pages")
            print(f"📁 Output directory: {self.output_dir}")
            print(
                f"📋 Metadata file: {metadata['source_pdf'].replace('.pdf', '_metadata.json')}"
            )

            total_size = sum(
                result["file_size_mb"] for result in successful_extractions.values()
            )
            print(f"💾 Total size: {total_size:.1f} MB")

            print(f"\n📄 Extracted pages:")
            for page_num in sorted(successful_extractions.keys()):
                result = successful_extractions[page_num]
                print(
                    f"  Page {page_num:2d}: {result['filename']} ({result['complexity']} quality)"
                )

            print(f"\n🤖 Ready for VLM processing!")
            print(f"   Each page is saved as a complete image with context preserved.")
            print(f"   Use the metadata file for suggested VLM prompts.")

        errors = {k: v for k, v in extraction_results.items() if "error" in v}
        if errors:
            print(f"\n❌ Errors: {len(errors)} pages failed")
            for page_num, error_info in errors.items():
                print(f"  Page {page_num}: {error_info['error']}")


# Run the VLM-optimized extraction
print("Starting VLM-optimized extraction...")

if os.path.exists(FILEPATH):
    extractor = VLMOptimizedExtractor()

    # Step 1: Analyze which pages have images
    print("Analyzing pages for image content...")
    page_analysis = extractor.analyze_pages_for_images(FILEPATH)

    print(f"\nPage analysis:")
    for page_num, info in page_analysis.items():
        status = "📊 HAS IMAGES" if info["has_images"] else "📄 text only"
        quality = (
            f"({info['extraction_priority']} priority)" if info["has_images"] else ""
        )
        print(f"  Page {page_num}: {status} {quality} - {info['image_count']} images")

    # Step 2: Extract pages with images
    extraction_results = extractor.extract_pages_with_images(FILEPATH, page_analysis)

    # Step 3: Create VLM metadata
    metadata = extractor.create_vlm_metadata(FILEPATH, extraction_results)

    # Step 4: Print summary
    extractor.print_summary(extraction_results, metadata)

else:
    print(f"File not found: {FILEPATH}")
