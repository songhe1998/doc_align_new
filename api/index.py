import sys
import config
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
    import aligner_anchors
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
    strategy: str = "standard"

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
        if req.strategy == "anchors":
            print("Using Experimental Anchor Strategy")
            result = aligner_anchors.align_documents_anchors(req.target_text, req.mod_text)
            if isinstance(result, str) and result.startswith("Error"):
                 return JSONResponse(status_code=500, content={"detail": result, "type": "AlignerError"})
            
            # Anchor aligner already returns list of dicts or raises
            alignments = result
            
        else:
            # Standard Strategy
            alignment_text = aligner.align_documents(req.target_text, req.mod_text)
            
            if not alignment_text or alignment_text.startswith("Error"):
                return JSONResponse(status_code=500, content={"detail": alignment_text or "Unknown Error", "type": "AlignerError"})
            
            alignments = aligner.parse_alignments(alignment_text)
            
        return {"alignments": alignments}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": f"{str(e)}\n{traceback.format_exc()}", "type": "AlignerError", "trace": traceback.format_exc()})

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
    Returns a random PDF from the ndas folder for testing.
    """
    import random
    import glob
    
    # Path to ndas
    nda_dir = os.path.join(current_dir, "../ndas")
    
    filename = "Standard NDA (Template)"
    content = "This is a fallback. No PDFs found in ndas folder."
    
    if os.path.exists(nda_dir):
        files = glob.glob(os.path.join(nda_dir, "*.pdf"))
        # Filter out files that start with ._ or other system temp files
        files = [f for f in files if not os.path.basename(f).startswith("._")]
        
        if files:
            selected_file = random.choice(files)
            fname = os.path.basename(selected_file)
            print(f"Loading random demo file: {fname}")
            
            try:
                # Read content using utils
                text = utils.read_file(selected_file)
                if text:
                    filename = fname
                    content = text
            except Exception as e:
                print(f"Error reading {fname}: {e}")

    # Return nested structure expected by App.jsx
    return {
        "target": {"filename": filename, "content": content},
        "mod": {"filename": f"{filename} (Copy)", "content": content}
    }

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
