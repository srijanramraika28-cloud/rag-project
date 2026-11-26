import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

UPLOAD_DIR = BASE_DIR / "uploads"
QDRANT_DIR = BASE_DIR / "data" / "qdrant"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
QDRANT_DIR.parent.mkdir(parents=True, exist_ok=True)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))
COLLECTION_NAME = "smartdoc_documents"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
