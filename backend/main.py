from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
import tempfile

# Import our existing modules
import aligner
import augmenter
import utils

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AlignRequest(BaseModel):
    target_text: str
    mod_text: str

class AugmentRequest(BaseModel):
    target_text: str
    mod_text: str
    alignments: list

@app.post("/upload")
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

@app.post("/align")
async def align_docs(req: AlignRequest):
    try:
        raw_output = aligner.align_documents(req.target_text, req.mod_text)
        if not raw_output:
            raise HTTPException(status_code=500, detail="LLM alignment failed")
            
        alignments = aligner.parse_alignments(raw_output)
        return {"alignments": alignments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/augment")
async def augment_docs(req: AugmentRequest):
    try:
        augmented_text = augmenter.augment_document(req.target_text, req.mod_text, req.alignments)
        return {"augmented_text": augmented_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/demo-data")
async def get_demo_data():
    try:
        # Assuming CWD is project root
        target_path = "ndas/1588052992CCTV%20Non%20Disclosure%20Agreement.pdf"
        mod_path = "ndas/20150916-model-sharing-non-disclosure-agreement.pdf"
        
        if not os.path.exists(target_path):
            # Fallback if running from backend dir
            target_path = "../ndas/1588052992CCTV%20Non%20Disclosure%20Agreement.pdf"
            mod_path = "../ndas/20150916-model-sharing-non-disclosure-agreement.pdf"
        
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
