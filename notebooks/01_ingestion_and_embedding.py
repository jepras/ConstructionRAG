# Notebook 1: Ingestion and Embedding
"""
**Purpose:** This notebook establishes the complete data ingestion pipeline. It takes raw PDF documents, parses them into text, tables, and images, generates rich descriptions for images using a Vision-Language Model (VLM), structures the data, creates embeddings, and stores everything in a ChromaDB vector store.

**Outcome:** A populated vector database (`./chroma_db`) and a reusable Python function for the ingestion process.
"""
# --- Core Libraries ---
import os
import uuid
import base64
import io
from dotenv import load_dotenv

# --- Pydantic for Data Structuring ---
from pydantic import BaseModel, Field
from typing import Literal, Optional

# --- PDF Parsing ---
from unstructured.partition.pdf import partition_pdf

# --- LangChain Components ---
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # This import works for both
from langchain_core.messages import HumanMessage

# --- Vector Database ---
import chromadb

# ==============================================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==============================================================================
load_dotenv()

# ==============================================================================
# 2. DEFINE CONFIGURATION CONSTANTS
# ==============================================================================
# --- OpenRouter Configuration (for VLM/Chat) ---
VLM_MODEL = "haotian-liu/llava-13b"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_HTTP_REFERER = "http://localhost"

# --- OpenAI Configuration (for Embeddings) ---
# We will use OpenAI's latest small embedding model directly.
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# --- Path and Naming Configuration ---
PDF_SOURCE_DIR = "../documents/"
FILES_TO_PROCESS = ["sample_document.pdf"]
DB_PATH = "../chroma_db"
COLLECTION_NAME = "project_docs"

# ==============================================================================
# 3. VERIFY CONFIGURATION
# ==============================================================================
if not os.getenv("OPENROUTER_API_KEY"):
    raise ValueError("OPENROUTER_API_KEY not found in .env file.")
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY not found in .env file for direct embedding access."
    )

print("✅ Configuration loaded successfully.")

# --- Set data structures ---


class RichMetadata(BaseModel):
    source_filename: str
    source_document_type: str = Field(default="Not Specified")
    page_number: int
    content_type: Literal["text", "table", "image"]
    section_title: Optional[str] = None


class DocumentChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str  # This will hold the text chunk or the image caption
    embedding: list[float]
    metadata: RichMetadata


print("Pydantic models defined.")

# --- core processing functions ---


# CORRECTED Cell 4


def get_image_caption(image_bytes: bytes, vlm_model: ChatOpenAI) -> str:
    """Generates a detailed caption for an image using a VLM via a LangChain ChatModel."""
    print("  -> Generating image caption...")
    try:
        # Create the message payload for the VLM
        msg = vlm_model.invoke(
            [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Describe this image from an architectural or engineering document in detail. Focus on quantifiable elements, labels, and the type of diagram (e.g., floor plan, elevation, schematic). Transcribe any visible text.",
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
        caption = msg.content
        print("  -> Caption generated successfully.")
        return caption
    except Exception as e:
        print(f"  -> Error generating image caption: {e}")
        return "Error generating image description."


def process_pdf_elements(
    filepath: str, vlm_model: ChatOpenAI
) -> list[tuple[str, dict]]:
    """
    Parses a PDF using unstructured, processes elements, and returns a list of (content, metadata) tuples.
    This version includes extensive debugging print statements.
    """
    print(f"--- [DEBUG] Starting to process: {os.path.basename(filepath)} ---")

    # Let's simplify the call first to remove potential issues with complex parameters.
    # This is a key debugging step.
    print("[DEBUG] Calling partition_pdf with a simplified 'hi_res' strategy...")
    try:
        elements = partition_pdf(
            filename=filepath,
            strategy="hi_res",
            languages=["eng", "dan"],
            # For debugging, we are temporarily removing extra parameters like
            # image_output_dir_path, chunking_strategy, etc.
            # We want to see if the core function returns anything at all.
            extract_images_in_pdf=True,
        )
    except Exception as e:
        print(f"[DEBUG] CRITICAL ERROR during partition_pdf: {e}")
        return []  # Return empty list if partitioning fails

    print(f"[DEBUG] partition_pdf finished. Found {len(elements)} raw elements.")
    if not elements:
        print(
            "[DEBUG] WARNING: No elements were extracted from the PDF. The document might be empty, corrupted, or incompatible."
        )

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    processed_data = []

    # Loop through the raw elements and print what we find
    for i, el in enumerate(elements):
        print(f"\n[DEBUG] --- Element {i+1}/{len(elements)} ---")
        print(f"[DEBUG] Element Category: {el.category}")
        print(f"[DEBUG] Element Text Snippet: {el.text[:100].strip()}...")
        # print(f"[DEBUG] Element Metadata: {el.metadata.to_dict()}") # Uncomment for very verbose output

        metadata_dict = el.metadata.to_dict()
        filename = metadata_dict.get("filename", "Unknown")
        page_number = metadata_dict.get("page_number", 1)

        rich_meta = RichMetadata(
            source_filename=filename,
            page_number=page_number,
            content_type="text",  # Default
        )

        # We will keep the robust logic from before, but the prints will tell us if we even get here.
        if el.category == "Image":
            print("[DEBUG] Processing as Image element.")
            # The logic to get image_bytes might still be tricky.
            # For now, let's just confirm we identified an image.
            # In a future step, we can re-add the file-based logic if this works.
            # For now, let's just create a placeholder caption.
            caption = f"Placeholder caption for image on page {page_number}"
            rich_meta.content_type = "image"
            processed_data.append((caption, rich_meta.model_dump()))

        elif el.category == "Table":
            print("[DEBUG] Processing as Table element.")
            rich_meta.content_type = "table"
            table_text = metadata_dict.get("text_as_html") or el.text
            processed_data.append((table_text, rich_meta.model_dump()))

        elif el.category in ["Title", "NarrativeText", "ListItem"]:
            print("[DEBUG] Processing as Text element.")
            rich_meta.content_type = "text"
            chunks = text_splitter.split_text(el.text)
            for chunk in chunks:
                processed_data.append((chunk, rich_meta.model_dump()))
        else:
            print(f"[DEBUG] Skipping element of unhandled category: {el.category}")

    print(
        f"\n--- [DEBUG] Finished element loop. Total processed data items: {len(processed_data)} ---"
    )
    return processed_data


# --- Ingest into ChromaDB ---
def ingest_documents(file_paths: list[str], collection: chromadb.Collection):
    """
    Orchestrates the full ingestion pipeline.
    - VLM for images is handled by OpenRouter.
    - Embeddings are handled by OpenAI's official API.
    """
    print("Initializing clients for ingestion...")

    # 1. Initialize VLM client pointing to OpenRouter
    vlm_model = ChatOpenAI(
        model=VLM_MODEL,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=OPENROUTER_API_BASE,
        default_headers={"HTTP-Referer": OPENROUTER_HTTP_REFERER},
    )

    # 2. Initialize Embedding client pointing directly to OpenAI
    #    By NOT providing openai_api_base, it defaults to OpenAI's servers.
    embedding_model = OpenAIEmbeddings(
        model=OPENAI_EMBEDDING_MODEL,
        openai_api_key=os.getenv("OPENAI_API_KEY"),  # Uses the direct OpenAI key
    )

    all_chunks = []
    for filepath in file_paths:
        processed_data = process_pdf_elements(filepath, vlm_model)
        all_chunks.extend(processed_data)

    if not all_chunks:
        print("No data processed. Aborting ingestion.")
        return

    print(f"\nEmbedding {len(all_chunks)} chunks using OpenAI's API...")

    contents = [item[0] for item in all_chunks]
    metadatas = [item[1] for item in all_chunks]

    embeddings = embedding_model.embed_documents(contents)

    ids = [str(uuid.uuid4()) for _ in all_chunks]

    print("Storing chunks in ChromaDB...")
    collection.add(
        ids=ids, embeddings=embeddings, documents=contents, metadatas=metadatas
    )
    print(
        f"Successfully ingested {collection.count()} documents into collection '{COLLECTION_NAME}'."
    )


# --- Execute ---

# ==============================================================================
# 4. EXECUTE THE INGESTION PIPELINE
# ==============================================================================
# This is the main execution block that brings everything together.

print("--- Starting Ingestion Process ---")

# Step 1: Initialize the ChromaDB Client
# This will create the database directory at DB_PATH if it doesn't exist,
# or connect to it if it already does. It's a file-based, persistent database.
print(f"Initializing database at: {DB_PATH}")
db_client = chromadb.PersistentClient(path=DB_PATH)

# Step 2: Get or Create the Collection
# A collection is like a table in a traditional database.
# This command is idempotent: it will create the collection if it's new,
# or simply connect to it if it already exists.
print(f"Accessing collection: {COLLECTION_NAME}")
collection = db_client.get_or_create_collection(name=COLLECTION_NAME)

# Step 3: Construct the full file paths for the documents to process
full_file_paths = [os.path.join(PDF_SOURCE_DIR, f) for f in FILES_TO_PROCESS]
print(f"Found {len(full_file_paths)} files to process.")

# Step 4: Run the main ingestion function
# This will trigger the PDF parsing, image captioning (API calls),
# chunking, embedding (API calls), and storage. This step can take time.
ingest_documents(full_file_paths, collection)
print("\n--- Ingestion Process Finished ---")


# ==============================================================================
# 5. VERIFY THE RESULTS
# ==============================================================================
# It's crucial to verify that the data was ingested correctly.

print("\n--- Verification ---")
# Check the number of items in the collection. This is our most basic sanity check.
try:
    item_count = collection.count()
    print(f"The collection '{COLLECTION_NAME}' now contains {item_count} items.")

    # If items exist, perform a test query to see what was stored.
    if item_count > 0:
        print("\nPerforming a test query for 'requirements'...")

        # Query the collection for a generic term relevant to project documents.
        results = collection.query(
            query_texts=["What are the requirements for this project?"],
            n_results=min(
                3, item_count
            ),  # Ask for 3 results, or fewer if the DB is small
            include=["documents", "metadatas"],
        )

        print("\nTop query results:")
        # Nicely print the retrieved documents and their metadata
        for i, (doc, meta) in enumerate(
            zip(results["documents"][0], results["metadatas"][0])
        ):
            print(f"  --- Result {i+1} ---")
            print(f"    Source: {meta.get('source_filename', 'N/A')}")
            print(f"    Page:   {meta.get('page_number', 'N/A')}")
            print(f"    Type:   {meta.get('content_type', 'N/A')}")
            # Print the first 250 characters of the content to keep it readable
            print(f"    Content: {doc[:250].replace(chr(10), ' ')}...")

except Exception as e:
    print(f"\nAn error occurred during verification: {e}")
    print("Please check your database connection and collection name.")
