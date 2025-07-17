# --- Core Libraries ---
import os
import uuid
import base64
import io
import random
from dotenv import load_dotenv
from PIL import Image, ImageDraw

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
    content_type: Literal["text", "table", "image"]


print("✅ Pydantic models defined.")

# ==============================================================================
# 2. LOAD ENVIRONMENT & DEFINE CONFIGURATION
# ==============================================================================
load_dotenv()

# --- OpenRouter Configuration (for VLM/Chat) ---
VLM_MODEL = "anthropic/claude-3-5-sonnet"  # Valid OpenRouter model with vision support
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_HTTP_REFERER = "http://localhost"

# --- OpenAI Configuration (for Embeddings) ---
OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"  # 1536 dimensions, more stable

# --- Document and Language Configuration ---
PDF_SOURCE_DIR = "../documents/"
FILES_TO_PROCESS = ["sample_document.pdf"]
OCR_LANGUAGES = ["eng", "dan"]

# --- Database Configuration ---
DB_PATH = "../chroma_db"
COLLECTION_NAME = "project_docs"

# ==============================================================================
# 2. VERIFY KEYS & INITIALIZE CLIENTS
# ==============================================================================
if not os.getenv("OPENROUTER_API_KEY"):
    raise ValueError("OPENROUTER_API_KEY not found in .env file.")
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY not found in .env file for direct embedding access."
    )

# Initialize VLM client (pointing to OpenRouter)
vlm_model = ChatOpenAI(
    model=VLM_MODEL,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base=OPENROUTER_API_BASE,
    default_headers={"HTTP-Referer": OPENROUTER_HTTP_REFERER},
)

# Initialize Embedding client (pointing directly to OpenAI)
embedding_model = OpenAIEmbeddings(
    model=OPENAI_EMBEDDING_MODEL, openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Initialize ChromaDB Client
db_client = chromadb.PersistentClient(path=DB_PATH)

# Force delete and recreate collection to avoid dimension mismatches
try:
    db_client.delete_collection(name=COLLECTION_NAME)
    print(f"✅ Cleared existing collection '{COLLECTION_NAME}'")
except Exception as e:
    print(f"Note: Could not delete collection: {e}")

# Create fresh collection
collection = db_client.create_collection(name=COLLECTION_NAME)
print(f"✅ Created fresh collection '{COLLECTION_NAME}'")

# Verify the embedding model dimensions
test_embedding = embedding_model.embed_query("test")
print(
    f"✅ Embedding model '{OPENAI_EMBEDDING_MODEL}' produces {len(test_embedding)}-dimensional vectors"
)

print("✅ Configuration loaded and all clients initialized successfully.")
print("   - VLM Client: Using ChatOpenRouter")
print("   - Embedding Client: Using OpenAIEmbeddings (direct)")
print(
    f"Database collection '{COLLECTION_NAME}' is ready. It currently contains {collection.count()} items."
)

print("--- Step 2.A: Starting VLM Test ---")

# 1. Create a simple dummy image with text using the Pillow library
try:
    # Create a black image
    img = Image.new("RGB", (400, 100), color="black")
    d = ImageDraw.Draw(img)

    # Draw white text on it. If the VLM reads this, we know it's working.
    d.text(
        (10, 10), "TEST IMAGE\nThis is a test. System check 123.", fill=(255, 255, 255)
    )

    # Save the image to an in-memory buffer to get its bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    dummy_image_bytes = buffer.getvalue()
    print("Dummy image created successfully.")

    # 2. Initialize a specific VLM client for the test
    #    (This uses the VLM_MODEL constant from the cell above)
    vlm_test_model = ChatOpenAI(
        model=VLM_MODEL,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=OPENROUTER_API_BASE,
        default_headers={"HTTP-Referer": OPENROUTER_HTTP_REFERER},
    )

    # 3. Call the VLM with the dummy image
    print(f"Calling VLM with model ID: '{VLM_MODEL}'...")
    response_message = vlm_test_model.invoke(
        [
            HumanMessage(
                content=[
                    {"type": "text", "text": "What text do you see in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(dummy_image_bytes).decode('utf-8')}"
                        },
                    },
                ]
            )
        ]
    )

    # 4. Print the result
    print("\n✅ --- VLM TEST SUCCEEDED --- ✅")
    print("VLM Response:", response_message.content)

except Exception as e:
    print("\n❌ --- VLM TEST FAILED --- ❌")
    print("The following error occurred:")
    print(e)


# --- Configuration complete ---

# --- Partition 1 pdf ---

# Select the first PDF from our list to process
filepath = os.path.join(PDF_SOURCE_DIR, FILES_TO_PROCESS[0])

print(f"--- Step 1: Partitioning PDF: {os.path.basename(filepath)} ---")

# We use the robust `hi_res` strategy and provide our languages for OCR
raw_pdf_elements = partition_pdf(
    filename=filepath,
    strategy="hi_res",
    languages=OCR_LANGUAGES,
    extract_images_in_pdf=True,
)

print(f"\n--- Partitioning Complete ---")
print(f"Found {len(raw_pdf_elements)} raw elements in the document.")

# --- Count Elements by Category ---
category_counts = {}
for el in raw_pdf_elements:
    category = el.category
    category_counts[category] = category_counts.get(category, 0) + 1

print("\n--- Element Categories Found: ---")
for category, count in category_counts.items():
    print(f"  {category}: {count} elements")

# Highlight images specifically
image_count = category_counts.get("Image", 0)
print(f"\n📸 **Images found: {image_count}** (will be processed with VLM for captions)")

# --- Immediate Inspection ---
# Look at the first 5 elements to see what categories were identified
print("\n--- First 5 Elements Extracted: ---")
for i, el in enumerate(raw_pdf_elements[:5]):
    print(
        f"  Element {i+1}: Category='{el.category}', Text='{el.text[:80].strip().replace(chr(10), ' ')}...'"
    )


# -- Categorise, process & strcuture ---


# Helper function for VLM captioning
def get_image_caption(image_bytes: bytes, vlm: ChatOpenAI) -> str:
    print("  -> Calling VLM for image caption...")
    msg = vlm.invoke(
        [
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Describe this architectural or engineering image in detail. Focus on labels, dimensions, and diagram type.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                        },
                    },
                ]
            )
        ]
    )
    return msg.content


# --- Main Structuring Logic ---
print(f"--- Step 2: Structuring {len(raw_pdf_elements)} raw elements ---")
structured_data = []
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

for el in raw_pdf_elements:
    metadata_dict = el.metadata.to_dict()
    rich_meta = RichMetadata(
        source_filename=metadata_dict.get("filename", "Unknown"),
        page_number=metadata_dict.get("page_number", 1),
        content_type="text",
    )

    """
    if el.category == "Image":
        rich_meta.content_type = "image"

        # --- FINAL, CORRECT IMAGE HANDLING LOGIC ---
        # 1. Get the image path from the metadata dictionary.
        image_path = metadata_dict.get("image_path")

        # 2. Check if the path exists to avoid errors.
        if image_path and os.path.exists(image_path):
            try:
                # 3. Open the file in binary read mode ("rb").
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()

                # 4. Pass the bytes to the VLM for captioning.
                caption = get_image_caption(image_bytes, vlm_model)
                structured_data.append({"content": caption, "metadata": rich_meta})
            except Exception as e:
                print(
                    f"  -> Warning: Failed to process image at {image_path}. Error: {e}"
                )
        else:
            print(
                f"  -> Warning: Found an image element but its path '{image_path}' does not exist. Skipping."
            )
        # ---------------------------------------------
    """

    if el.category == "Table":
        rich_meta.content_type = "table"
        table_html = metadata_dict.get("text_as_html", el.text)
        structured_data.append({"content": table_html, "metadata": rich_meta})

    elif hasattr(el, "text") and el.text.strip():
        rich_meta.content_type = "text"
        chunks = text_splitter.split_text(el.text)
        for chunk in chunks:
            structured_data.append({"content": chunk, "metadata": rich_meta})

print(f"\n--- Structuring Complete ---")
print(
    f"Created {len(structured_data)} structured data chunks (text, tables, and image captions)."
)

# --- Immediate Inspection ---
print("\n--- Random Samples of Structured Data: ---")
if structured_data:
    for item in random.sample(structured_data, min(5, len(structured_data))):
        # We need to check if content exists before stripping
        content_snippet = (
            item["content"].strip()[:80] if item.get("content") else "[EMPTY CONTENT]"
        )
        print(
            f"  Type: {item['metadata'].content_type}, Page: {item['metadata'].page_number}, Content: '{content_snippet}'..."
        )
else:
    print("  No data was structured.")


# --- Generate embeddings ---
print(f"--- Step 3: Generating Embeddings for {len(structured_data)} chunks ---")

# Extract just the content to be embedded
contents_to_embed = [item["content"] for item in structured_data]

if contents_to_embed:
    embeddings = embedding_model.embed_documents(contents_to_embed)
    print(f"--- Embedding Complete ---")
    print(
        f"Successfully generated {len(embeddings)} embeddings, each with dimension {len(embeddings[0])}."
    )
else:
    embeddings = []
    print("--- Warning: No content was available to embed. ---")


# --- Store in ChromaDB ---
print(f"--- Step 4: Storing {len(structured_data)} chunks in ChromaDB ---")

if structured_data and embeddings:
    ids_to_add = [str(uuid.uuid4()) for _ in structured_data]
    metadatas_to_add = [item["metadata"].model_dump() for item in structured_data]

    # Add to the collection
    collection.add(
        ids=ids_to_add,
        embeddings=embeddings,
        documents=contents_to_embed,
        metadatas=metadatas_to_add,
    )

    print("--- Population Complete ---")
    print(f"Total items in collection '{COLLECTION_NAME}' is now: {collection.count()}")
else:
    print("--- Warning: No data was available to store in the database. ---")

# ==============================================================================
# 5. FINAL VERIFICATION
# ==============================================================================
print(f"--- Step 5: Verifying data in '{COLLECTION_NAME}' ---")

item_count = collection.count()
print(f"The collection contains {item_count} items.")

if item_count > 0:
    print("\nPerforming a test query for 'projektdokumentation'...")

    # Verify we're using the same embedding model for querying
    print(f"Using embedding model: {OPENAI_EMBEDDING_MODEL}")

    # Generate query embeddings using the SAME model used for storage
    query_embeddings = embedding_model.embed_documents(["projektdokumentation"])

    # Query using the explicit embeddings instead of query_texts
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(3, item_count),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],  # Include distances to see relevance
    )

    print("\n--- Top Query Results: ---")
    for i in range(len(results["ids"][0])):
        dist = results["distances"][0][i]
        meta = results["metadatas"][0][i]
        doc = results["documents"][0][i]
        print(f"  Result {i+1} (Distance: {dist:.4f}):")
        print(
            f"    Source: {meta.get('source_filename', 'N/A')}, Page: {meta.get('page_number', 'N/A')}"
        )
        print(f"    Content: '{doc[:250].strip()}'...")
        print("-" * 20)
