"""Agendamento da coleta periódica com APScheduler (RF06)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

JOB_ID = "coleta_periodica"

agendador = BackgroundScheduler(timezone="America/Sao_Paulo")


def executar_coleta_periodica() -> None:
    """Job do APScheduler: coleta todos os produtos ativos sem intervenção manual."""
    from app.database import SessionLocal
    from app.services.coleta_service import ColetaService

    logger.info("Iniciando coleta periódica de produtos ativos.")
    db = SessionLocal()
    try:
        resultados = ColetaService().executar_coleta_ativos(db)
        validas = sum(1 for item in resultados if item.coleta_valida)
        logger.info(
            "Coleta periódica concluída: %s produto(s), %s válida(s).",
            len(resultados),
            validas,
        )
    except Exception:
        logger.exception("Falha na coleta periódica.")
    finally:
        db.close()


def _montar_trigger(
    intervalo_minutos: int | None = None,
    intervalo_segundos: int | None = None,
) -> IntervalTrigger:
    segundos = (
        intervalo_segundos
        if intervalo_segundos is not None
        else settings.COLETA_SCHEDULER_INTERVALO_SEGUNDOS
    )
    if segundos is not None:
        return IntervalTrigger(seconds=max(1, segundos))
    minutos = (
        intervalo_minutos
        if intervalo_minutos is not None
        else settings.COLETA_SCHEDULER_INTERVALO_MINUTOS
    )
    return IntervalTrigger(minutes=max(1, minutos))


def iniciar_agendador(
    scheduler: BackgroundScheduler | None = None,
    *,
    intervalo_minutos: int | None = None,
    intervalo_segundos: int | None = None,
    executar_no_startup: bool | None = None,
    habilitado: bool | None = None,
    job_func=None,
) -> BackgroundScheduler:
    """Registra o job de intervalo e inicia o scheduler."""
    scheduler = scheduler or agendador
    if habilitado is None:
        habilitado = settings.COLETA_SCHEDULER_HABILITADO
    if not habilitado:
        logger.info("Agendador de coleta desabilitado por configuração.")
        return scheduler

    if executar_no_startup is None:
        executar_no_startup = settings.COLETA_SCHEDULER_EXECUTAR_NO_STARTUP

    trigger = _montar_trigger(intervalo_minutos, intervalo_segundos)
    proxima = datetime.now(timezone.utc) if executar_no_startup else None
    scheduler.add_job(
        job_func or executar_coleta_periodica,
        trigger=trigger,
        id=JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=proxima,
    )
    if not scheduler.running:
        scheduler.start()
    logger.info(
        "Agendador de coleta iniciado (%s). Próxima execução: %s.",
        trigger,
        getattr(scheduler.get_job(JOB_ID), "next_run_time", None),
    )
    return scheduler


def parar_agendador(scheduler: BackgroundScheduler | None = None) -> None:
    scheduler = scheduler or agendador
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Agendador de coleta encerrado.")


def status_agendador(scheduler: BackgroundScheduler | None = None) -> dict:
    scheduler = scheduler or agendador
    job = scheduler.get_job(JOB_ID)
    proxima = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "ativo": bool(scheduler.running and job is not None),
        "intervalo_minutos": settings.COLETA_SCHEDULER_INTERVALO_MINUTOS,
        "intervalo_segundos": settings.COLETA_SCHEDULER_INTERVALO_SEGUNDOS,
        "proxima_execucao": proxima,
    }
