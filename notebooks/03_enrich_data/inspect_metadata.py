#!/usr/bin/env python3
"""
Quick script to inspect metadata structure of enriched elements
"""

import pickle
from pathlib import Path
from pydantic import BaseModel
from typing import Literal, Optional

# Configuration
META_DATA_RUN_TO_LOAD = "run_20250721_085153"
DATA_BASE_DIR = "../../data/internal"
META_DATA_DIR = f"{DATA_BASE_DIR}/02_meta_data"


# Add the StructuralMetadata class for pickle compatibility
class StructuralMetadata(BaseModel):
    """Enhanced metadata focusing on high-impact, easy-to-implement fields"""

    source_filename: str
    page_number: int
    content_type: Literal["text", "table", "full_page_with_images"]
    page_context: str = "unknown"
    content_length: int = 0
    has_numbers: bool = False
    element_category: str = "unknown"
    has_tables_on_page: bool = False
    has_images_on_page: bool = False
    text_complexity: str = "medium"
    section_title_category: Optional[str] = None
    section_title_inherited: Optional[str] = None
    section_title_pattern: Optional[str] = None


def inspect_metadata():
    """Inspect the metadata structure of enriched elements"""

    # Load the pickle file
    pickle_path = Path(META_DATA_DIR) / META_DATA_RUN_TO_LOAD / "enriched_elements.pkl"

    print(f"🔍 INSPECTING METADATA STRUCTURE")
    print("=" * 50)
    print(f"📂 Loading from: {pickle_path}")

    if not pickle_path.exists():
        print(f"❌ File not found: {pickle_path}")
        return

    try:
        with open(pickle_path, "rb") as f:
            enriched_elements = pickle.load(f)

        print(f"✅ Loaded {len(enriched_elements)} enriched elements")

        # Inspect first few elements
        for i, element in enumerate(enriched_elements[:3]):
            print(f"\n📋 ELEMENT {i+1}:")
            print(f"   ID: {element.get('id', 'N/A')}")
            print(f"   Element type: {element.get('element_type', 'N/A')}")

            # Check structural metadata
            if "structural_metadata" in element:
                struct_meta = element["structural_metadata"]
                print(f"   📊 Structural metadata:")
                print(
                    f"      Content type: {getattr(struct_meta, 'content_type', 'N/A')}"
                )
                print(
                    f"      Page number: {getattr(struct_meta, 'page_number', 'N/A')}"
                )
                print(
                    f"      Source filename: {getattr(struct_meta, 'source_filename', 'N/A')}"
                )

            # Check original element
            if "original_element" in element:
                orig_element = element["original_element"]
                print(f"   🔍 Original element:")
                print(f"      Type: {type(orig_element)}")

                # Check if it has metadata
                if hasattr(orig_element, "metadata"):
                    metadata = orig_element.metadata
                    print(f"      Has metadata: True")
                    print(f"      Metadata type: {type(metadata)}")

                    # Try to get metadata as dict
                    if hasattr(metadata, "to_dict"):
                        metadata_dict = metadata.to_dict()
                        print(f"      📋 Metadata keys: {list(metadata_dict.keys())}")

                        # Show values for key fields
                        for key in ["image_path", "filepath", "text_as_html"]:
                            if key in metadata_dict:
                                value = metadata_dict[key]
                                print(f"      {key}: {value}")
                    else:
                        print(
                            f"      📋 Metadata keys: {list(metadata.keys()) if hasattr(metadata, 'keys') else 'Not a dict'}"
                        )
                else:
                    print(f"      Has metadata: False")

                # Check other attributes
                print(
                    f"      Available attributes: {[attr for attr in dir(orig_element) if not attr.startswith('_')]}"
                )

                # Try to get text
                if hasattr(orig_element, "text"):
                    text = getattr(orig_element, "text", "")
                    print(f"      Text length: {len(text)} chars")

            print("-" * 40)

        # Look specifically for image elements
        print(f"\n🖼️ LOOKING FOR IMAGE ELEMENTS:")
        print("=" * 30)

        image_elements = [
            el
            for el in enriched_elements
            if el.get("structural_metadata", {}).content_type == "full_page_with_images"
        ]
        print(f"📁 Found {len(image_elements)} image elements")

        for i, img_element in enumerate(image_elements[:2]):
            print(f"\n🖼️ IMAGE ELEMENT {i+1}:")
            struct_meta = img_element["structural_metadata"]
            print(f"   Page: {struct_meta.page_number}")
            print(f"   File: {struct_meta.source_filename}")

            orig_element = img_element["original_element"]
            print(f"   🔍 Original element type: {type(orig_element)}")

            if hasattr(orig_element, "metadata"):
                metadata = orig_element.metadata
                print(f"   📋 Metadata type: {type(metadata)}")

                if hasattr(metadata, "to_dict"):
                    metadata_dict = metadata.to_dict()
                    print(f"   📋 All metadata keys: {list(metadata_dict.keys())}")

                    # Show all metadata values
                    for key, value in metadata_dict.items():
                        print(f"   {key}: {value}")
                else:
                    print(
                        f"   📋 Metadata keys: {list(metadata.keys()) if hasattr(metadata, 'keys') else 'Not a dict'}"
                    )
            else:
                print(f"   ❌ No metadata found")

            # Check other attributes
            print(
                f"   🔍 Available attributes: {[attr for attr in dir(orig_element) if not attr.startswith('_')]}"
            )

            # Since it's a dict, show all keys and values
            print(f"   📋 Dictionary keys: {list(orig_element.keys())}")
            for key, value in orig_element.items():
                print(f"   {key}: {value}")

            # Try to get text
            if hasattr(orig_element, "text"):
                text = getattr(orig_element, "text", "")
                print(f"   📝 Text length: {len(text)} chars")
                if text:
                    print(f"   📝 Text preview: {text[:100]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    inspect_metadata()
