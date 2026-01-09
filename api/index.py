import sys
from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
import tempfile

# Unconditionally add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Safe Boot: Try to import modules
MODULES_LOADED = False
IMPORT_ERROR = None
VERSION = "1.0.2-Restored"

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

# PATH TUNNELING MIDDLEWARE
# Fixes Vercel path stripping by restoring path from ?__path= query param
@app.middleware("http")
async def path_tunnel_middleware(request: Request, call_next):
    # Check if we are receiving the tunneled path from vercel.json
    qp = request.query_params
    if "__path" in qp:
        original_segment = qp["__path"]
        # Reconstruct the full API path. 
        # vercel.json captures everything AFTER /api/.
        # So if source was /api/demo-data, __path is demo-data.
        # We want to restore it to /api/demo-data to match our routes.
        restored_path = f"/api/{original_segment}"
        
        # Override the Scope
        request.scope["path"] = restored_path
        
        # Log for debugging (optional)
        print(f"PATH FIXED: Tunneled '{original_segment}' -> '{restored_path}'")
        
    response = await call_next(request)
    return response

# Create a router
router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok" if MODULES_LOADED else "error", 
        "message": "LegalAlign API is running" if MODULES_LOADED else "Safe Mode (Modules Failed)",
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
        suffix = os.path.splitext(file.filename)[1]
        # Explicitly use /tmp for Vercel
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
        return JSONResponse(status_code=500, content={"detail": f"{str(e)}\n{traceback.format_exc()}", "type": "UploadError"})

@router.post("/align")
async def align_docs(req: AlignRequest):
    try:
        raw_output = aligner.align_documents(req.target_text, req.mod_text)
        if not raw_output:
             return JSONResponse(status_code=500, content={"detail": "LLM alignment failed", "type": "LLMError"})
        
        alignments = aligner.parse_alignments(raw_output)
        return {"alignments": alignments}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": f"{str(e)}\n{traceback.format_exc()}", "type": "AlignError"})

@router.post("/augment")
async def augment_docs(req: AugmentRequest):
    try:
        augmented_text = augmenter.augment_document(req.target_text, req.mod_text, req.alignments)
        return {"augmented_text": augmented_text}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": f"{str(e)}\n{traceback.format_exc()}", "type": "AugmentError"})

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
        return JSONResponse(status_code=500, content={"detail": f"{str(e)}\n{traceback.format_exc()}", "type": "DemoDataError"})

# Mounting Strategy: Double Mount for robustness
app.include_router(router, prefix="/api")
app.include_router(router)

# ROUTING FIX:
# The Sanity Check worked with @app.get("/api/demo-data").
# The Router version failed (saw path '/').
# We will explicitly mount routes on 'app' with the full /api prefix to match the success case.

@app.post("/api/upload")
async def upload_file_direct(file: UploadFile = File(...)):
    return await upload_file(file)

@app.post("/api/align")
async def align_docs_direct(req: AlignRequest):
    return await align_docs(req)

@app.post("/api/augment")
async def augment_docs_direct(req: AugmentRequest):
    return await augment_docs(req)

@app.get("/api/demo-data")
async def get_demo_data_direct():
    return await get_demo_data()

# Keep the health check which works
@app.get("/api/health")
async def health_check_direct():
    return await health_check()

# Also keep the function-based versions for internal logic or other mounts, 
# but the @app. verb ones above are the primary public entrypoints.

# ROOT DISPATCHER (The "Nuclear" Option)
# If Vercel strips path to '/', we catch it here and route manually using ?__path=
@app.api_route("/", methods=["GET", "POST"])
async def root_dispatcher(request: Request):
    qp = request.query_params
    target = qp.get("__path", "")
    
    print(f"ROOT DISPATCH: target='{target}'")

    if target == "demo-data":
        return await get_demo_data_direct()
    elif target == "health":
        return await health_check_direct()
    elif target == "align":
        # Need to parse body manually or forward? 
        # Since this is a manual dispatch, we might need to reconstruct the model.
        # But 'align' is POST.
        # Let's try to trust the middleware first, but this dispatcher handles GETs easily.
        # For POSTs with bodies, it's trickier. 
        # Let's return a specific error that proves we got here.
        return JSONResponse(status_code=400, content={"detail": "Please use direct POST", "dispatch": "root"})
    
    return {
        "detail": "Root Dispatcher (Path not found)",
        "target_path": target,
        "query_params": dict(qp),
        "headers": dict(request.headers)
    }

# Debug Catch-All
@app.api_route("/{path_name:path}", methods=["GET", "POST"])
async def catch_all(request: Request, path_name: str):
     return {
        "detail": "Not Found (Catch-All)", 
        "path": path_name,
        "scope_path": request.scope.get("path"),
        "query_params": dict(request.query_params), # ADDED THIS
        "headers": dict(request.headers),
        "available_routes": [r.path for r in app.routes if hasattr(r, 'path')]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
