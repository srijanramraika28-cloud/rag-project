from __future__ import annotations
import uuid
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .config import (
    NVIDIA_API_KEY, NVIDIA_MODEL, QDRANT_DIR, COLLECTION_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP, RETRIEVER_K,
)

_embeddings = None
_client = None
_vectorstore = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return _embeddings


def get_client():
    global _client
    if _client is None:
        _client = QdrantClient(path=str(QDRANT_DIR))
        if not _client.collection_exists(COLLECTION_NAME):
            _client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
    return _client


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = QdrantVectorStore(
            client=get_client(), collection_name=COLLECTION_NAME, embedding=get_embeddings()
        )
    return _vectorstore


def index_pdf(pdf_path: Path, document_id: str, display_name: str) -> dict[str, Any]:
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()
    if not pages:
        raise ValueError("No readable text was found in this PDF.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(pages)
    if not chunks:
        raise ValueError("This PDF does not contain extractable text. Scanned PDFs need OCR.")

    for chunk in chunks:
        chunk.metadata.update({"document_id": document_id, "document_name": display_name})
        # PyPDFLoader uses zero-based page numbers; show one-based numbers in the UI.
        chunk.metadata["page_number"] = int(chunk.metadata.get("page", 0)) + 1

    get_vectorstore().add_documents(chunks, ids=[str(uuid.uuid4()) for _ in chunks])
    return {"pages": len(pages), "chunks": len(chunks)}


def ask_question(question: str, document_ids: list[str] | None = None) -> dict[str, Any]:
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY is missing. Add your NVIDIA API key to the .env file.")

    search_kwargs: dict[str, Any] = {"k": RETRIEVER_K}
    if document_ids:
        search_kwargs["filter"] = Filter(
            must=[FieldCondition(key="metadata.document_id", match=MatchValue(value=doc_id)) for doc_id in document_ids]
        ) if len(document_ids) == 1 else Filter(
            should=[FieldCondition(key="metadata.document_id", match=MatchValue(value=doc_id)) for doc_id in document_ids]
        )

    docs = get_vectorstore().similarity_search(question, **search_kwargs)
    if not docs:
        return {
            "answer": "I couldn't find relevant information in the uploaded documents. Try asking about a topic covered in your PDFs.",
            "sources": [],
        }

    context_parts = []
    sources = []
    seen = set()
    for doc in docs:
        name = doc.metadata.get("document_name", "Uploaded PDF")
        page = doc.metadata.get("page_number", "?")
        context_parts.append(f"[Source: {name}, page {page}]\n{doc.page_content}")
        key = (name, page)
        if key not in seen:
            sources.append({"document": name, "page": page, "excerpt": doc.page_content[:240].strip()})
            seen.add(key)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are SmartDoc AI, a helpful study assistant. Answer using ONLY the supplied document context. "
         "Do not invent facts. If the context does not contain the answer, clearly say that the uploaded documents do not provide it. "
         "Explain clearly in student-friendly language. When useful, organize the answer with short headings or bullet points. "
         "Cite source pages in the answer using the provided source labels.\n\nDOCUMENT CONTEXT:\n{context}"),
        ("human", "{question}"),
    ])
    llm = ChatNVIDIA(
        model=NVIDIA_MODEL,
        nvidia_api_key=NVIDIA_API_KEY,
        temperature=0.2,
        max_completion_tokens=1800,
    )
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": "\n\n---\n\n".join(context_parts), "question": question})
    return {"answer": answer, "sources": sources}


def delete_document(document_id: str) -> None:
    get_client().delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(must=[FieldCondition(key="metadata.document_id", match=MatchValue(value=document_id))]),
    )
