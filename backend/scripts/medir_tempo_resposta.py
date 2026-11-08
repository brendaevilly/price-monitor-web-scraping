"""Mede o tempo de resposta das rotas principais (RNF01).

Meta: até 2 segundos em condições normais, sem contar o scraping.

Rotas medidas: POST /usuarios/login, GET /produtos,
GET /produtos/{id}/historico e GET /produtos/{id}/analise.

Roda contra uma API já no ar (local, Docker ou a hospedada), com um usuário
real que já tenha ao menos um produto monitorado:

    python scripts/medir_tempo_resposta.py --email ana@exemplo.com --senha '***'
    python scripts/medir_tempo_resposta.py --url https://minha-api --email ... --senha ... \\
        --repeticoes 30 --saida ../docs/desempenho-medicao.md

Também aceita --token (pula o login, que então aparece como "não medido") e
--produto-id (senão usa o produto com mais coletas entre os primeiros 10).
Código de saída 1 se o p95 de alguma rota passar da meta.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

import requests

META_SEGUNDOS = 2.0


@dataclass
class Medicao:
    rota: str
    tempos: list[float] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    @property
    def p95(self) -> float:
        if not self.tempos:
            return float("nan")
        ordenados = sorted(self.tempos)
        indice = max(0, round(0.95 * len(ordenados)) - 1)
        return ordenados[indice]

    @property
    def status(self) -> str:
        if self.erros and not self.tempos:
            return "ERRO"
        if self.erros:
            return "ERRO PARCIAL"
        return "OK" if self.p95 <= META_SEGUNDOS else "ACIMA DA META"


def _medir(sessao: requests.Session, medicao: Medicao, metodo: str, url: str, repeticoes: int, **kw):
    """Descarta a 1a chamada (aquecimento: conexão, pool, cache de plano) e mede as demais."""
    ultima = None
    for i in range(repeticoes + 1):
        inicio = time.perf_counter()
        try:
            resp = sessao.request(metodo, url, timeout=30, **kw)
        except requests.RequestException as exc:
            medicao.erros.append(f"{type(exc).__name__}: {exc}")
            continue
        duracao = time.perf_counter() - inicio
        if resp.status_code >= 400:
            medicao.erros.append(f"HTTP {resp.status_code}: {resp.text[:120]}")
            continue
        ultima = resp
        if i > 0:
            medicao.tempos.append(duracao)
    return ultima


def _fmt(v: float) -> str:
    return "-" if v != v else f"{v * 1000:.0f} ms"


def _tabela(medicoes: list[Medicao], base_url: str, repeticoes: int, coletas: int | None) -> str:
    linhas = [
        f"Medição de {datetime.now():%d/%m/%Y %H:%M} em `{base_url}` "
        f"({repeticoes} repetições por rota"
        + (f", produto com {coletas} coletas" if coletas is not None else "")
        + f"; meta p95 ≤ {META_SEGUNDOS:.0f} s).",
        "",
        "| Rota | mín | média | p95 | máx | Resultado |",
        "|---|---|---|---|---|---|",
    ]
    for m in medicoes:
        if m.tempos:
            linhas.append(
                f"| {m.rota} | {_fmt(min(m.tempos))} | {_fmt(statistics.mean(m.tempos))} "
                f"| {_fmt(m.p95)} | {_fmt(max(m.tempos))} | {m.status} |"
            )
        else:
            linhas.append(f"| {m.rota} | - | - | - | - | {m.status} |")
    for m in medicoes:
        for e in sorted(set(m.erros)):
            linhas.append(f"\n- {m.rota}: {e}")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8000", help="URL base da API")
    ap.add_argument("--email")
    ap.add_argument("--senha")
    ap.add_argument("--token", help="access token já obtido (pula o login)")
    ap.add_argument("--produto-id", help="produto a usar em histórico/análise")
    ap.add_argument("--repeticoes", type=int, default=20)
    ap.add_argument("--saida", help="arquivo .md para gravar a tabela de resultados")
    args = ap.parse_args()

    if not args.token and not (args.email and args.senha):
        ap.error("informe --email e --senha, ou --token")

    base = args.url.rstrip("/")
    sessao = requests.Session()
    medicoes: list[Medicao] = []

    token = args.token
    login = Medicao("POST /usuarios/login")
    if args.email and args.senha:
        resp = _medir(sessao, login, "POST", f"{base}/usuarios/login", args.repeticoes,
                      json={"email": args.email, "senha": args.senha})
        if resp is not None and not token:
            token = resp.json()["access_token"]
    else:
        login.erros.append("não medido (--token informado)")
    medicoes.append(login)

    if not token:
        print("Não foi possível obter token.", file=sys.stderr)
        print(_tabela(medicoes, base, args.repeticoes, None))
        return 1
    sessao.headers["Authorization"] = f"Bearer {token}"

    lista = Medicao("GET /produtos")
    resp = _medir(sessao, lista, "GET", f"{base}/produtos", args.repeticoes)
    medicoes.append(lista)

    produto_id, coletas = args.produto_id, None
    if produto_id is None and resp is not None and resp.json():
        # Escolhe o produto com mais coletas: é o pior caso para histórico/análise.
        melhor = -1
        for p in resp.json()[:10]:
            h = sessao.get(f"{base}/produtos/{p['produto_id']}/historico", timeout=30)
            if h.ok and len(h.json()["coletas"]) > melhor:
                melhor, produto_id = len(h.json()["coletas"]), p["produto_id"]
    if produto_id is None:
        print("Nenhum produto monitorado para medir histórico/análise.", file=sys.stderr)
        for rota in ("historico", "analise"):
            m = Medicao(f"GET /produtos/{{id}}/{rota}")
            m.erros.append("sem produto monitorado")
            medicoes.append(m)
    else:
        for rota in ("historico", "analise"):
            m = Medicao(f"GET /produtos/{{id}}/{rota}")
            r = _medir(sessao, m, "GET", f"{base}/produtos/{produto_id}/{rota}", args.repeticoes)
            if rota == "historico" and r is not None:
                coletas = len(r.json()["coletas"])
            medicoes.append(m)

    tabela = _tabela(medicoes, base, args.repeticoes, coletas)
    print(tabela)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(tabela + "\n")
    return 0 if all(m.status in ("OK",) or "não medido" in "".join(m.erros) for m in medicoes) else 1


if __name__ == "__main__":
    sys.exit(main())
