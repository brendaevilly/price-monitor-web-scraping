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


settings = Settings()