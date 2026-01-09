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

# Debug 404 Handler - Critical for routing diagnosis
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    # Flatten route list for debugging
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append(route.path)
        elif hasattr(route, "path_format"):
             routes.append(route.path_format)
    
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Not Found (Debug Mode)",
            "requested_path": request.url.path,
            "method": request.method,
            "root_path": request.scope.get("root_path", ""),
            "registered_routes": routes
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
