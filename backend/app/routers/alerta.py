from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.models.alerta import Alerta
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.schemas.alerta import AlertaOut, ProdutoResumoOut

router = APIRouter(prefix="/alertas", tags=["Alerta"])


@router.get(
    "",
    response_model=list[AlertaOut],
    summary="Listar meus alertas disparados (UC14)",
)
def listar_alertas(
    limite: int = Query(50, ge=1, le=200, description="Máximo de alertas devolvidos."),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    # RNF03: só devolve os alertas do usuário autenticado.
    linhas = db.execute(
        select(Alerta, Produto)
        .join(Produto, Produto.id == Alerta.produto_id)
        .where(Alerta.usuario_id == usuario.id)
        .order_by(Alerta.data_envio.desc(), Alerta.id)
        .limit(limite)
    ).all()
    return [
        AlertaOut(
            id=a.id,
            tipo=a.tipo,
            data_envio=a.data_envio,
            mensagem=a.mensagem,
            produto=ProdutoResumoOut.model_validate(p),
        )
        for a, p in linhas
    ]