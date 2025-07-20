# --- Core Libraries ---
import os
import uuid
import base64
from dotenv import load_dotenv
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from pathlib import Path

# --- Pydantic for Data Structuring ---
from pydantic import BaseModel, Field
from typing import Literal, Optional

# --- PDF Parsing ---
from unstructured.partition.pdf import partition_pdf

# --- LangChain Components ---
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage

# --- Vector Database ---
import chromadb

# ==============================================================================
# 1. DEFINE DATA MODELS
# ==============================================================================


class RichMetadata(BaseModel):
    source_filename: str
    source_document_type: str = Field(default="Not Specified")
    page_number: int
    content_type: Literal["text", "table", "full_page_with_images"]
    # Enhanced fields for image-rich pages
    original_image_count: Optional[int] = None
    page_complexity: Optional[Literal["simple", "complex", "fragmented"]] = None
    extraction_method: Optional[str] = None
    image_filepath: Optional[str] = None


class VLMPageExtractor:
    """Extracts full pages for image-rich content with intelligent complexity detection"""

    def __init__(self, output_dir="vlm_pages", high_quality_dpi=300, standard_dpi=200):
        self.output_dir = Path(output_dir)
        self.high_quality_dpi = high_quality_dpi
        self.standard_dpi = standard_dpi
        self.output_dir.mkdir(exist_ok=True)

    def analyze_pdf_for_image_pages(self, pdf_path):
        """Analyze PDF structure to identify pages needing full-page extraction"""
        doc = fitz.open(pdf_path)
        page_analysis = {}

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images()

            # Detect fragmentation pattern
            is_fragmented = False
            if len(images) > 10:
                small_count = 0
                for img in images[:5]:  # Sample first 5 images
                    try:
                        base_image = doc.extract_image(img[0])
                        if base_image["width"] * base_image["height"] < 5000:
                            small_count += 1
                    except:
                        continue
                is_fragmented = small_count >= 3

            # Determine extraction strategy
            if len(images) == 0:
                complexity = "text_only"
                needs_full_page = False
            elif is_fragmented:
                complexity = "fragmented"
                needs_full_page = True
            elif len(images) >= 3:
                complexity = "complex"
                needs_full_page = True
            else:
                complexity = "simple"
                needs_full_page = False

            page_analysis[page_num + 1] = {
                "image_count": len(images),
                "complexity": complexity,
                "needs_full_page_extraction": needs_full_page,
                "is_fragmented": is_fragmented,
            }

        doc.close()
        return page_analysis

    def extract_image_rich_pages(self, pdf_path, page_analysis):
        """Extract full pages as high-quality images for VLM processing"""
        pages_to_extract = {
            page_num: info
            for page_num, info in page_analysis.items()
            if info["needs_full_page_extraction"]
        }

        if not pages_to_extract:
            return {}

        extracted_pages = {}
        pdf_basename = Path(pdf_path).stem

        print(f"📄 Extracting {len(pages_to_extract)} image-rich pages...")

        for page_num, info in pages_to_extract.items():
            try:
                # Use high DPI for fragmented pages, standard for complex
                dpi = (
                    self.high_quality_dpi
                    if info["is_fragmented"]
                    else self.standard_dpi
                )

                page_images = convert_from_path(
                    pdf_path, first_page=page_num, last_page=page_num, dpi=dpi
                )

                if page_images:
                    filename = (
                        f"{pdf_basename}_page{page_num:02d}_{info['complexity']}.png"
                    )
                    filepath = self.output_dir / filename
                    page_images[0].save(filepath, "PNG", optimize=False)

                    extracted_pages[page_num] = {
                        "filepath": str(filepath),
                        "filename": filename,
                        "width": page_images[0].width,
                        "height": page_images[0].height,
                        "dpi": dpi,
                        "complexity": info["complexity"],
                        "original_image_count": info["image_count"],
                    }

                    print(f"  ✅ Page {page_num}: {filename} ({info['complexity']})")

            except Exception as e:
                print(f"  ❌ Page {page_num}: Error - {e}")

        return extracted_pages


def get_vlm_caption(image_path: str, vlm: ChatOpenAI, page_metadata: dict) -> str:
    """Generate context-aware VLM captions based on page complexity"""

    with open(image_path, "rb") as img_file:
        image_bytes = img_file.read()

    # Create context-aware prompts
    complexity = page_metadata.get("complexity", "unknown")
    original_count = page_metadata.get("original_image_count", 0)

    if complexity == "fragmented":
        prompt = f"""This page contains a technical drawing or blueprint reconstructed from {original_count} image fragments. 

Provide a comprehensive description focusing on:
- Technical specifications, measurements, and dimensions
- Architectural or engineering details and symbols
- Text labels, annotations, legends, and callouts
- Spatial relationships and layout structure
- Overall purpose and type of technical drawing
- Any visible standards, codes, or compliance information"""

    elif complexity == "complex":
        prompt = f"""This page contains {original_count} images with mixed content including text and annotations.

Describe in detail:
- Each distinct visual element and diagram
- Text overlays, labels, and annotations on images
- How images relate to each other and surrounding text
- Technical details, measurements, or specifications
- Tables, charts, or data visualizations
- Overall context and purpose of the visual content"""

    else:
        prompt = """Describe this technical/architectural content comprehensively, including:
- All visible text, labels, annotations, and measurements
- Technical specifications and engineering details
- Diagrams, charts, tables, and visual elements
- Purpose and context of the content"""

    print(f"  🤖 Generating VLM caption for {complexity} page...")

    msg = vlm.invoke(
        [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                        },
                    },
                ]
            )
        ]
    )

    return msg.content


print("✅ Enhanced data models and VLM extractor defined.")

# ==============================================================================
# 2. LOAD ENVIRONMENT & INITIALIZE CLIENTS
# ==============================================================================
load_dotenv()

# --- Configuration ---
VLM_MODEL = "anthropic/claude-3-5-sonnet"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_HTTP_REFERER = "http://localhost"
OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"

PDF_SOURCE_DIR = "../../data/external/construction_pdfs"
FILES_TO_PROCESS = ["test-with-little-variety.pdf"]  # Updated to your test file
OCR_LANGUAGES = ["eng", "dan"]

DB_PATH = "../chroma_db"
COLLECTION_NAME = "project_docs"

# --- Verify API Keys ---
if not os.getenv("OPENROUTER_API_KEY"):
    raise ValueError("OPENROUTER_API_KEY not found in .env file.")
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in .env file.")

# --- Initialize Clients ---
vlm_model = ChatOpenAI(
    model=VLM_MODEL,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base=OPENROUTER_API_BASE,
    default_headers={"HTTP-Referer": OPENROUTER_HTTP_REFERER},
)

embedding_model = OpenAIEmbeddings(
    model=OPENAI_EMBEDDING_MODEL, openai_api_key=os.getenv("OPENAI_API_KEY")
)

# --- Initialize ChromaDB ---
db_client = chromadb.PersistentClient(path=DB_PATH)

try:
    db_client.delete_collection(name=COLLECTION_NAME)
    print(f"✅ Cleared existing collection '{COLLECTION_NAME}'")
except Exception as e:
    print(f"Note: Could not delete collection: {e}")

collection = db_client.create_collection(name=COLLECTION_NAME)
print(f"✅ Created fresh collection '{COLLECTION_NAME}'")

# Verify embedding dimensions
test_embedding = embedding_model.embed_query("test")
print(f"✅ Embedding model produces {len(test_embedding)}-dimensional vectors")

print("✅ All clients initialized successfully.")

# ==============================================================================
# 3. HYBRID PROCESSING PIPELINE
# ==============================================================================

filepath = os.path.join(PDF_SOURCE_DIR, FILES_TO_PROCESS[0])
print(f"\n🔄 Processing: {os.path.basename(filepath)}")

# --- Step 1: Quick Analysis with PyMuPDF ---
print("📊 Step 1: Analyzing PDF structure for image content...")
page_extractor = VLMPageExtractor()
page_analysis = page_extractor.analyze_pdf_for_image_pages(filepath)

print("📋 Page Analysis Results:")
for page_num, info in page_analysis.items():
    status = (
        f"🖼️  IMAGE-RICH" if info["needs_full_page_extraction"] else "📝 text-focused"
    )
    print(
        f"  Page {page_num}: {status} ({info['complexity']}) - {info['image_count']} images"
    )

# --- Step 2: Extract Image-Rich Pages ---
extracted_pages = page_extractor.extract_image_rich_pages(filepath, page_analysis)

# --- Step 3: Unstructured Processing (No Image Extraction) ---
print(f"\n📄 Step 2: Unstructured processing for text/tables...")
raw_pdf_elements = partition_pdf(
    filename=filepath,
    strategy="hi_res",
    languages=OCR_LANGUAGES,
    extract_images_in_pdf=False,  # We handle images separately!
)

print(f"✅ Found {len(raw_pdf_elements)} text/table elements")

# At the end of your partitioning notebook:
import pickle

data_to_save = {
    "raw_elements": raw_pdf_elements,
    "extracted_pages": extracted_pages,
    "page_analysis": page_analysis,
    "filepath": filepath,
}

with open("processed_elements.pkl", "wb") as f:
    pickle.dump(data_to_save, f)

print("✅ Saved processed elements for structural analysis")

# --- Step 4: Intelligent Content Structuring ---
print(f"\n🧠 Step 3: Structuring content with VLM integration...")
structured_data = []
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
processed_image_pages = set()

# Process image-rich pages with VLM
for page_num, page_info in extracted_pages.items():
    try:
        # Generate VLM caption
        caption = get_vlm_caption(page_info["filepath"], vlm_model, page_info)

        # Create rich metadata
        rich_meta = RichMetadata(
            source_filename=Path(filepath).name,
            page_number=page_num,
            content_type="full_page_with_images",
            original_image_count=page_info["original_image_count"],
            page_complexity=page_info["complexity"],
            extraction_method="vlm_full_page",
            image_filepath=page_info["filepath"],
        )

        # Create comprehensive content
        content = f"PAGE {page_num} VISUAL CONTENT ({page_info['complexity']} layout):\n{caption}"

        structured_data.append({"content": content, "metadata": rich_meta})
        processed_image_pages.add(page_num)

        print(f"  ✅ VLM processed page {page_num}")

    except Exception as e:
        print(f"  ❌ VLM failed for page {page_num}: {e}")

# Process text/table content from unstructured (skip image pages)
for el in raw_pdf_elements:
    metadata_dict = el.metadata.to_dict()
    page_num = metadata_dict.get("page_number", 1)

    # Skip pages already processed with VLM
    if page_num in processed_image_pages:
        continue

    rich_meta = RichMetadata(
        source_filename=metadata_dict.get("filename", "Unknown"),
        page_number=page_num,
        content_type="text",
    )

    if el.category == "Table":
        rich_meta.content_type = "table"
        table_html = metadata_dict.get("text_as_html", el.text)
        structured_data.append({"content": table_html, "metadata": rich_meta})

    elif hasattr(el, "text") and el.text.strip():
        chunks = text_splitter.split_text(el.text)
        for chunk in chunks:
            structured_data.append({"content": chunk, "metadata": rich_meta})

print(f"\n📊 Processing Summary:")
print(f"  Total pages: {len(page_analysis)}")
print(f"  Image-rich pages (VLM): {len(extracted_pages)}")
print(f"  Structured chunks: {len(structured_data)}")

# ==============================================================================
# 4. GENERATE EMBEDDINGS & STORE
# ==============================================================================

print(f"\n🔗 Step 4: Generating embeddings for {len(structured_data)} chunks...")

contents_to_embed = [item["content"] for item in structured_data]

if contents_to_embed:
    embeddings = embedding_model.embed_documents(contents_to_embed)
    print(f"✅ Generated {len(embeddings)} embeddings")
else:
    embeddings = []
    print("❌ No content to embed")

# --- Store in ChromaDB ---
print(f"💾 Step 5: Storing in ChromaDB...")

if structured_data and embeddings:
    ids_to_add = [str(uuid.uuid4()) for _ in structured_data]
    metadatas_to_add = [item["metadata"].model_dump() for item in structured_data]

    collection.add(
        ids=ids_to_add,
        embeddings=embeddings,
        documents=contents_to_embed,
        metadatas=metadatas_to_add,
    )

    print(f"✅ Stored {len(structured_data)} chunks in '{COLLECTION_NAME}'")
    print(f"📊 Collection now contains: {collection.count()} total items")
else:
    print("❌ No data to store")

# ==============================================================================
# 5. VERIFICATION
# ==============================================================================

print(f"\n🔍 Step 6: Verification with test query...")

if collection.count() > 0:
    # Test query for technical content
    query_embeddings = embedding_model.embed_documents(["technical drawing floor plan"])

    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(3, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    print(f"\n📋 Top Results for 'technical drawing floor plan':")
    for i in range(len(results["ids"][0])):
        dist = results["distances"][0][i]
        meta = results["metadatas"][0][i]
        doc = results["documents"][0][i]

        print(f"\n  Result {i+1} (Distance: {dist:.4f}):")
        print(
            f"    📄 Source: {meta.get('source_filename')} | Page: {meta.get('page_number')}"
        )
        print(
            f"    📝 Type: {meta.get('content_type')} | Complexity: {meta.get('page_complexity')}"
        )
        if meta.get("image_filepath"):
            print(f"    🖼️  Image: {Path(meta.get('image_filepath')).name}")
        print(f"    📖 Content: {doc[:200]}...")
        print("    " + "-" * 50)

print(f"\n🎉 Hybrid VLM + Unstructured pipeline complete!")
print(f"   📊 Successfully processed {len(page_analysis)} pages")
print(f"   🖼️  VLM analyzed {len(extracted_pages)} image-rich pages")
print(f"   💾 Stored {collection.count()} searchable chunks")
