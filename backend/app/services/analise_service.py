"""Serviço de análise estatística do histórico de preços (UC11).

Compara o preço mais recente de um produto com a coleta anterior e com a
média histórica, e classifica a variação conforme as faixas do UC11:

    Pequena queda  : 5%  <= variação < 10%
    Queda relevante: 10% <= variação < 20%
    Grande queda   : variação >= 20%

Nota de decisão de projeto (vale confirmar com o grupo): a especificação de
requisitos (RN06) descreve um único limiar de 10%, comparando o preço atual
com a coleta anterior OU com a média histórica. Já o UC11 (entrega mais
recente) descreve três faixas, usando a média histórica como referência. Esta
implementação segue o UC11, por ser o documento mais específico e recente;
a comparação com a coleta anterior (RF12) é calculada e devolvida, mas não
decide a faixa de classificação.

RN10 ("quantidade mínima de dados") não define um número exato. Adotou-se
MIN_AMOSTRAS_MEDIA = 3 coletas anteriores válidas como mínimo para calcular
uma média confiável — ajustável conforme o grupo decidir.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Protocol


class ClassificacaoQueda(str, enum.Enum):
    SEM_DADOS = "sem_dados"          # 3a: histórico insuficiente para calcular a média
    SEM_QUEDA = "sem_queda"          # preço subiu, ficou igual, ou variação < 5% (4a)
    PEQUENA = "pequena_queda"        # 5% a 9%
    RELEVANTE = "queda_relevante"    # 10% a 19%
    GRANDE = "grande_queda"          # >= 20%


class ColetaComPreco(Protocol):
    """O que o serviço precisa de cada item do histórico (duck typing, para
    aceitar tanto o modelo HistoricoPreco do SQLAlchemy quanto objetos de
    teste simples, sem depender do banco)."""

    preco: Decimal
    data_hora_coleta: object  # comparável (datetime); ignorado em testes simples
    coleta_valida: bool


@dataclass(frozen=True)
class ResultadoAnalise:
    preco_atual: Decimal
    media_historica: Decimal | None
    amostras_media: int
    variacao_percentual_media: float | None
    variacao_percentual_anterior: float | None
    classificacao: ClassificacaoQueda

    @property
    def queda_relevante(self) -> bool:
        """True quando a queda está nas faixas 'relevante' ou 'grande'
        (>= 10% em relação à média histórica). Usado pelo AlertaService
        para decidir se um e-mail deve ser disparado (RF15)."""
        return self.classificacao in (ClassificacaoQueda.RELEVANTE, ClassificacaoQueda.GRANDE)


class AnaliseService:
    """«service» — RNF07: opera sobre o histórico sem manter estado de negócio."""

    def __init__(self, limiar_queda_percentual: float = 5.0, min_amostras_media: int = 3):
        # Abaixo deste percentual a variação não é considerada queda (UC11, 4a).
        self.limiar_queda_percentual = limiar_queda_percentual
        # RN10: mínimo de coletas anteriores válidas para confiar na média.
        self.min_amostras_media = min_amostras_media

    # --- auxiliares internos -------------------------------------------------

    @staticmethod
    def _historico_valido_ordenado(historico: Iterable[ColetaComPreco]) -> list[ColetaComPreco]:
        """RN09: ignora coletas inválidas ou com preço <= 0; RN10: assume que
        a lista já pertence a um único produto. Ordena do mais antigo ao mais
        recente."""
        validos = [
            c for c in historico
            if getattr(c, "coleta_valida", True) and c.preco is not None and c.preco > 0
        ]
        return sorted(validos, key=lambda c: c.data_hora_coleta)

    @staticmethod
    def _variacao_percentual(referencia: Decimal, atual: Decimal) -> float:
        """Percentual de queda de 'atual' em relação a 'referencia'.
        Positivo = queda; negativo = alta."""
        return float((referencia - atual) / referencia * 100)

    # --- métodos do diagrama de classes --------------------------------------

    def comparar_com_coleta_anterior(self, historico: Iterable[ColetaComPreco]) -> float | None:
        """RF12: variação percentual entre o preço atual e a coleta válida
        imediatamente anterior. None se não houver coleta anterior."""
        validos = self._historico_valido_ordenado(historico)
        if len(validos) < 2:
            return None
        atual, anterior = validos[-1], validos[-2]
        return self._variacao_percentual(anterior.preco, atual.preco)

    def comparar_com_media(self, historico: Iterable[ColetaComPreco]) -> float | None:
        """RF12: variação percentual entre o preço atual e a média das
        coletas anteriores válidas. None se não houver amostras suficientes
        (RN10)."""
        validos = self._historico_valido_ordenado(historico)
        if not validos:
            return None
        anteriores = validos[:-1]
        if len(anteriores) < self.min_amostras_media:
            return None
        media = sum(c.preco for c in anteriores) / len(anteriores)
        return self._variacao_percentual(media, validos[-1].preco)

    def identificar_queda_relevante(self, historico: Iterable[ColetaComPreco]) -> bool:
        """Atalho booleano (assinatura do diagrama de classes) — usa o
        resultado completo de `classificar` por trás."""
        return self.classificar(historico).queda_relevante

    # --- classificação completa (UC11) ---------------------------------------

    def classificar(self, historico: Iterable[ColetaComPreco]) -> ResultadoAnalise:
        """Fluxo principal do UC11: compara o preço atual com a média
        histórica e classifica a queda em pequena/relevante/grande."""
        validos = self._historico_valido_ordenado(historico)
        if not validos:
            raise ValueError(
                "Histórico vazio ou sem coletas válidas: nada para analisar."
            )

        atual = validos[-1]
        anteriores = validos[:-1]

        variacao_anterior = self.comparar_com_coleta_anterior(historico)

        # 3a. Dados históricos insuficientes: não classifica.
        if len(anteriores) < self.min_amostras_media:
            return ResultadoAnalise(
                preco_atual=atual.preco,
                media_historica=None,
                amostras_media=len(anteriores),
                variacao_percentual_media=None,
                variacao_percentual_anterior=variacao_anterior,
                classificacao=ClassificacaoQueda.SEM_DADOS,
            )

        media = sum(c.preco for c in anteriores) / len(anteriores)
        variacao_media = self._variacao_percentual(media, atual.preco)

        # 4a. Preço subiu/igual ou caiu menos que o limiar: não é queda.
        if variacao_media < self.limiar_queda_percentual:
            classificacao = ClassificacaoQueda.SEM_QUEDA
        elif variacao_media < 10:
            classificacao = ClassificacaoQueda.PEQUENA
        elif variacao_media < 20:
            classificacao = ClassificacaoQueda.RELEVANTE
        else:
            classificacao = ClassificacaoQueda.GRANDE

        return ResultadoAnalise(
            preco_atual=atual.preco,
            media_historica=media,
            amostras_media=len(anteriores),
            variacao_percentual_media=variacao_media,
            variacao_percentual_anterior=variacao_anterior,
            classificacao=classificacao,
        )
