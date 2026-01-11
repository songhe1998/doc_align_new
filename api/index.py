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
    import config
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
# Fixes Vercel path stripping by restoring path from ?_action= query param
@app.middleware("http")
async def path_tunnel_middleware(request: Request, call_next):
    # Check if we are receiving the tunneled path from vercel.json
    qp = request.query_params
    if "_action" in qp:
        original_segment = qp["_action"]
        restored_path = f"/api/{original_segment}"
        # Override the Scope
        request.scope["path"] = restored_path
        print(f"PATH FIXED: Tunneled '{original_segment}' -> '{restored_path}'")
        
    response = await call_next(request)
    return response

# Create a router
router = APIRouter()

@router.get("/health")
async def health_check():
    import openai, httpx, pydantic
    
    api_key_status = False
    try:
        import config
        api_key_status = bool(config.OPENAI_API_KEY)
    except:
        pass

    return {
        "status": "ok" if MODULES_LOADED else "error", 
        "message": "LegalAlign API is running" if MODULES_LOADED else "Safe Mode (Modules Failed)",
        "modules_loaded": MODULES_LOADED,
        "import_error": IMPORT_ERROR,
        "version": VERSION,
        "api_key_configured": api_key_status,
        "libs": {
            "openai": openai.__version__,
            "httpx": httpx.__version__,
            "pydantic": pydantic.__version__
        }
    }

class AlignRequest(BaseModel):
    target_text: str
    mod_text: str

class AugmentRequest(BaseModel):
    target_text: str
    mod_text: str

@app.post("/upload")
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

@app.post("/align")
async def align_docs(req: AlignRequest):
    try:
        raw_output = aligner.align_documents(req.target_text, req.mod_text)
        if not raw_output:
             return JSONResponse(status_code=500, content={"detail": "LLM alignment returned empty response", "type": "EmptyResponse"})
        
        alignments = aligner.parse_alignments(raw_output)
        return {"alignments": alignments}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": f"LLM Error: {str(e)}", "type": "LLMError", "trace": traceback.format_exc()})

@app.post("/augment")
async def augment_docs(req: AugmentRequest):
    try:
        augmented_text = augmenter.augment_document(req.target_text, req.mod_text, req.alignments)
        return {"augmented_text": augmented_text}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": f"{str(e)}\n{traceback.format_exc()}", "type": "AugmentError"})

@app.get("/demo-data")
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

from fastapi.staticfiles import StaticFiles

# ... (Keep existing API routes)

# Mount the React Frontend (must be last)
# Check if build directory exists (it will on Render after build)
frontend_dist = os.path.join(current_dir, "../frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
else:
    print(f"WARNING: Frontend dist not found at {frontend_dist}. API only mode.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
