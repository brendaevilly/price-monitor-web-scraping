import { useEffect, useState } from 'react';
import { IconeCalendario, IconeSetaBaixo } from './Icones';
import { buscarAnalise } from '../services/dashboardService';
import './AnaliseDetalhe.css';

/* UC07 + UC11: variação vs. coleta anterior e vs. média, selo de classificação
   e seletor da janela de comparação (GET /produtos/{id}/analise?janela_dias=). */

const JANELAS = [
  { valor: 7, rotulo: 'Últimos 7 dias' },
  { valor: 30, rotulo: 'Últimos 30 dias' },
  { valor: 90, rotulo: 'Últimos 90 dias' },
  { valor: 0, rotulo: 'Todo o histórico' },
];

const JANELA_PADRAO = 30;

// Só estas classificações exibem selo. `sem_dados` (UC07 3a / UC11 3a) nunca exibe.
const SELOS = {
  sem_queda: { rotulo: 'Sem queda', classe: 'neutro' },
  pequena_queda: { rotulo: 'Pequena queda', classe: 'pequena' },
  queda_relevante: { rotulo: 'Queda relevante', classe: 'relevante' },
  grande_queda: { rotulo: 'Grande queda', classe: 'grande' },
};

const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

// O Pydantic serializa Decimal como string ("3200.00"); os percentuais já vêm como número.
const num = (v) => (v === null || v === undefined ? null : Number(v));

function moeda(v) {
  const n = num(v);
  return n === null || Number.isNaN(n) ? '—' : brl.format(n);
}

// Duas casas: bate com o arredondamento do back e com os limiares (ex.: 9,96% não vira "10,0%").
const pct = (v) =>
  `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;

const rotuloJanela = (dias) =>
  dias === 0 ? 'todo o histórico' : `últimos ${dias} ${dias === 1 ? 'dia' : 'dias'}`;

// No back: positivo = queda (preço atual abaixo da referência); negativo = alta.
function descreverVariacao(valor, referencia) {
  const v = num(valor);
  if (v === null || Number.isNaN(v)) return null;
  if (v > 0) return { sentido: 'queda', seta: '▼', valor: pct(v), texto: `abaixo ${referencia}` };
  if (v < 0) return { sentido: 'alta', seta: '▲', valor: pct(Math.abs(v)), texto: `acima ${referencia}` };
  return { sentido: 'igual', seta: '=', valor: pct(0), texto: `igual ${referencia}` };
}

function CartaoVariacao({ titulo, variacao, vazio }) {
  return (
    <div className="analise-cartao">
      <dt>{titulo}</dt>
      <dd>
        {variacao ? (
          <>
            <span className={`analise-variacao analise-variacao-${variacao.sentido}`}>
              <span aria-hidden="true">{variacao.seta}</span> {variacao.valor}
            </span>
            <span className="analise-legenda">{variacao.texto}</span>
          </>
        ) : (
          <>
            <span className="analise-variacao analise-variacao-nenhuma">—</span>
            <span className="analise-legenda">{vazio}</span>
          </>
        )}
      </dd>
    </div>
  );
}

function ResultadoAnalise({ analise }) {
  const semDados = analise.classificacao === 'sem_dados';
  const selo = semDados ? null : SELOS[analise.classificacao] ?? null;
  const semColeta = num(analise.preco_atual) === null;
  const janela = rotuloJanela(analise.janela_dias);

  const anterior = descreverVariacao(analise.variacao_percentual_anterior, 'da coleta anterior');
  const media = descreverVariacao(analise.variacao_percentual_media, 'da média');

  let aviso = null;
  if (semColeta) {
    aviso = 'Ainda não há preços coletados para este produto.';
  } else if (semDados) {
    aviso =
      `Dados insuficientes para classificar a queda: ${analise.amostras_media} de ` +
      `${analise.amostras_minimas} coletas anteriores necessárias (${janela}). ` +
      'Tente uma janela maior ou aguarde novas coletas.';
  }

  return (
    <>
      <div className="analise-resumo">
        <p className="analise-preco">
          <span className="analise-rotulo">Preço atual</span>
          <strong>{moeda(analise.preco_atual)}</strong>
        </p>
        {selo && (
          <p className="analise-preco">
            <span className="analise-rotulo">Classificação da queda</span>
            <span className={`selo selo-${selo.classe}`}>{selo.rotulo}</span>
          </p>
        )}
      </div>

      {aviso && (
        <p className="aviso" role="status">
          {aviso}
        </p>
      )}

      {!semColeta && (
        <dl className="analise-variacoes">
          <CartaoVariacao
            titulo="Versus coleta anterior"
            variacao={anterior}
            vazio="Sem coleta anterior para comparar."
          />
          <CartaoVariacao
            titulo="Versus média"
            variacao={media}
            vazio="Sem dados suficientes para a média."
          />
        </dl>
      )}

      {!semColeta && !semDados && (
        <p className="analise-nota">
          Média de {moeda(analise.media_historica)} calculada com {analise.amostras_media}{' '}
          {analise.amostras_media === 1 ? 'coleta anterior' : 'coletas anteriores'} ({janela}).
        </p>
      )}
    </>
  );
}

function AnaliseDetalhe({ produtoId }) {
  const [janela, setJanela] = useState(JANELA_PADRAO);
  const [tentativa, setTentativa] = useState(0);
  // Guarda a chave da requisição junto do resultado: se a chave atual mudou
  // (outro produto, outra janela, nova tentativa), o resultado antigo é descartado
  // e a tela mostra "carregando" sem precisar de setState síncrono no efeito.
  const [resultado, setResultado] = useState(null); // { chave, analise } | { chave, erro }

  const chave = `${produtoId}|${janela}|${tentativa}`;

  useEffect(() => {
    let ativo = true;
    buscarAnalise(produtoId, janela).then(
      (analise) => ativo && setResultado({ chave, analise }),
      (e) => ativo && setResultado({ chave, erro: e.message || 'Não foi possível carregar a análise.' })
    );
    return () => {
      ativo = false;
    };
  }, [produtoId, janela, chave]);

  const carregando = resultado?.chave !== chave;

  let corpo;
  if (carregando) {
    corpo = (
      <p className="vazio" role="status">
        Carregando análise…
      </p>
    );
  } else if (resultado.erro) {
    corpo = (
      <div className="analise-erro">
        <p className="erro" role="alert">
          {resultado.erro}
        </p>
        <button type="button" className="btn-link" onClick={() => setTentativa((t) => t + 1)}>
          Tentar novamente
        </button>
      </div>
    );
  } else {
    corpo = <ResultadoAnalise analise={resultado.analise} />;
  }

  return (
    <section className="analise" aria-labelledby="titulo-analise" aria-busy={carregando}>
      <div className="analise-topo">
        <h3 id="titulo-analise">Análise de preço</h3>
        <label className="periodo">
          <span className="sr-only">Janela de comparação</span>
          <IconeCalendario className="periodo-esq" tamanho={16} />
          <select value={janela} onChange={(e) => setJanela(Number(e.target.value))}>
            {JANELAS.map((j) => (
              <option key={j.valor} value={j.valor}>
                {j.rotulo}
              </option>
            ))}
          </select>
          <IconeSetaBaixo className="periodo-dir" tamanho={16} />
        </label>
      </div>
      {corpo}
    </section>
  );
}

export default AnaliseDetalhe;
