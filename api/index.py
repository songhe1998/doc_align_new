import sys
from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter
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

import aligner
import augmenter
import utils

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

class AlignRequest(BaseModel):
    target_text: str
    mod_text: str

class AugmentRequest(BaseModel):
    target_text: str
    mod_text: str
    alignments: list

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "LegalAlign API is running"}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        content = utils.read_file(tmp_path)
        os.unlink(tmp_path)
        if content is None:
            raise HTTPException(status_code=400, detail="Could not read file")
        return {"filename": file.filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/align")
async def align_docs(req: AlignRequest):
    try:
        raw_output = aligner.align_documents(req.target_text, req.mod_text)
        if not raw_output:
            raise HTTPException(status_code=500, detail="LLM alignment failed")
        alignments = aligner.parse_alignments(raw_output)
        return {"alignments": alignments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/augment")
async def augment_docs(req: AugmentRequest):
    try:
        augmented_text = augmenter.augment_document(req.target_text, req.mod_text, req.alignments)
        return {"augmented_text": augmented_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/demo-data")
async def get_demo_data():
    try:
        # Robust path finding
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(base_dir) # parent of api/
        
        # Check standard location (local) or Vercel location
        # On Vercel, sometimes CWD is /var/task
        paths_to_try = [
            os.path.join(project_root, "ndas"),
            os.path.join(os.getcwd(), "ndas"),
            "ndas" # relative to CWD
        ]
        
        found_target = None
        found_mod = None
        
        target_name = "1588052992CCTV%20Non%20Disclosure%20Agreement.pdf"
        mod_name = "20150916-model-sharing-non-disclosure-agreement.pdf"

        for p in paths_to_try:
            t = os.path.join(p, target_name)
            m = os.path.join(p, mod_name)
            if os.path.exists(t):
                found_target = t
                found_mod = m
                break
        
        # Fallback names without %20 if plain spaces used
        if not found_target:
             target_name_space = "1588052992CCTV Non Disclosure Agreement.pdf"
             for p in paths_to_try:
                t = os.path.join(p, target_name_space)
                m = os.path.join(p, mod_name)
                if os.path.exists(t):
                    found_target = t
                    found_mod = m
                    break
        
        if not found_target:
            return {"target": {"filename": "Error", "content": "Demo files not found on server"}, "mod": {"filename": "Error", "content": ""}}

        target_content = utils.read_file(found_target)
        mod_content = utils.read_file(found_mod)
        
        return {
            "target": {"filename": "Demo_Target.pdf", "content": target_content},
            "mod": {"filename": "Demo_Mod.pdf", "content": mod_content}
        }
    except Exception as e:
        print(f"Demo Error: {str(e)}")
        # Don't crash, return empty
        return {"target": {"filename": "Error", "content": str(e)}, "mod": {"filename": "Error", "content": ""}}

# Include the router TWICE to handle both /api/path and /path
# This solves the Vercel routing ambiguity
app.include_router(router, prefix="/api")
app.include_router(router) # For when Vercel strips the prefix or requests come to root context

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
