from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from io import BytesIO
import re

app = FastAPI(title="LabelFlow AI API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ComplianceRequest(BaseModel):
    text: str

@app.get("/")
def home():
    return {
        "message": "LabelFlow AI backend is running",
        "status": "success"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The file is empty.")

    try:
        reader = PdfReader(BytesIO(content))
        pages = [
            {"page": number, "text": page.extract_text() or ""}
            for number, page in enumerate(reader.pages, start=1)
        ]
        return {
            "filename": file.filename,
            "page_count": len(pages),
            "pages": pages,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {exc}"
        ) from exc

@app.post("/check-compliance")
def check_compliance(request: ComplianceRequest):
    text = request.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Please provide extracted label text."
        )

    checks = [
        {
            "item": "Product or device name",
            "passed": bool(re.search(
                r"\b(product name|device name|model name)\b",
                text, re.I
            )),
            "note": "Look for an explicit product or device name."
        },
        {
            "item": "Manufacturer identification",
            "passed": bool(re.search(
                r"\b(manufacturer|manufactured by)\b",
                text, re.I
            )),
            "note": "Look for manufacturer identification and required contact details."
        },
        {
            "item": "Lot or batch identifier",
            "passed": bool(re.search(
                r"\b(lot|batch)\s*(no\.?|number|#|:)?\b",
                text, re.I
            )),
            "note": "Check whether a lot or batch identifier is present."
        },
        {
            "item": "Expiry or use-by information",
            "passed": bool(re.search(
                r"\b(expiry|expiration|use by|use-by|exp\.?)\b",
                text, re.I
            )),
            "note": "Check whether expiry information is required for this device."
        },
        {
            "item": "UDI information",
            "passed": bool(re.search(
                r"\b(UDI|unique device identification|unique device identifier)\b",
                text, re.I
            )),
            "note": "Check UDI requirements for the applicable device and market."
        },
        {
            "item": "Warnings or precautions",
            "passed": bool(re.search(
                r"\b(warning|warnings|precaution|precautions|caution)\b",
                text, re.I
            )),
            "note": "Review applicable safety warnings and precautions."
        },
        {
            "item": "Instructions for use",
            "passed": bool(re.search(
                r"\b(instructions for use|directions for use|IFU)\b",
                text, re.I
            )),
            "note": "Verify whether instructions must appear on the label or in accompanying documentation."
        }
    ]

    passed = sum(1 for item in checks if item["passed"])
    return {
        "status": "preliminary_screening",
        "message": "Keyword screening only; this is not regulatory approval.",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks
    }
