# backend/api/gp/workspace.py
"""
API endpoint для генерации рабочего набора MapInfo из выписки ЕГРН.

Функционал:
- Парсинг выписки ЕГРН (XML)
- Пространственный анализ (поиск ЗОУИТ, ОКС)
- Генерация структуры папок как в test_full_workspace.py
- Создание всех слоев MapInfo (TAB)
- Упаковка в ZIP архив
- Автоматическое скачивание
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import logging
import io
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

from parsers.egrn_parser import parse_egrn_xml
from utils.spatial_analysis import perform_spatial_analysis
from models.workspace_data import WorkspaceData
from generator.mif_writer import (
    create_workspace_directory,
    get_project_base_dir,
    create_parcel_mif,
    create_parcel_points_mif,
    create_building_zone_mif,
    create_oks_mif,
    create_zouit_mif,
    create_zouit_labels_mif,
)
from generator.wor_builder import create_workspace_wor
from generator.mif_to_tab_converter import convert_all_mif_to_tab

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/workspace", tags=["workspace"])


@router.get("/health")
async def health_check():
    """Проверка работоспособности модуля."""
    return {"status": "ok", "service": "workspace"}


@router.post("/generate")
async def generate_workspace(egrn_file: UploadFile = File(...)):
    """
    Генерация рабочего набора MapInfo из выписки ЕГРН.
    
    Принимает XML файл выписки ЕГРН, выполняет:
    1. Парсинг ЕГРН
    2. Пространственный анализ (ЗОУИТ, ОКС)
    3. Создание структуры папок GP_Graphics_<cadnum>/
    4. Генерацию всех слоев MapInfo (TAB)
    5. Создание WOR файла
    6. Упаковку в ZIP архив
    
    Returns:
        ZIP архив для скачивания
    """
    workspace_dir = None
    
    try:
        # ========== ШАГ 1: Парсинг ЕГРН ========== #
        logger.info(f"📥 Получен файл: {egrn_file.filename}")
        
        if not egrn_file.filename.lower().endswith('.xml'):
            raise HTTPException(
                status_code=400,
                detail="Поддерживаются только XML файлы выписки ЕГРН"
            )
        
        content = await egrn_file.read()
        egrn_data = parse_egrn_xml(content)
        
        if not egrn_data.cadnum:
            raise HTTPException(
                status_code=400,
                detail="Не удалось извлечь кадастровый номер из ЕГРН"
            )
        
        logger.info(f"✅ ЕГРН распознан: {egrn_data.cadnum}")
        
        # ========== ШАГ 2: Пространственный анализ ========== #
        logger.info("🔍 Запуск пространственного анализа...")
        
        spatial_result = perform_spatial_analysis(egrn_data)
        
        # Создаем WorkspaceData
        workspace = WorkspaceData(
            parcel=egrn_data,
            building_zone=spatial_result.building_zone,
            capital_objects=spatial_result.capital_objects,
            zouit=spatial_result.zouit_list
        )
        
        logger.info(f"✅ Анализ завершен:")
        logger.info(f"   - ОКС: {len(workspace.capital_objects)}")
        logger.info(f"   - ЗОУИТ: {len(workspace.zouit)}")
        
        # ========== ШАГ 3: Создание структуры папок ========== #
        logger.info("📁 Создание структуры папок...")
        
        workspace_dir = create_workspace_directory(workspace.parcel.cadnum)
        project_base = get_project_base_dir(workspace_dir)
        
        logger.info(f"✅ Создана: {workspace_dir.name}/")
        logger.info(f"   └── База_проекта/")
        
        # ========== ШАГ 4: Генерация MIF/MID файлов ========== #
        logger.info("🗺️  Генерация слоев MapInfo...")
        
        # Участок
        create_parcel_mif(workspace.parcel, project_base)
        logger.info("   ✅ участок.MIF")
        
        # Точки участка
        create_parcel_points_mif(workspace.parcel, project_base)
        logger.info("   ✅ участок_точки.MIF")
        
        # Зона строительства
        create_building_zone_mif(
            workspace.building_zone,
            workspace.parcel.cadnum,
            project_base
        )
        logger.info("   ✅ зона_строительства.MIF")
        
        # ОКС (если есть)
        result_oks = create_oks_mif(workspace.capital_objects, project_base)
        if result_oks:
            logger.info(f"   ✅ окс.MIF ({len(workspace.capital_objects)} объектов)")
        
        # ЗОУИТ (если есть)
        result_zouit = create_zouit_mif(workspace.zouit, project_base)
        if result_zouit:
            logger.info(f"   ✅ {len(result_zouit)} слоёв ЗОУИТ")
            
            # Подписи ЗОУИТ
            if workspace.parcel.geometry:
                result_labels = create_zouit_labels_mif(
                    zouit_list=workspace.zouit,
                    parcel_geometry=workspace.parcel.geometry,
                    output_dir=project_base
                )
                if result_labels:
                    logger.info("   ✅ зоуит_подписи.MIF")
        
        # ========== ШАГ 5: Конвертация MIF → TAB ========== #
        logger.info("🔄 Конвертация MIF → TAB...")
        
        tab_files = convert_all_mif_to_tab(project_base, remove_mif=True, method='auto')
        logger.info(f"✅ Конвертировано: {len(tab_files)} файлов")
        
        # ========== ШАГ 6: Создание WOR файла ========== #
        logger.info("📝 Создание рабочего набора (WOR)...")
        
        has_oks = result_oks is not None
        has_labels = result_zouit and workspace.parcel.geometry and result_labels
        
        wor_path = create_workspace_wor(
            workspace_dir=workspace_dir,
            cadnum=workspace.parcel.cadnum,
            has_oks=has_oks,
            zouit_files=result_zouit,
            has_zouit_labels=has_labels,
            address=workspace.parcel.address,
            specialist_name="Автоматически сгенерировано",
            zouit_list=workspace.zouit,
        )
        
        logger.info(f"✅ {wor_path.name} создан")
        
        # ========== ШАГ 7: Упаковка в ZIP ========== #
        logger.info("📦 Создание ZIP архива...")
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Добавляем все файлы из workspace_dir
            for file_path in workspace_dir.rglob('*'):
                if file_path.is_file():
                    # Относительный путь внутри ZIP
                    arcname = file_path.relative_to(workspace_dir.parent)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        # Формируем имя архива
        safe_cadnum = workspace.parcel.cadnum.replace(':', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"GP_Graphics_{safe_cadnum}_{timestamp}.zip"
        
        logger.info(f"✅ ZIP архив создан: {zip_filename}")
        logger.info(f"📊 Размер: {len(zip_buffer.getvalue()) / 1024:.2f} KB")
        
        # ========== ШАГ 8: Возврат файла ========== #
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"'
            }
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception(f"❌ Ошибка генерации рабочего набора: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации рабочего набора: {str(e)}"
        )
    
    finally:
        # Очистка временной директории
        if workspace_dir and workspace_dir.exists():
            try:
                shutil.rmtree(workspace_dir)
                logger.info(f"🗑️  Временная директория удалена: {workspace_dir.name}")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось удалить {workspace_dir}: {e}")
