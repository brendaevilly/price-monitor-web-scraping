import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")

    # RNF08 — intervalo mínimo entre requisições e limite de tentativas do robô
    COLETA_INTERVALO_MINIMO_SEGUNDOS: float = float(
        os.getenv("COLETA_INTERVALO_MINIMO_SEGUNDOS", "2")
    )
    COLETA_MAX_TENTATIVAS: int = int(os.getenv("COLETA_MAX_TENTATIVAS", "3"))
    COLETA_TIMEOUT_SEGUNDOS: float = float(os.getenv("COLETA_TIMEOUT_SEGUNDOS", "15"))

    # RF06 — agendamento da coleta periódica (APScheduler)
    COLETA_SCHEDULER_HABILITADO: bool = os.getenv(
        "COLETA_SCHEDULER_HABILITADO", "true"
    ).strip().lower() in {"1", "true", "yes", "sim", "on"}
    COLETA_SCHEDULER_INTERVALO_MINUTOS: int = int(
        os.getenv("COLETA_SCHEDULER_INTERVALO_MINUTOS", "60")
    )
    _intervalo_segundos = os.getenv("COLETA_SCHEDULER_INTERVALO_SEGUNDOS", "").strip()
    COLETA_SCHEDULER_INTERVALO_SEGUNDOS: int | None = (
        int(_intervalo_segundos) if _intervalo_segundos else None
    )
    COLETA_SCHEDULER_EXECUTAR_NO_STARTUP: bool = os.getenv(
        "COLETA_SCHEDULER_EXECUTAR_NO_STARTUP", "false"
    ).strip().lower() in {"1", "true", "yes", "sim", "on"}

    # RF15 / RF16 — alerta por e-mail (RN07, RN08, RN11)
    ALERTA_QUEDA_MINIMA_PERCENTUAL: float = float(
        os.getenv("ALERTA_QUEDA_MINIMA_PERCENTUAL", "5")
    )
    ALERTA_INTERVALO_REENVIOS_HORAS: int = int(
        os.getenv("ALERTA_INTERVALO_REENVIOS_HORAS", "24")
    )
    ALERTA_SMTP_DRY_RUN: bool = os.getenv(
        "ALERTA_SMTP_DRY_RUN", "false"
    ).strip().lower() in {"1", "true", "yes", "sim", "on"}
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    SMTP_USAR_TLS: bool = os.getenv("SMTP_USAR_TLS", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
        "on",
    }


settings = Settings()