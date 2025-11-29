# backend/main.py
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.auth import router as auth_router
from api.gp.kaiten import router as kaiten_router
from api.gp.midmif import router as midmif_router  # ← ДОБАВЛЕНО

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("gpzu-web")

app = FastAPI(
    title="ГПЗУ Web API",
    description="API для автоматизированной системы выдачи градостроительных планов",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://10.1.200.12:3000",
        "http://10.1.200.12:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

FRONTEND_BUILD = Path(__file__).parent.parent / "frontend" / "build"

# API роуты
app.include_router(auth_router)
app.include_router(kaiten_router)
app.include_router(midmif_router)  # ← ДОБАВЛЕНО

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "GPZU Web API", "version": "1.0.0"}

# Статические файлы
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Frontend
if FRONTEND_BUILD.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_BUILD / "static"), name="static")
    
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        file_path = FRONTEND_BUILD / full_path
        if file_path.is_file() and file_path.exists():
            return FileResponse(file_path)
        
        index_path = FRONTEND_BUILD / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend not found")
else:
    logger.warning(f"Frontend build не найден: {FRONTEND_BUILD}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Запуск ГПЗУ Web API...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")