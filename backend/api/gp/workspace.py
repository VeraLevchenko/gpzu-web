"""
API endpoints для создания рабочего набора MapInfo.

Функционал:
- Парсинг выписки ЕГРН
- Пространственный анализ (поиск ОКС, ЗОУИТ)
- Генерация MIF/MID файлов
- Конвертация в TAB
- Создание WOR-файла
- Скачивание ZIP архива
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
import logging
import io
import zipfile
from pathlib import Path
import shutil

from parsers.egrn_parser import parse_egrn_xml
from generator.spatial_adapter import create_workspace_from_egrn
from generator.mif_writer import (
    create_parcel_mif,
    create_parcel_points_mif,
    create_building_zone_mif,
    create_oks_mif,
    create_zouit_mif,
    create_zouit_labels_mif,
    create_workspace_directory,
    get_project_base_dir,
    create_oks_labels_mif
)
from generator.mif_to_tab_converter import convert_all_mif_to_tab
from generator.wor_builder import create_workspace_wor
from api.auth import verify_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/workspace", tags=["workspace"])


@router.post("/create")
async def create_workspace(
    file: UploadFile = File(...),
    user: dict  = Depends(verify_credentials),
):
    """
    Создание полного рабочего набора MapInfo из выписки ЕГРН.
    
    Принимает XML выписку ЕГРН и возвращает ZIP архив с:
    - TAB/DAT/ID/MAP файлами всех слоёв
    - WOR-файлом рабочего набора
    - README.txt с описанием
    
    Returns:
        ZIP архив с рабочим набором
    
    Raises:
        400: Неверный формат файла
        500: Ошибка генерации
    """
    
    # Проверка формата
    if not file.filename or not file.filename.lower().endswith('.xml'):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате XML"
        )
    
    try:
        # ========== ШАГ 1: Парсинг ЕГРН ========== #
        logger.info(f"Workspace: парсинг ЕГРН {file.filename}")
        
        content = await file.read()
        egrn_data = parse_egrn_xml(content)
        
        logger.info(f"Workspace: КН={egrn_data.cadnum}, точек={len(egrn_data.coordinates)}")
        
        # ✅ ДОБАВЛЕНО: Логирование площади после парсинга
        logger.info(f"🔍 Workspace: Площадь из ЕГРН = '{egrn_data.area}' (тип: {type(egrn_data.area).__name__})")
        logger.info(f"🔍 Workspace: Адрес = '{egrn_data.address}'")
        
        # ========== ШАГ 2: Пространственный анализ ========== #
        logger.info("Workspace: пространственный анализ")
        
        workspace = create_workspace_from_egrn(egrn_data)
        
        logger.info(f"Workspace: найдено ОКС={len(workspace.capital_objects)}, ЗОУИТ={len(workspace.zouit)}")
        
        # ✅ ДОБАВЛЕНО: Логирование площади после создания workspace
        logger.info(f"🔍 Workspace: parcel.area = {workspace.parcel.area}")
        logger.info(f"🔍 Workspace: parcel.geometry.area = {workspace.parcel.geometry.area:.2f}")
        
        # ========== ШАГ 3: Создание рабочей директории ========== #
        logger.info("Workspace: создание структуры папок")
        
        workspace_dir = create_workspace_directory(workspace.parcel.cadnum)
        project_base = get_project_base_dir(workspace_dir)
        
        # ========== ШАГ 4: Генерация MIF/MID файлов ========== #
        logger.info("Workspace: генерация MIF/MID")
        
        create_parcel_mif(workspace.parcel, project_base)
        create_parcel_points_mif(workspace.parcel, project_base)
        create_building_zone_mif(workspace.building_zone, workspace.parcel.cadnum, project_base)
        
        has_oks = False
        if workspace.capital_objects:
            result_oks = create_oks_mif(workspace.capital_objects, project_base)
            has_oks = result_oks is not None
        
        # ✅ ДОБАВЛЕНО: слой подписей ОКС (точки в центре пересечения ОКС с участком)
        has_oks_labels = False
        if has_oks and workspace.parcel.geometry:
            result_oks_labels = create_oks_labels_mif(
                capital_objects=workspace.capital_objects,
                parcel_geometry=workspace.parcel.geometry,
                output_dir=project_base,
                filename="подписи_окс",
            )
            has_oks_labels = result_oks_labels is not None
        
        zouit_files = None
        has_zouit_labels = False
        if workspace.zouit:
            zouit_files = create_zouit_mif(workspace.zouit, project_base)
            
            # Создаем слой подписей ЗОУИТ
            if zouit_files and workspace.parcel.geometry:
                result_labels = create_zouit_labels_mif(
                    zouit_list=workspace.zouit,
                    parcel_geometry=workspace.parcel.geometry,
                    output_dir=project_base
                )
                has_zouit_labels = result_labels is not None
        
        # ========== ШАГ 5: Конвертация MIF → TAB ========== #
        logger.info("Workspace: конвертация MIF → TAB")
        
        tab_files = convert_all_mif_to_tab(project_base, remove_mif=True, method='auto')
        logger.info(f"Workspace: конвертировано {len(tab_files)} файлов")
        
        # ========== ШАГ 6: Создание WOR-файла ========== #
        logger.info("Workspace: создание WOR-файла")
        
        wor_path = create_workspace_wor(
            workspace_dir=workspace_dir,
            cadnum=workspace.parcel.cadnum,
            has_oks=has_oks,
            has_oks_labels=has_oks_labels,
            zouit_files=zouit_files,
            has_zouit_labels=has_zouit_labels,
            address=workspace.parcel.address,
            area=workspace.parcel.area,  # ✅ ДОБАВЛЕНО: площадь из ЕГРН
            specialist_name=(user.get("fio") or user.get("username") or ""),
            zouit_list=workspace.zouit,
        )
        
        logger.info(f"Workspace: WOR создан {wor_path.name}")
        
        # ========== ШАГ 7: Создание ZIP архива ========== #
        logger.info("Workspace: упаковка в ZIP")
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Добавляем WOR-файл
            zip_file.write(wor_path, wor_path.name)
            
            # Добавляем README
            readme_path = workspace_dir / "README.txt"
            if readme_path.exists():
                zip_file.write(readme_path, "README.txt")
            
            # Добавляем все файлы из База_проекта
            for file_path in project_base.glob("*.*"):
                arcname = f"База_проекта/{file_path.name}"
                zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        # Очистка временных файлов
        try:
            shutil.rmtree(workspace_dir)
        except Exception as e:
            logger.warning(f"Не удалось удалить временную папку: {e}")
        
        # Формируем имя ZIP файла
        cadnum_safe = workspace.parcel.cadnum.replace(":", "-")
        zip_filename = f"GP_Graphics_{cadnum_safe}.zip"
        
        logger.info(f"Workspace: отправка архива {zip_filename}")
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"'
            }
        )
        
    except RuntimeError as ex:
        logger.error(f"Workspace: ошибка генерации: {ex}")
        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )
    except Exception as ex:
        logger.exception(f"Workspace: неожиданная ошибка: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка создания рабочего набора: {str(ex)}"
        )
