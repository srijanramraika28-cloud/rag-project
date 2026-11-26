from __future__ import annotations
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pypdf import PdfReader

from .config import BASE_DIR, UPLOAD_DIR, MAX_UPLOAD_MB
from .rag import index_pdf, ask_question, delete_document

app = FastAPI(title="SmartDoc AI API", version="1.0.0", description="RAG-powered PDF question answering")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Lightweight metadata catalogue. Vector data itself is persisted in Qdrant.
DOCUMENTS: dict[str, dict] = {}
CATALOG_PATH = BASE_DIR / "data" / "documents.json"
CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
if CATALOG_PATH.exists():
    try:
        import json
        DOCUMENTS = {item["id"]: item for item in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))}
    except Exception:
        DOCUMENTS = {}


def save_catalog():
    import json
    CATALOG_PATH.write_text(json.dumps(list(DOCUMENTS.values()), indent=2), encoding="utf-8")


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    document_ids: list[str] = Field(default_factory=list)


@app.get("/api/health")
def health():
    from .config import NVIDIA_API_KEY
    return {"status": "ok", "nvidia_configured": bool(NVIDIA_API_KEY)}


@app.get("/api/documents")
def list_documents():
    return {"documents": list(DOCUMENTS.values())}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    filename = Path(file.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is too large. Maximum size is {MAX_UPLOAD_MB} MB.")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    doc_id = str(uuid.uuid4())
    safe_path = UPLOAD_DIR / f"{doc_id}.pdf"
    safe_path.write_bytes(content)
    try:
        # Validate PDF and count pages before indexing.
        reader = PdfReader(str(safe_path))
        if len(reader.pages) == 0:
            raise ValueError("The PDF has no pages.")
        stats = index_pdf(safe_path, doc_id, filename)
        record = {"id": doc_id, "name": filename, "pages": stats["pages"], "chunks": stats["chunks"]}
        DOCUMENTS[doc_id] = record
        save_catalog()
        return {"message": "PDF uploaded and indexed successfully.", "document": record}
    except Exception as exc:
        safe_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/chat")
def chat(payload: ChatRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Please enter a question.")
    valid_ids = [doc_id for doc_id in payload.document_ids if doc_id in DOCUMENTS]
    if not DOCUMENTS:
        raise HTTPException(status_code=400, detail="Upload a PDF before asking a question.")
    try:
        return ask_question(payload.question.strip(), valid_ids or None)
    except Exception as exc:
        message = str(exc)
        if "NVIDIA_API_KEY" in message:
            raise HTTPException(status_code=503, detail=message)
        raise HTTPException(status_code=502, detail=f"AI request failed: {message}")


@app.delete("/api/documents/{document_id}")
def remove_document(document_id: str):
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        delete_document(document_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not remove vectors: {exc}")
    (UPLOAD_DIR / f"{document_id}.pdf").unlink(missing_ok=True)
    DOCUMENTS.pop(document_id, None)
    save_catalog()
    return {"message": "Document deleted."}


@app.get("/api/config")
def public_config():
    from .config import NVIDIA_API_KEY, MAX_UPLOAD_MB
    return {"nvidia_configured": bool(NVIDIA_API_KEY), "max_upload_mb": MAX_UPLOAD_MB}


# Serve the web interface at http://localhost:8000
app.mount("/", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="frontend")
