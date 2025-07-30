from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.models.message_log import MessageLog, Report
from backend.app.schemas.message_log import (
    MessageLog as MessageLogSchema,
    MessageLogCreate,
    Report as ReportSchema,
    ReportCreate,
)
from backend.app.services.message_log_service import (
    get_message_logs,
    get_message_log_by_id,
    create_message_log,
)
from backend.app.services.report_service import (
    get_reports,
    get_report_by_id,
    create_report,
    update_report_status,
)

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/messages/", response_model=List[MessageLogSchema])
async def read_message_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    message_type: Optional[str] = None,
    direction: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список логов сообщений с возможностью фильтрации.
    """
    filters = {}
    if user_id is not None:
        filters["user_id"] = user_id
    if message_type is not None:
        filters["message_type"] = message_type
    if direction is not None:
        filters["direction"] = direction
    if start_date is not None:
        filters["start_date"] = start_date
    if end_date is not None:
        filters["end_date"] = end_date
        
    logs = await get_message_logs(db, skip=skip, limit=limit, filters=filters)
    return logs


@router.get("/messages/{log_id}", response_model=MessageLogSchema)
async def read_message_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить лог сообщения по ID.
    """
    log = await get_message_log_by_id(db, log_id=log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Message log not found")
    return log


@router.post("/messages/", response_model=MessageLogSchema, status_code=status.HTTP_201_CREATED)
async def create_message_log_api(
    log: MessageLogCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новый лог сообщения.
    """
    return await create_message_log(db=db, log=log)


# Маршруты для отчетов
@router.get("/reports/", response_model=List[ReportSchema])
async def read_reports(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список отчетов с возможностью фильтрации.
    """
    filters = {}
    if user_id is not None:
        filters["user_id"] = user_id
    if report_type is not None:
        filters["report_type"] = report_type
    if status is not None:
        filters["status"] = status
    if start_date is not None:
        filters["start_date"] = start_date
    if end_date is not None:
        filters["end_date"] = end_date
        
    reports = await get_reports(db, skip=skip, limit=limit, filters=filters)
    return reports


@router.get("/reports/{report_id}", response_model=ReportSchema)
async def read_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить отчет по ID.
    """
    report = await get_report_by_id(db, report_id=report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/reports/", response_model=ReportSchema, status_code=status.HTTP_201_CREATED)
async def create_report_api(
    report: ReportCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новый отчет.
    """
    return await create_report(db=db, report=report)


@router.put("/reports/{report_id}/status", response_model=ReportSchema)
async def update_report_status_api(
    report_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить статус отчета.
    """
    db_report = await get_report_by_id(db, report_id=report_id)
    if db_report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if status not in ["pending", "processing", "completed", "failed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    return await update_report_status(db=db, report_id=report_id, status=status)
