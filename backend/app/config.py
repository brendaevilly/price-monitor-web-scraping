<<<<<<< HEAD
import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
# utf-8-sig remove o BOM que o Bloco de Notas do Windows coloca no .env
load_dotenv(_BACKEND_DIR / ".env", encoding="utf-8-sig")


def _env(nome: str, padrao: str = "") -> str:
    return os.getenv(nome, padrao).strip().strip('"').strip("'")


def _supabase_url() -> str:
    """Aceita a URL do projeto, mesmo se vier com /rest/v1 colado do painel."""
    url = _env("SUPABASE_URL").rstrip("/")
    for sufixo in ("/rest/v1", "/auth/v1", "/storage/v1"):
        if url.endswith(sufixo):
            url = url[: -len(sufixo)]
    return url.rstrip("/")


class Settings:
    DATABASE_URL: str = _env("DATABASE_URL")
    SUPABASE_URL: str = _supabase_url()
    SUPABASE_SECRET_KEY: str = _env("SUPABASE_SECRET_KEY")

    # RNF08 — intervalo mínimo entre requisições e limite de tentativas do robô
    COLETA_INTERVALO_MINIMO_SEGUNDOS: float = float(
        os.getenv("COLETA_INTERVALO_MINIMO_SEGUNDOS", "2")
    )
    COLETA_MAX_TENTATIVAS: int = int(os.getenv("COLETA_MAX_TENTATIVAS", "3"))
    COLETA_TIMEOUT_SEGUNDOS: float = float(os.getenv("COLETA_TIMEOUT_SEGUNDOS", "15"))

    # Issue #105 — o frete mostrado na página entra na medição do preço.
    COLETA_INCLUIR_FRETE: bool = os.getenv("COLETA_INCLUIR_FRETE", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
        "on",
    }

    # Issue #103 — Selenium para passar por "você é um robô?" nos sites.
    # "auto": tenta com requests e só abre o Chrome se a loja bloquear;
    # "sempre": usa sempre o Chrome; "desligado": só requests (como antes).
    COLETA_SELENIUM_MODO: str = _env("COLETA_SELENIUM_MODO", "auto").lower()
    COLETA_SELENIUM_ESPERA_DESAFIO_SEGUNDOS: float = float(
        os.getenv("COLETA_SELENIUM_ESPERA_DESAFIO_SEGUNDOS", "10")
    )
    # Caminho do Chrome/Chromium, se não estiver no PATH (ex.: /usr/bin/chromium).
    COLETA_SELENIUM_CHROME_BIN: str = _env("COLETA_SELENIUM_CHROME_BIN")

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
=======
import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
# utf-8-sig remove o BOM que o Bloco de Notas do Windows coloca no .env
load_dotenv(_BACKEND_DIR / ".env", encoding="utf-8-sig")


def _env(nome: str, padrao: str = "") -> str:
    return os.getenv(nome, padrao).strip().strip('"').strip("'")


def _supabase_url() -> str:
    """Aceita a URL do projeto, mesmo se vier com /rest/v1 colado do painel."""
    url = _env("SUPABASE_URL").rstrip("/")
    for sufixo in ("/rest/v1", "/auth/v1", "/storage/v1"):
        if url.endswith(sufixo):
            url = url[: -len(sufixo)]
    return url.rstrip("/")


class Settings:
    DATABASE_URL: str = _env("DATABASE_URL")
    SUPABASE_URL: str = _supabase_url()
    SUPABASE_SECRET_KEY: str = _env("SUPABASE_SECRET_KEY")

    # Origens do frontend autorizadas a chamar a API pelo navegador (separadas por vírgula).
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]

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

    # RN06 / RN09 / RN10 / UC11 — análise estatística do histórico
    # Faixas de queda sobre a média histórica: pequena >= 5%, relevante >= 10%, grande >= 20%
    ANALISE_LIMIAR_PEQUENA_PERCENTUAL: float = float(
        os.getenv("ANALISE_LIMIAR_PEQUENA_PERCENTUAL", "5")
    )
    ANALISE_LIMIAR_RELEVANTE_PERCENTUAL: float = float(
        os.getenv("ANALISE_LIMIAR_RELEVANTE_PERCENTUAL", "10")
    )
    ANALISE_LIMIAR_GRANDE_PERCENTUAL: float = float(
        os.getenv("ANALISE_LIMIAR_GRANDE_PERCENTUAL", "20")
    )
    # Mínimo de coletas anteriores válidas para comparar (RN10)
    ANALISE_MIN_COLETAS_COMPARACAO: int = int(
        os.getenv("ANALISE_MIN_COLETAS_COMPARACAO", "3")
    )
    # Janela da média histórica em dias (0 = todo o histórico)
    ANALISE_JANELA_DIAS: int = int(os.getenv("ANALISE_JANELA_DIAS", "30"))

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
>>>>>>> fc95810ab81209f9418926a060684f6f9af4bddb
