# LabelFlow AI — Medical Device Labeling Management

## Overview
A prototype for medical-device label document analysis.

## Features
- PDF text extraction
- Preliminary keyword-based screening
- Text comparison between original and revised PDFs
- Template-based label draft generation
- SQLite audit history
- FastAPI backend and HTML interface
- Automated API tests

## Technology
Python, FastAPI, Uvicorn, pypdf, SQLite, HTML, CSS, JavaScript and pytest.

## Setup
Activate the virtual environment and install dependencies:

    python -m pip install -r requirements.txt

Start the backend:

    python -m uvicorn main:app --reload

Open API documentation:

    http://127.0.0.1:8000/docs

Open pdf-tool.html in your browser while the backend is running.

## Tests
Run:

    python -m pytest .\tests\test_api.py -v

Expected result: 6 tests passed.

## API Endpoints
- GET / — Backend status
- GET /health — Health check
- POST /extract-pdf — Extract PDF text
- POST /check-compliance — Preliminary keyword screening
- POST /change-impact — Compare two PDFs
- POST /generate-label-draft — Generate template-based draft
- GET /audit-history — Retrieve saved activity

## Limitations
Keyword screening is not regulatory approval. Label drafts are template-based and do not use a generative AI model. Change analysis compares extracted text, not artwork, layout or barcodes. Audit history is locally stored and is not tamper-proof. Human review is required before a real medical-device label is approved.

## Security
Never commit API keys, passwords or .env files to GitHub.

## Project Status
Working prototype with tested API endpoints, local audit logging and six automated tests. Real AI integration and further validation remain future work.
