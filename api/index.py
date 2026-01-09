import sys
from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
import tempfile

import sys

# Unconditionally add current directory to path to support all import styles
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Safe Boot: Try to import modules, capture error if fails
MODULES_LOADED = False
IMPORT_ERROR = None
VERSION = "1.0.1-StaticDemo" # Update this to verify deployment

try:
    import aligner
    import augmenter
    import utils
    MODULES_LOADED = True
except Exception as e:
    import traceback
    IMPORT_ERROR = f"{str(e)}\n{traceback.format_exc()}"

# Define the app
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a router for the core logic
router = APIRouter()

@router.get("/health")
async def health_check():
    status_code = 200 if MODULES_LOADED else 503
    return {
        "status": "ok" if MODULES_LOADED else "error", 
        "message": "LegalAlign API is running" if MODULES_LOADED else "LegalAlign API started in Safe Mode (Modules Failed)",
        "modules_loaded": MODULES_LOADED,
        "import_error": IMPORT_ERROR,
        "version": VERSION
    }

class AlignRequest(BaseModel):
    target_text: str
    mod_text: str

class AugmentRequest(BaseModel):
    target_text: str
    mod_text: str
    alignments: list

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Vercel only allows writing to /tmp
        suffix = os.path.splitext(file.filename)[1]
        
        # Explicitly use /tmp for Vercel friendliness
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='/tmp') as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        content = utils.read_file(tmp_path)
        os.unlink(tmp_path)
        
        if content is None:
            raise HTTPException(status_code=400, detail="Could not read file")
        return {"filename": file.filename, "content": content}
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        # Return 500 with details for debugging
        return JSONResponse(status_code=500, content={"detail": error_msg, "type": "UploadError"})

@router.post("/align")
async def align_docs(req: AlignRequest):
    try:
        raw_output = aligner.align_documents(req.target_text, req.mod_text)
        if not raw_output:
             return JSONResponse(status_code=500, content={"detail": "LLM alignment failed (returned None)", "type": "LLMError"})
        
        if isinstance(raw_output, str) and raw_output.startswith("Error:"):
             return JSONResponse(status_code=500, content={"detail": raw_output, "type": "LLMConfigError"})

        alignments = aligner.parse_alignments(raw_output)
        return {"alignments": alignments}
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return JSONResponse(status_code=500, content={"detail": error_msg, "type": "AlignError"})

@router.post("/augment")
async def augment_docs(req: AugmentRequest):
    try:
        augmented_text = augmenter.augment_document(req.target_text, req.mod_text, req.alignments)
        return {"augmented_text": augmented_text}
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return JSONResponse(status_code=500, content={"detail": error_msg, "type": "AugmentError"})

@router.get("/demo-data")
async def get_demo_data():
    """
    Returns static demo data to avoid filesystem reads on Vercel.
    """
    try:
        target_content = (
            "NON-DISCLOSURE AGREEMENT\n\n"
            "This Non-Disclosure Agreement (the \"Agreement\") is entered into by and between "
            "Company A (\"Discloser\") and Company B (\"Recipient\").\n\n"
            "1. Confidential Information\n"
            "Definition: 'Confidential Information' means all non-public information disclosed by Discloser, "
            "whether written or oral, that is designated as confidential or effectively should be treated as such.\n\n"
            "2. Obligations\n"
            "Recipient agrees to hold Confidential Information in strict confidence and use it only for the Purpose."
        )
        
        mod_content = (
            "CONFIDENTIALITY AGREEMENT\n\n"
            "Parties: Company A and Company B.\n\n"
            "1. Definition of Confidential Info\n"
            "'Confidential Information' refers to any proprietary data shared between the parties.\n\n"
            "2. Duty of Care\n"
            "receiving party shall protect the information with reasonable care."
        )

        return {
            "target": {"filename": "Demo_Target_Static.txt", "content": target_content},
            "mod": {"filename": "Demo_Mod_Static.txt", "content": mod_content}
        }
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return JSONResponse(status_code=500, content={"detail": error_msg, "type": "DemoDataError"})

# SIMPLIFIED ROUTING:
# We rely on vercel.json to send /api/* -> /api/index.py
# Inside index.py, we want to handle paths RELATIVE to the mount.
# But Vercel behavior varies.
# SAFEST BET: Mount at ROOT. If Vercel strips /api, it hits /demo-data.
# If Vercel keeps /api, we need to handle that?
# Let's use a wildcard mount or keep the double mount but safer?
# Actually, the user says /health works. /health matches ONE of them.
# The issue is /demo-data fails.

# Let's clear the router include and use detailed explicit routes if needed? No, too much work.
# Let's try mounting ONLY at root. Vercel usually strips the prefix if rewrite destination is a file.
app.include_router(router)
# Also add a specific /api prefix just in case, but AFTER root?
# No, let's stick to the double mount but validly.

# WAIT. If I mount at /api AND /, and Vercel sends /api/demo-data.
# It matches /api prefix -> path /demo-data.
# If Vercel sends /demo-data.
# It matches / prefix -> path /demo-data.

# Let's keep double router but ensure no conflicts.
app.include_router(router, prefix="/api")

# Debug Catch-All
from fastapi import Request
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return {
        "detail": "Not Found (Debug Mode)",
        "path": request.url.path,
        "method": request.method,
        "root_path": request.scope.get("root_path", ""),
        "headers": dict(request.headers),
        "params": dict(request.query_params)
    }

# Expose 'handler' for Vercel
handler = app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
