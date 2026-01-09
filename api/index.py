from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "mode": "sanity_check", "version": "MINIMAL_1.0"}

@app.get("/api/demo-data")
def demo_data():
    return {"message": "Sanity check demo data"}

# Catch-all for debugging paths
@app.api_route("/{path_name:path}", methods=["GET", "POST"])
async def catch_all(path_name: str):
    return {"status": "ok", "path": path_name, "mode": "catch_all"}

# Vercel Entrypoint
handler = app
