# backend/main.py
"""
Основной файл приложения gpzu-web.

Веб-приложение для автоматизации работы с градостроительными планами
земельных участков (ГПЗУ) и сопутствующими документами.

Модули:
- Kaiten: создание задач в Kaiten
- MID/MIF: подготовка файлов для MapInfo
- ТУ: формирование запросов технических условий
- ГПЗУ: подготовка градостроительных планов
"""

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Импорт роутеров
from api.auth import router as auth_router
from api.gp.kaiten import router as kaiten_router
from api.gp.midmif import router as midmif_router
from api.gp.tu import router as tu_router
from api.gp.gradplan import router as gradplan_router

# ========================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ========================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("gpzu-web")

# ========================================================================
# СОЗДАНИЕ ПРИЛОЖЕНИЯ
# ========================================================================

app = FastAPI(
    title="ГПЗУ Web API",
    description="API для автоматизированной системы выдачи градостроительных планов",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ========================================================================
# НАСТРОЙКА CORS
# ========================================================================

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

# ========================================================================
# СОЗДАНИЕ ДИРЕКТОРИЙ
# ========================================================================

# Папка для загрузок (если понадобится)
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Путь к frontend build
FRONTEND_BUILD = Path(__file__).parent.parent / "frontend" / "build"

# ========================================================================
# РЕГИСТРАЦИЯ API РОУТЕРОВ
# ========================================================================

# Аутентификация
app.include_router(auth_router)

# Модули градостроительного плана
app.include_router(kaiten_router)      # Создание задач в Kaiten
app.include_router(midmif_router)      # Подготовка MID/MIF файлов
app.include_router(tu_router)          # Формирование запросов ТУ
app.include_router(gradplan_router)    # Подготовка градостроительных планов

# ========================================================================
# СЛУЖЕБНЫЕ ENDPOINTS
# ========================================================================

@app.get("/api/health")
async def health_check():
    """
    Проверка работоспособности API.
    
    Returns:
        Статус сервиса и версия
    """
    return {
        "status": "ok",
        "service": "GPZU Web API",
        "version": "1.0.0",
        "modules": {
            "auth": "enabled",
            "kaiten": "enabled",
            "midmif": "enabled",
            "tu": "enabled",
            "gradplan": "enabled",
        }
    }


@app.get("/api/info")
async def api_info():
    """
    Информация о доступных модулях.
    
    Returns:
        Список модулей с описанием
    """
    return {
        "modules": [
            {
                "name": "Kaiten",
                "prefix": "/api/gp/kaiten",
                "description": "Создание задач в Kaiten из заявлений",
                "endpoints": 2
            },
            {
                "name": "MID/MIF",
                "prefix": "/api/gp/midmif",
                "description": "Подготовка файлов MID/MIF для MapInfo",
                "endpoints": 2
            },
            {
                "name": "ТУ",
                "prefix": "/api/gp/tu",
                "description": "Формирование запросов технических условий",
                "endpoints": 3
            },
            {
                "name": "ГПЗУ",
                "prefix": "/api/gp/gradplan",
                "description": "Подготовка градостроительных планов",
                "endpoints": 4
            },
        ]
    }

# ========================================================================
# СТАТИЧЕСКИЕ ФАЙЛЫ (для загрузок, если понадобится)
# ========================================================================

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ========================================================================
# FRONTEND (React приложение)
# ========================================================================

if FRONTEND_BUILD.exists():
    logger.info(f"Frontend build найден: {FRONTEND_BUILD}")
    
    # Статические файлы React
    app.mount("/static", StaticFiles(directory=FRONTEND_BUILD / "static"), name="static")
    
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        """
        Обслуживание React приложения.
        
        Все запросы, не начинающиеся с /api, перенаправляются на frontend.
        """
        # API endpoints не обрабатываем
        if full_path.startswith("api"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Если запрашивается конкретный файл и он существует
        file_path = FRONTEND_BUILD / full_path
        if file_path.is_file() and file_path.exists():
            return FileResponse(file_path)
        
        # Иначе возвращаем index.html (для React Router)
        index_path = FRONTEND_BUILD / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        
        # Если даже index.html нет
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend not found")

else:
    logger.warning(f"Frontend build не найден: {FRONTEND_BUILD}")
    logger.info("Для разработки запустите frontend отдельно: cd frontend && npm start")

# ========================================================================
# ЗАПУСК СЕРВЕРА
# ========================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 80)
    logger.info("Запуск ГПЗУ Web API...")
    logger.info("=" * 80)
    logger.info("Swagger UI: http://localhost:8000/api/docs")
    logger.info("ReDoc:      http://localhost:8000/api/redoc")
    logger.info("Health:     http://localhost:8000/api/health")
    logger.info("=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )