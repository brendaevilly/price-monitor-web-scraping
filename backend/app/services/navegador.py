"""Navegador real (Selenium) para o robô de coleta (issue #103).

Algumas lojas respondem ao `requests` com a tela "você é um robô?" (captcha,
verificação de tráfego, desafio JS). Um Chrome headless executa o JavaScript da
página e se apresenta como um navegador comum, o que resolve boa parte dos
desafios automáticos (ex.: "Verificando seu navegador..."). Captchas que exigem
um humano (digitar caracteres, clicar em imagens) continuam sem solução: nesse
caso a coleta falha e é registrada como inválida (RN09), como antes.

O `ColetaService` usa este módulo só quando precisa (modo "auto") ou sempre
(modo "sempre"); ver `COLETA_SELENIUM_MODO` em config.py.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

from app.config import settings

logger = logging.getLogger(__name__)

MODO_DESLIGADO = "desligado"
MODO_AUTO = "auto"
MODO_SEMPRE = "sempre"
MODOS_VALIDOS = {MODO_DESLIGADO, MODO_AUTO, MODO_SEMPRE}

# Esconde o sinal mais óbvio de automação (`navigator.webdriver`) antes de a
# página carregar. Roda via CDP em cada novo documento.
_SCRIPT_ANTIDETECCAO = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en']});
"""


class NavegadorIndisponivel(RuntimeError):
    """Selenium/Chrome não está instalado ou não conseguiu iniciar."""


@dataclass
class RespostaNavegador:
    """Mesma interface mínima de `requests.Response` usada pelo ColetaService."""

    text: str
    status_code: int = 200
    url: str = ""

    def raise_for_status(self) -> None:  # o navegador não expõe o status HTTP
        return None


def modo_selenium() -> str:
    modo = (settings.COLETA_SELENIUM_MODO or MODO_AUTO).strip().lower()
    return modo if modo in MODOS_VALIDOS else MODO_AUTO


def _criar_driver(user_agent: str):
    """Cria um Chrome headless. Import tardio: selenium só é exigido se usado."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise NavegadorIndisponivel(
            "Selenium não instalado (pip install selenium)."
        ) from exc

    opcoes = Options()
    opcoes.add_argument("--headless=new")
    opcoes.add_argument("--no-sandbox")  # necessário em container (Docker)
    opcoes.add_argument("--disable-dev-shm-usage")
    opcoes.add_argument("--disable-gpu")
    opcoes.add_argument("--window-size=1366,768")
    opcoes.add_argument("--lang=pt-BR")
    opcoes.add_argument(f"--user-agent={user_agent}")
    opcoes.add_argument("--disable-blink-features=AutomationControlled")
    opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])
    opcoes.add_experimental_option("useAutomationExtension", False)
    # Não espera imagens/anúncios terminarem: o preço vem no HTML.
    opcoes.page_load_strategy = "eager"
    if settings.COLETA_SELENIUM_CHROME_BIN:
        opcoes.binary_location = settings.COLETA_SELENIUM_CHROME_BIN

    try:
        driver = webdriver.Chrome(options=opcoes)  # Selenium Manager acha o driver
    except Exception as exc:  # WebDriverException, falta do Chrome, etc.
        raise NavegadorIndisponivel(f"Não foi possível iniciar o Chrome: {exc}") from exc

    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": _SCRIPT_ANTIDETECCAO}
        )
    except Exception:  # CDP é um reforço; sem ele o Chrome ainda funciona
        logger.debug("CDP indisponível; seguindo sem o script anti-detecção.")
    driver.set_page_load_timeout(settings.COLETA_TIMEOUT_SEGUNDOS)
    return driver


def buscar_pagina(
    url: str,
    user_agent: str,
    pagina_bloqueada: Callable[[str], bool],
    criar_driver: Optional[Callable[[str], object]] = None,
) -> RespostaNavegador:
    """Abre `url` num Chrome headless e devolve o HTML renderizado.

    Se a página aparecer como desafio de robô, espera até
    `COLETA_SELENIUM_ESPERA_DESAFIO_SEGUNDOS` para ele se resolver sozinho
    (desafios por JS costumam liberar a página em poucos segundos). Se continuar
    bloqueada, devolve o HTML mesmo assim: quem chama decide que é falha.

    `criar_driver` existe para os testes injetarem um navegador falso.
    """
    driver = (criar_driver or _criar_driver)(user_agent)
    try:
        try:
            driver.get(url)
        except Exception as exc:
            # Timeout de carregamento: o HTML parcial costuma já ter o preço.
            if "timeout" not in type(exc).__name__.lower():
                raise
            logger.warning("Timeout ao carregar %s; usando o HTML parcial.", url)

        limite = time.monotonic() + max(0.0, settings.COLETA_SELENIUM_ESPERA_DESAFIO_SEGUNDOS)
        html = driver.page_source or ""
        while pagina_bloqueada(html) and time.monotonic() < limite:
            time.sleep(1.0)
            html = driver.page_source or ""

        return RespostaNavegador(
            text=html,
            url=getattr(driver, "current_url", url) or url,
        )
    finally:
        try:
            driver.quit()
        except Exception:  # pragma: no cover
            logger.debug("Falha ao encerrar o navegador.", exc_info=True)
