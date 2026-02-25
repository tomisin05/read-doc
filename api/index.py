"""
Verbatim Extractor — FastAPI Backend
Runs on Vercel as a Python serverless function.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile
import os
import sys
from pathlib import Path
from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, storage as firebase_storage

# ── Init Firebase Admin SDK ──────────────────────────────────────────────────
# Set GOOGLE_APPLICATION_CREDENTIALS env var in Vercel to your service account JSON path
# OR embed the JSON directly as FIREBASE_SERVICE_ACCOUNT env var

if not firebase_admin._apps:
    import json
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
    else:
        # Fallback: use default credentials (Cloud Run / GCP environment)
        cred = credentials.ApplicationDefault()

    firebase_admin.initialize_app(cred, {
        'storageBucket': os.environ.get("VITE_FIREBASE_STORAGE_BUCKET", "")
    })

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(title="Verbatim Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your Vercel domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth Middleware ───────────────────────────────────────────────────────────
async def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ── Request/Response Models ───────────────────────────────────────────────────
class ProcessRequest(BaseModel):
    storage_path: str       # Firebase Storage path e.g. uploads/uid/timestamp_file.docx
    filename: str           # Original filename
    mode: str               # 'both' | 'highlighted' | 'underlined'
    user_id: str


class ProcessResponse(BaseModel):
    download_url: str
    output_filename: str


# ── Extractor Logic (inlined from verbatim_extractor.py) ─────────────────────
from docx import Document
from docx.oxml.ns import qn


def run_is_highlighted(run):
    rpr = run._r.find(qn('w:rPr'))
    if rpr is None: return False
    
    # Check standard highlight
    highlight = rpr.find(qn('w:highlight'))
    if highlight is not None:
        val = highlight.get(qn('w:val'), '')
        if val.lower() not in ('', 'none'):
            return True
    
    # Check background shading (often used when pasting from web)
    shd = rpr.find(qn('w:shd'))
    if shd is not None:
        fill = shd.get(qn('w:fill'), '')
        if fill.lower() not in ('', 'auto', 'ffffff', 'none'):
            return True
    
    return False


def run_is_underlined(run):
    rpr = run._r.find(qn('w:rPr'))
    if rpr is None: return False
    u = rpr.find(qn('w:u'))
    if u is None: return False
    val = u.get(qn('w:val'), 'single')
    return val.lower() != 'none'


def run_is_bold(run):
    rpr = run._r.find(qn('w:rPr'))
    if rpr is None: return False
    b = rpr.find(qn('w:b'))
    return b is not None


def paragraph_is_structural(para):
    style_name = (para.style.name or '').lower()
    if any(k in style_name for k in ('heading', 'block', 'tag', 'cite', 'title')):
        return True
    runs = [r for r in para.runs if r.text.strip()]
    if not runs: return False
    return all(run_is_bold(r) for r in runs)


def run_passes(run, mode):
    if mode == 'highlighted':
        return run_is_highlighted(run)
    elif mode == 'underlined':
        return run_is_underlined(run)
    else:  # both (OR)
        return run_is_highlighted(run) or run_is_underlined(run)


def paragraph_has_marked_runs(para, mode):
    for run in para.runs:
        if run.text.strip() and run_passes(run, mode):
            return True
    return False


def filter_paragraph_runs(para, mode):
    if paragraph_is_structural(para):
        return True

    runs_to_remove = []
    prev_kept = False
    for run in para.runs:
        if not run.text.strip():
            continue
        keep = run_passes(run, mode)
        if not keep:
            runs_to_remove.append(run)
        else:
            if prev_kept and not run.text.startswith(' '):
                run.text = ' ' + run.text
            prev_kept = True

    for run in runs_to_remove:
        run._r.getparent().remove(run._r)

    remaining = [r for r in para.runs if r.text.strip()]
    return len(remaining) > 0


def extract_document(input_path: str, output_path: str, mode: str):
    out_doc = Document(input_path)
    paras_to_remove = []
    prev_was_structural = False

    for para in out_doc.paragraphs:
        is_structural = paragraph_is_structural(para)
        if is_structural or prev_was_structural:
            prev_was_structural = is_structural
            continue
        prev_was_structural = False

        if not paragraph_has_marked_runs(para, mode):
            paras_to_remove.append(para)
        else:
            has_content = filter_paragraph_runs(para, mode)
            if not has_content:
                paras_to_remove.append(para)

    for para in paras_to_remove:
        para._element.getparent().remove(para._element)

    # Clean up double-empty paragraphs
    all_paras = out_doc.element.body.findall('.//' + qn('w:p'))
    prev_empty = False
    for p_el in all_paras:
        texts = ''.join(t.text or '' for t in p_el.iter(qn('w:t')))
        is_empty = not texts.strip()
        if is_empty and prev_empty:
            p_el.getparent().remove(p_el)
        prev_empty = is_empty

    out_doc.save(output_path)


# ── API Endpoint ──────────────────────────────────────────────────────────────
@app.post("/api/process", response_model=ProcessResponse)
async def process_document(
    body: ProcessRequest,
    user=Depends(verify_token),
):
    # Verify user owns the file
    if user["uid"] != body.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    bucket = firebase_storage.bucket()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Download from Firebase Storage
        input_path = os.path.join(tmpdir, "input.docx")
        blob = bucket.blob(body.storage_path)
        blob.download_to_filename(input_path)

        # Process
        stem = Path(body.filename).stem
        output_filename = f"{stem}_read-doc.docx"
        output_path = os.path.join(tmpdir, output_filename)

        try:
            extract_document(input_path, output_path, body.mode)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

        # Upload processed file back to Firebase Storage
        output_storage_path = f"outputs/{body.user_id}/{output_filename}"
        output_blob = bucket.blob(output_storage_path)
        output_blob.upload_from_filename(output_path, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        # Generate signed download URL (valid 1 hour)
        from datetime import timedelta
        download_url = output_blob.generate_signed_url(
            expiration=timedelta(hours=1),
            method="GET",
        )

        # Delete the uploaded input file immediately after processing
        try:
            bucket.blob(body.storage_path).delete()
        except Exception:
            pass  # Non-critical

    return ProcessResponse(
        download_url=download_url,
        output_filename=output_filename,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
