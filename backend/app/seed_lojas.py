"""Cadastro das lojas do MVP no banco (issue #67).

Idempotente: pode rodar várias vezes; só insere o que ainda não existe
(a unicidade é pelo domínio normalizado, como em POST /lojas).

Uso (a partir da pasta backend/):

    python -m app.seed_lojas

Alternativa direta no Supabase: app/db_scripts/seed_lojas.sql
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.loja import Loja
from app.utils.urls import normalizar_dominio

# (nome, domínio). O domínio precisa casar com um extrator de coleta_service.EXTRATORES.
LOJAS_MVP: tuple[tuple[str, str], ...] = (
    ("Mercado Livre", "mercadolivre.com.br"),
    ("Magazine Luiza", "magazineluiza.com.br"),
    ("Amazon Brasil", "amazon.com.br"),
    ("Kabum", "kabum.com.br"),
    ("Books to Scrape (demo)", "books.toscrape.com"),
)


def semear_lojas(db: Session) -> list[Loja]:
    """Insere as lojas do MVP que faltam e devolve as criadas agora."""
    criadas: list[Loja] = []
    for nome, dominio in LOJAS_MVP:
        dominio = normalizar_dominio(dominio)
        if db.scalar(select(Loja).where(Loja.dominio == dominio)) is not None:
            continue
        loja = Loja(nome=nome, dominio=dominio)
        db.add(loja)
        criadas.append(loja)
    db.commit()
    for loja in criadas:
        db.refresh(loja)
    return criadas


def main() -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        criadas = semear_lojas(db)
    finally:
        db.close()
    if criadas:
        for loja in criadas:
            print(f"Loja cadastrada: {loja.nome} ({loja.dominio})")
    else:
        print("Nenhuma loja nova: todas as lojas do MVP já estão cadastradas.")


if __name__ == "__main__":
    main()
