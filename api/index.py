from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
import sys

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import aligner
import augmenter
import utils

# Initialize FastAPI with specific docs URLs for /api prefix
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "LegalAlign API is running"}

class AlignRequest(BaseModel):
    target_text: str
    mod_text: str

class AugmentRequest(BaseModel):
    target_text: str
    mod_text: str
    alignments: list

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save to temp file to read it
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Read content
        content = utils.read_file(tmp_path)
        
        # Cleanup
        os.unlink(tmp_path)
        
        if content is None:
            raise HTTPException(status_code=400, detail="Could not read file")
            
        return {"filename": file.filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/align")
async def align_docs(req: AlignRequest):
    try:
        raw_output = aligner.align_documents(req.target_text, req.mod_text)
        if not raw_output:
            raise HTTPException(status_code=500, detail="LLM alignment failed")
            
        alignments = aligner.parse_alignments(raw_output)
        return {"alignments": alignments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/augment")
async def augment_docs(req: AugmentRequest):
    try:
        augmented_text = augmenter.augment_document(req.target_text, req.mod_text, req.alignments)
        return {"augmented_text": augmented_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demo-data")
async def get_demo_data():
    try:
        # Path resolution for Vercel environment
        # Vercel copies api files to some root. 
        # But we need to look for ndas which we un-ignored.
        # Actually we need to check where we are running.
        
        # Try finding the file relative to this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # ndas should be in the parent of api/
        # But we added it to gitignore with exclusions.
        # Wait, file structure on Vercel:
        # /var/task/api/...
        # /var/task/ndas/...
        
        project_root = os.path.dirname(base_dir)
        target_path = os.path.join(project_root, "ndas", "1588052992CCTV%20Non%20Disclosure%20Agreement.pdf")
        mod_path = os.path.join(project_root, "ndas", "20150916-model-sharing-non-disclosure-agreement.pdf")
        
        if not os.path.exists(target_path):
             # Fallback logic removed, rely on os.path.join
             print(f"File not found at {target_path}")
        
        target_content = utils.read_file(target_path)
        mod_content = utils.read_file(mod_path)
        
        return {
            "target": {"filename": "Demo_Target.pdf", "content": target_content},
            "mod": {"filename": "Demo_Mod.pdf", "content": mod_content}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
