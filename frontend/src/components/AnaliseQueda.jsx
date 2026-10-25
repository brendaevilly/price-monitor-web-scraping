import { CLASSIFICACAO_UC11 } from '../services/produtoService';

function formatarPercentual(valor) {
  if (valor === null || valor === undefined) return '—';
  return `${valor.toFixed(2).replace('.', ',')}%`;
}

function formatarPreco(valor) {
  if (valor === null || valor === undefined) return '—';
  return Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

// Resultado do UC11 para um produto (objeto devolvido por GET /produtos/{id}/analise).
function AnaliseQueda({ analise }) {
  const info = CLASSIFICACAO_UC11[analise.classificacao];
  const faltam = Math.max(analise.amostras_minimas - analise.amostras_media, 0);

  return (
    <div className={`analise analise-${analise.classificacao}`}>
      <span className="analise-badge">{info.rotulo}</span>
      <p className="analise-faixa">{info.faixa}</p>
      {analise.classificacao === 'sem_dados' && analise.preco_atual !== null && (
        <p className="analise-aviso">
          Faltam {faltam} coleta{faltam === 1 ? '' : 's'} para calcular a média histórica.
        </p>
      )}
      <dl className="analise-valores">
        <dt>Preço atual</dt>
        <dd>{formatarPreco(analise.preco_atual)}</dd>
        <dt>Média histórica</dt>
        <dd>{formatarPreco(analise.media_historica)}</dd>
        <dt>Variação vs. média</dt>
        <dd>{formatarPercentual(analise.variacao_percentual_media)}</dd>
        <dt>Variação vs. coleta anterior</dt>
        <dd>{formatarPercentual(analise.variacao_percentual_anterior)}</dd>
      </dl>
    </div>
  );
}

export default AnaliseQueda;
