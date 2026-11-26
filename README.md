# SmartDoc AI — RAG PDF Chatbot

A complete local web application built around the RAG pipeline in the teacher-provided demo. It lets a user upload PDF files, index their text, ask questions, and see the document/page references used to form an answer.

## Features

- Clean responsive HTML/CSS/JavaScript chat interface
- FastAPI backend
- PDF upload and text extraction with PyPDF / LangChain
- Text chunking (default 600 characters, 80 overlap — matching the demo)
- FastEmbed embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- Persistent local Qdrant vector database
- NVIDIA Nemotron through the NVIDIA API
- Multiple PDFs and document-specific filtering
- Source document and page references
- Remove uploaded documents
- Basic file validation, size limits, and API error messages

## Requirements

- Windows 10/11, macOS, or Linux
- Python 3.10 or newer
- Internet connection for installing Python packages, downloading the embedding model the first time, and calling NVIDIA
- An NVIDIA API key with access to the configured model

## Run on Windows

1. Extract the ZIP to a normal folder, for example `Desktop\SmartDoc-AI`.
2. Open the folder and double-click `start_windows.bat`. It creates a virtual environment, installs dependencies, and creates `.env` from `.env.example` the first time.
3. Open the `.env` file in Notepad. Replace `your_nvidia_api_key_here` with your own NVIDIA API key. Save the file. Do not share this file or upload it to GitHub.
4. Double-click `start_windows_configured.bat` (or open Command Prompt in the project folder and run the commands below).
5. Open **http://localhost:8000** in Chrome.

### Manual Windows commands

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set NVIDIA_API_KEY
python -m uvicorn backend.main:app --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set NVIDIA_API_KEY
python -m uvicorn backend.main:app --reload
```

## How to use

1. Open the site at `http://localhost:8000`.
2. Upload one or more text-based PDFs using the upload area.
3. Wait for the indexing confirmation.
4. Ask a question in the chat box. Select one or more document names in the left library to limit retrieval; with none selected, all uploaded documents are searched.
5. Review the source chips under the answer to see the PDF and page number of retrieved passages.
6. Remove a PDF from the library using the × control beside its name.

## Project structure

```text
SmartDoc-AI/
├── backend/
│   ├── main.py             # FastAPI routes and static frontend hosting
│   ├── rag.py              # PDF indexing, Qdrant retrieval, NVIDIA generation
│   └── config.py           # Environment-based configuration
├── frontend/
│   ├── index.html          # User interface
│   ├── style.css           # Responsive styling
│   └── script.js           # Upload, chat, and document interactions
├── sample_documents/
│   └── teacher_sample.pdf  # PDF included in the teacher's ZIP, for testing
├── uploads/                # Uploaded PDFs (created automatically)
├── data/qdrant/            # Persistent vector database (created automatically)
├── .env.example
└── requirements.txt
```

## How this matches the teacher demo

The original demo's core flow is retained: `PyPDFLoader` → `RecursiveCharacterTextSplitter` → `FastEmbedEmbeddings` → `QdrantVectorStore` → retriever → `ChatNVIDIA` → grounded prompt. The original demo hard-coded one local PDF path and ran one terminal question. This version turns that flow into reusable functions and adds a web API, uploads, a document catalogue, persistent Qdrant storage, multiple-document filtering, and a browser chat UI.

The sample PDF from the teacher ZIP is copied to `sample_documents/teacher_sample.pdf`. It is not automatically indexed: upload it through the website to test the project.

## Important notes / limitations

- The NVIDIA API key is required for answer generation. PDF indexing can work without it, but chat requests will report that the key is missing.
- The first upload may take longer because FastEmbed downloads its embedding model on first use.
- This version extracts selectable text from PDFs. Scanned/image-only PDFs need an OCR stage, which is not included yet.
- Qdrant data and uploaded PDFs are stored locally in `data/` and `uploads/`; deleting the project folder deletes that local data.
- This is a local academic demo, not a production deployment. Authentication, per-user data isolation, HTTPS, and production hosting should be added before public deployment.
- Do not put API keys in Python or JavaScript source code. Keep the real key only in `.env`.

## Troubleshooting

- **`NVIDIA_API_KEY is missing`**: check that `.env` exists in the project root and contains `NVIDIA_API_KEY=...`; restart the server after editing it.
- **Module not found**: activate `.venv` and run `pip install -r requirements.txt` again.
- **Port 8000 is busy**: run `python -m uvicorn backend.main:app --reload --port 8001` and open `http://localhost:8001`.
- **PDF has no extractable text**: the PDF may be scanned. Use a text-based PDF or add OCR support.
- **NVIDIA model/API error**: confirm the key is valid and that the model is available to your NVIDIA account. You can change `NVIDIA_MODEL` in `.env` to another model available to your account.

## API endpoints

- `GET /api/health` — backend status and whether an NVIDIA key is configured
- `GET /api/documents` — list indexed documents
- `POST /api/upload` — upload and index a PDF (`multipart/form-data`, field name `file`)
- `POST /api/chat` — ask a question (`{"question":"...","document_ids":[]}`)
- `DELETE /api/documents/{document_id}` — delete a document and its vectors
- The most recent conversation transcript is saved in the browser's local storage and restored on reload. Clearing the conversation or starting a new one clears that saved transcript.
