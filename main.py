from openai import OpenAI
from io import BytesIO
import difflib
import re
import os

# Local AI configuration using Ollama

client = OpenAI(
    base_url="http://localhost:11434/v1/",
    api_key="ollama"
)

MODEL_NAME = "qwen2.5:7b"

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader

from audit_db import record_event, get_history


app = FastAPI(
    title="LabelFlow AI API",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class ComplianceRequest(BaseModel):
    text: str


class LabelDraftRequest(BaseModel):
    device_name: str
    manufacturer: str
    model_number: str = ""
    lot_number: str = ""
    expiry_date: str = ""
    udi: str = ""
    warnings: str = ""
    instructions: str = ""
    storage_conditions: str = ""


# --------------------------------------------------
# Home and health endpoints
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "LabelFlow AI backend is running",
        "status": "success"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# --------------------------------------------------
# PDF text extraction
# --------------------------------------------------

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file."
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The file is empty."
        )

    try:
        reader = PdfReader(BytesIO(content))

        pages = [
            {
                "page": number,
                "text": page.extract_text() or ""
            }
            for number, page in enumerate(reader.pages, start=1)
        ]

        return {
            "filename": file.filename,
            "page_count": len(pages),
            "pages": pages
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {exc}"
        ) from exc


# --------------------------------------------------
# Preliminary compliance keyword screening
# --------------------------------------------------

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
                text,
                re.I
            )),
            "note": "Look for an explicit product or device name."
        },
        {
            "item": "Manufacturer identification",
            "passed": bool(re.search(
                r"\b(manufacturer|manufactured by)\b",
                text,
                re.I
            )),
            "note": (
                "Look for manufacturer identification and "
                "required contact details."
            )
        },
        {
            "item": "Lot or batch identifier",
            "passed": bool(re.search(
                r"\b(lot|batch)\s*(no\.?|number|#|:)?\b",
                text,
                re.I
            )),
            "note": "Check whether a lot or batch identifier is present."
        },
        {
            "item": "Expiry or use-by information",
            "passed": bool(re.search(
                r"\b(expiry|expiration|use by|use-by|exp\.?)\b",
                text,
                re.I
            )),
            "note": (
                "Check whether expiry information is required "
                "for this device."
            )
        },
        {
            "item": "UDI information",
            "passed": bool(re.search(
                r"\b(UDI|unique device identification|"
                r"unique device identifier)\b",
                text,
                re.I
            )),
            "note": (
                "Check UDI requirements for the applicable "
                "device and market."
            )
        },
        {
            "item": "Warnings or precautions",
            "passed": bool(re.search(
                r"\b(warning|warnings|precaution|"
                r"precautions|caution)\b",
                text,
                re.I
            )),
            "note": "Review applicable safety warnings and precautions."
        },
        {
            "item": "Instructions for use",
            "passed": bool(re.search(
                r"\b(instructions for use|directions for use|IFU)\b",
                text,
                re.I
            )),
            "note": (
                "Verify whether instructions must appear on the label "
                "or in accompanying documentation."
            )
        }
    ]

    passed = sum(1 for item in checks if item["passed"])

    return {
        "status": "preliminary_screening",
        "message": (
            "Keyword screening only; this is not regulatory approval."
        ),
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks
    }


# --------------------------------------------------
# Change impact analysis
# --------------------------------------------------

@app.post("/change-impact")
async def change_impact(
    original_file: UploadFile = File(...),
    revised_file: UploadFile = File(...)
):
    """Compare text extracted from two label PDFs."""

    for upload in (original_file, revised_file):
        if (
            not upload.filename
            or not upload.filename.lower().endswith(".pdf")
        ):
            raise HTTPException(
                status_code=400,
                detail="Both uploads must be PDF files."
            )

    original_bytes = await original_file.read()
    revised_bytes = await revised_file.read()

    if not original_bytes or not revised_bytes:
        raise HTTPException(
            status_code=400,
            detail="Both PDF files must contain data."
        )

    try:
        original_reader = PdfReader(BytesIO(original_bytes))
        revised_reader = PdfReader(BytesIO(revised_bytes))

        original_text = "\n".join(
            page.extract_text() or ""
            for page in original_reader.pages
        )

        revised_text = "\n".join(
            page.extract_text() or ""
            for page in revised_reader.pages
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {exc}"
        ) from exc

    original_lines = original_text.splitlines()
    revised_lines = revised_text.splitlines()

    matcher = difflib.SequenceMatcher(
        a=original_lines,
        b=revised_lines,
        autojunk=False
    )

    changes = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        old_lines = original_lines[i1:i2]
        new_lines = revised_lines[j1:j2]

        combined = " ".join(old_lines + new_lines).lower()

        keywords = [
            word
            for word in [
                "warning",
                "caution",
                "sterile",
                "expiry",
                "expiration",
                "lot",
                "batch",
                "udi",
                "instructions for use",
                "storage",
                "dosage",
                "manufacturer",
                "model"
            ]
            if word in combined
        ]

        changes.append({
            "change_type": {
                "replace": "modified",
                "delete": "removed",
                "insert": "added"
            }[tag],
            "original_text": old_lines,
            "revised_text": new_lines,
            "potentially_sensitive": bool(keywords),
            "matched_keywords": keywords
        })

    # Log the completed comparison.
    sensitive_count = sum(
        1 for change in changes
        if change["potentially_sensitive"]
    )

    record_event(
        action="change_comparison",
        filename=(
            f"{original_file.filename} -> {revised_file.filename}"
        ),
        details=(
            f"Changes found: {len(changes)}; "
            f"potentially sensitive blocks: {sensitive_count}"
        )
    )

    return {
        "status": "comparison_complete",
        "original_filename": original_file.filename,
        "revised_filename": revised_file.filename,
        "changes_found": len(changes),
        "changes": changes,
        "review_notice": (
            "Text comparison only. Review all changes manually. "
            "This is not a regulatory impact determination and "
            "does not compare artwork, layout, or barcodes."
        )
    }


# --------------------------------------------------
# Label draft generation
# --------------------------------------------------

@app.post("/generate-label-draft")
def generate_label_draft(request: LabelDraftRequest):

    if (
        not request.device_name.strip()
        or not request.manufacturer.strip()
    ):
        raise HTTPException(
            status_code=400,
            detail="Device name and manufacturer are required."
        )

    prompt = f"""
    You are an AI assistant helping draft medical device labels.

    Generate a structured preliminary label draft using
    ONLY the information provided below.

    DEVICE INFORMATION:

    Device Name: {request.device_name}
    Manufacturer: {request.manufacturer}
    Model Number: {request.model_number}
    Lot Number: {request.lot_number}
    Expiry Date: {request.expiry_date}
    UDI: {request.udi}
    Warnings: {request.warnings}
    Instructions: {request.instructions}
    Storage Conditions: {request.storage_conditions}

    REQUIREMENTS:

    1. Organize information into clear sections.
    2. Use professional medical-device labeling language.
    3. Never invent missing product information.
    4. Mark missing information as [REQUIRES REVIEW].
    5. Do not invent regulatory claims or certifications.
    6. Preserve warnings and instructions as provided.
    7. Identify information requiring expert verification.
    8. Return a readable structured label draft.

    This is a preliminary draft, not an approved label.
    """

    try:

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You assist with preliminary medical "
                        "device label drafting. Never claim "
                        "regulatory approval."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        ai_draft = response.choices[0].message.content

        record_event(
            action="label_draft_generated",
            details="AI-assisted draft generated using local Qwen model."
        )

        return {
            "status": "draft_generated",
            "draft_type": "AI-assisted draft using local Qwen model",
            "label_draft": ai_draft,
            "review_notice": (
                "AI-generated preliminary draft. Verify all "
                "information against approved product specifications "
                "and applicable regulatory requirements. "
                "Human review and formal approval are mandatory."
            )
        }

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=f"Local AI generation failed: {str(exc)}"
        )

# --------------------------------------------------
# Audit history
# --------------------------------------------------

@app.get("/audit-history")
def audit_history(
    limit: int = Query(default=100, ge=1, le=200)
):
    """Return recent locally recorded audit events."""

    history = get_history(limit)

    return {
        "status": "success",
        "count": len(history),
        "history": history
    }
