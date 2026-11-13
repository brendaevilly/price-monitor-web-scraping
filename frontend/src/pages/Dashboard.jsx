import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  IconeAlertas,
  IconeCalendario,
  IconeConfig,
  IconeGrafico,
  IconeInicio,
  IconeKebab,
  IconeLogo,
  IconePacote,
  IconePacoteBusca,
  IconeBusca,
  IconeSeta,
  IconeSetaBaixo,
} from '../components/Icones';
import {
  buscarAnalise,
  buscarHistorico,
  listarAlertas,
  listarProdutos,
  resumoAnalise,
} from '../services/dashboardService';
import './Dashboard.css';

/* ---------- formatação ---------- */

const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const brlInteiro = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 0,
});

// O Pydantic serializa Decimal como string ("3200.00"): converte antes de usar.
const num = (v) => (v === null || v === undefined ? null : Number(v));

function moeda(v) {
  const n = num(v);
  return n === null || Number.isNaN(n) ? '—' : brl.format(n);
}

const dataCurta = (t) =>
  new Date(t).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });

const dataHora = (iso) =>
  new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });

const pct = (v) =>
  `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

/* ---------- rótulos (valores reais da API) ---------- */

const CLASSIFICACAO = {
  sem_dados: { rotulo: 'Dados insuficientes', classe: 'neutro' },
  sem_queda: { rotulo: 'Sem queda', classe: 'neutro' },
  pequena_queda: { rotulo: 'Pequena queda', classe: 'pequena' },
  queda_relevante: { rotulo: 'Queda relevante', classe: 'relevante' },
  grande_queda: { rotulo: 'Grande queda', classe: 'grande' },
};

const TIPO_ALERTA = {
  queda_preco: 'Queda de preço',
  preco_alvo: 'Preço-alvo atingido',
};

const PERIODOS = [
  { valor: 7, rotulo: 'Últimos 7 dias' },
  { valor: 30, rotulo: 'Últimos 30 dias' },
  { valor: 90, rotulo: 'Últimos 90 dias' },
  { valor: 0, rotulo: 'Todo o histórico' },
];

function statusDoAlerta(precoAtual, precoAlvo) {
  const atual = num(precoAtual);
  const alvo = num(precoAlvo);
  if (atual === null) return { rotulo: 'Sem dados', classe: 'neutro' };
  if (alvo === null) return { rotulo: 'Sem preço-alvo', classe: 'neutro' };
  if (atual <= alvo) return { rotulo: 'Preço atingido', classe: 'atingido' };
  return { rotulo: 'Em monitoramento', classe: 'monitorando' };
}

// UC07 3a: textos em português quando não há dados suficientes
function mensagemAnalise(analise) {
  if (analise.classificacao === 'sem_dados') {
    return `Dados insuficientes para classificar a queda: ${analise.amostras_media} de ${analise.amostras_minimas} coletas anteriores necessárias.`;
  }
  const v = num(analise.variacao_percentual_media);
  if (v === null) return null;
  if (v > 0) return `Preço atual ${pct(v)} abaixo da média histórica.`;
  if (v < 0) return `Preço atual ${pct(Math.abs(v))} acima da média histórica.`;
  return 'Preço atual igual à média histórica.';
}

function mensagemAnterior(analise) {
  const v = num(analise.variacao_percentual_anterior);
  if (v === null) return null;
  if (v > 0) return `${pct(v)} abaixo da coleta anterior.`;
  if (v < 0) return `${pct(Math.abs(v))} acima da coleta anterior.`;
  return 'Igual à coleta anterior.';
}

/* ---------- gráfico (SVG, sem dependências) ---------- */

// Escolhe limites e passos "redondos" (R$ 1.000, 2.000, 3.000...) como no design
function escalaBonita(min, max) {
  const bruto = (max - min) / 3;
  const mag = 10 ** Math.floor(Math.log10(bruto));
  const frac = bruto / mag;
  const passo = (frac <= 1 ? 1 : frac <= 2 ? 2 : frac <= 5 ? 5 : 10) * mag;
  const ini = Math.floor(min / passo) * passo;
  const fim = Math.ceil(max / passo) * passo;
  const ticks = [];
  for (let v = ini; v <= fim + passo / 2; v += passo) {
    ticks.push(Math.round(v * 100) / 100);
  }
  return { min: ini, max: fim, ticks, passo };
}

function GraficoPrecos({ pontos }) {
  const W = 640;
  const H = 270;
  const pad = { t: 14, r: 16, b: 34, l: 84 };
  const larguraUtil = W - pad.l - pad.r;
  const alturaUtil = H - pad.t - pad.b;

  const valores = pontos.map((p) => p.preco);
  let min = Math.min(...valores);
  let max = Math.max(...valores);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const escala = escalaBonita(min, max);
  const formatar = escala.passo < 1 ? brl : brlInteiro;

  const t0 = pontos[0].t;
  const t1 = pontos[pontos.length - 1].t;
  const x = (t) => (t1 === t0 ? pad.l + larguraUtil / 2 : pad.l + ((t - t0) / (t1 - t0)) * larguraUtil);
  const y = (v) => pad.t + (1 - (v - escala.min) / (escala.max - escala.min)) * alturaUtil;

  const linha = pontos
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.t).toFixed(1)} ${y(p.preco).toFixed(1)}`)
    .join(' ');

  // Datas espaçadas de forma uniforme no tempo, sem repetir o mesmo dia
  const quantidade = t1 === t0 ? 1 : 7;
  const rotulosX = [];
  for (let i = 0; i < quantidade; i += 1) {
    const t = quantidade === 1 ? t0 : t0 + (i * (t1 - t0)) / (quantidade - 1);
    const texto = dataCurta(t);
    if (rotulosX.length === 0 || rotulosX[rotulosX.length - 1].texto !== texto) {
      rotulosX.push({ t, texto, i });
    }
  }

  return (
    <svg
      className="grafico"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Variação de preço, de ${moeda(valores[0])} a ${moeda(valores[valores.length - 1])}`}
    >
      {escala.ticks.map((v) => (
        <text key={v} className="grafico-eixo" x={pad.l - 14} y={y(v) + 4} textAnchor="end">
          {formatar.format(v)}
        </text>
      ))}
      {rotulosX.map((r) => (
        <text
          key={r.i}
          className="grafico-eixo"
          x={x(r.t)}
          y={H - 8}
          textAnchor={r.i === 0 ? 'start' : r.i === quantidade - 1 ? 'end' : 'middle'}
        >
          {r.texto}
        </text>
      ))}
      <path className="grafico-sombra" d={linha} transform="translate(0 4)" />
      <path className="grafico-linha" d={linha} />
      {pontos.length <= 60 &&
        pontos.map((p) => (
          <circle key={p.t} className="grafico-alvo" cx={x(p.t)} cy={y(p.preco)} r="7">
            <title>{`${dataHora(p.iso)}: ${moeda(p.preco)}`}</title>
          </circle>
        ))}
    </svg>
  );
}

/* ---------- detalhe do produto selecionado (UC06 + UC07) ---------- */

function PainelDetalhe({ produto, detalhe, periodo }) {
  const pontos = useMemo(() => {
    const coletas = detalhe.historico?.coletas ?? [];
    const todos = coletas.map((c) => ({
      t: new Date(c.data_hora_coleta).getTime(),
      iso: c.data_hora_coleta,
      preco: Number(c.preco),
    }));
    if (periodo === 0 || todos.length === 0) return todos;
    // Janela contada a partir da coleta mais recente (mesmo critério do back)
    const corte = todos[todos.length - 1].t - periodo * 86400000;
    return todos.filter((p) => p.t >= corte);
  }, [detalhe.historico, periodo]);

  if (!produto) {
    return <p className="vazio">Selecione um produto na tabela para ver o histórico de preços.</p>;
  }
  if (detalhe.carregando) {
    return <p className="vazio" role="status">Carregando histórico…</p>;
  }
  if (detalhe.erro) {
    return <p className="erro" role="alert">{detalhe.erro}</p>;
  }

  const { historico, analise } = detalhe;
  const classe = CLASSIFICACAO[analise.classificacao] ?? {
    rotulo: analise.classificacao,
    classe: 'neutro',
  };
  const textoAnalise = mensagemAnalise(analise);
  const textoAnterior = mensagemAnterior(analise);

  let corpoGrafico;
  if (historico.coletas.length === 0) {
    corpoGrafico = <p className="vazio">Ainda não há preços coletados para este produto.</p>;
  } else if (pontos.length === 0) {
    corpoGrafico = <p className="vazio">Nenhuma coleta no período selecionado.</p>;
  } else {
    corpoGrafico = <GraficoPrecos pontos={pontos} />;
  }

  return (
    <>
      <p className="detalhe-nome">{produto.nome}</p>

      {corpoGrafico}

      <dl className="metricas">
        <div>
          <dt>Preço atual</dt>
          <dd>{moeda(historico.preco_atual)}</dd>
        </div>
        <div>
          <dt>Menor preço</dt>
          <dd>{moeda(historico.menor_preco)}</dd>
        </div>
        <div>
          <dt>Média histórica</dt>
          <dd>{moeda(historico.media_historica)}</dd>
        </div>
        <div>
          <dt>Classificação da queda</dt>
          <dd>
            <span className={`selo selo-${classe.classe}`}>{classe.rotulo}</span>
          </dd>
        </div>
      </dl>

      {(textoAnalise || textoAnterior) && (
        <p className="nota-analise">
          {textoAnalise} {textoAnterior}
        </p>
      )}
    </>
  );
}

/* ---------- página ---------- */

function Dashboard() {
  const { usuario, sair } = useAuth();

  const [carga, setCarga] = useState({ carregando: true, erro: null, avisoResumo: null });
  const [produtos, setProdutos] = useState([]);
  const [resumo, setResumo] = useState({});
  const [alertas, setAlertas] = useState({ itens: [], erro: null });
  const [busca, setBusca] = useState('');
  const [periodo, setPeriodo] = useState(30);
  const [selecionadoId, setSelecionadoId] = useState(null);
  const [menuAberto, setMenuAberto] = useState(null); // id do produto com o menu aberto
  const [detalhe, setDetalhe] = useState({
    carregando: false,
    erro: null,
    historico: null,
    analise: null,
  });

  const requisicao = useRef(0);
  const detalheRef = useRef(null);

  const selecionar = useCallback(async (id, { rolar = true } = {}) => {
    setSelecionadoId(id);
    const atual = ++requisicao.current;
    setDetalhe({ carregando: true, erro: null, historico: null, analise: null });
    if (rolar) detalheRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    try {
      const [historico, analise] = await Promise.all([buscarHistorico(id), buscarAnalise(id)]);
      if (atual !== requisicao.current) return; // resposta de uma seleção antiga
      setDetalhe({ carregando: false, erro: null, historico, analise });
    } catch (e) {
      if (atual !== requisicao.current) return;
      setDetalhe({ carregando: false, erro: e.message, historico: null, analise: null });
    }
  }, []);

  useEffect(() => {
    let ativo = true;
    (async () => {
      const [p, r, a] = await Promise.allSettled([
        listarProdutos(),
        resumoAnalise(),
        listarAlertas(5),
      ]);
      if (!ativo) return;

      if (p.status === 'rejected') {
        setCarga({ carregando: false, erro: p.reason.message, avisoResumo: null });
        return;
      }
      setProdutos(p.value);
      setResumo(
        r.status === 'fulfilled'
          ? Object.fromEntries(r.value.produtos.map((item) => [item.produto_id, item]))
          : {}
      );
      setAlertas(
        a.status === 'fulfilled'
          ? { itens: a.value, erro: null }
          : { itens: [], erro: a.reason.message }
      );
      setCarga({
        carregando: false,
        erro: null,
        avisoResumo:
          r.status === 'rejected'
            ? 'Não foi possível carregar os preços atuais. Os demais dados estão disponíveis.'
            : null,
      });
      // "Estado inicial" do design: o gráfico já aparece com o produto mais recente
      if (p.value.length > 0) selecionar(p.value[0].produto_id, { rolar: false });
    })();
    return () => {
      ativo = false;
    };
  }, [selecionar]);

  // Fecha os menus (ações da tabela) ao clicar fora ou apertar Esc
  useEffect(() => {
    if (menuAberto === null) return undefined;
    const fechar = (e) => {
      if (!(e.target instanceof Element) || !e.target.closest('[data-menu]')) setMenuAberto(null);
    };
    const esc = (e) => {
      if (e.key === 'Escape') setMenuAberto(null);
    };
    document.addEventListener('mousedown', fechar);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', fechar);
      document.removeEventListener('keydown', esc);
    };
  }, [menuAberto]);

  const produtoSelecionado = produtos.find((p) => p.produto_id === selecionadoId) ?? null;

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return produtos;
    return produtos.filter(
      (p) => p.nome.toLowerCase().includes(termo) || p.loja?.nome?.toLowerCase().includes(termo)
    );
  }, [produtos, busca]);

  const alertasAtivos = useMemo(() => produtos.filter((p) => p.alerta_ativo).length, [produtos]);

  // Economia = quanto o preço atual está abaixo da média histórica
  const maiorEconomia = useMemo(() => {
    let melhor = null;
    for (const r of Object.values(resumo)) {
      const media = num(r.media_historica);
      const atual = num(r.preco_atual);
      if (media === null || atual === null) continue;
      const economia = media - atual;
      if (economia > 0 && (melhor === null || economia > melhor.valor)) {
        melhor = { valor: economia, id: r.produto_id };
      }
    }
    return melhor;
  }, [resumo]);

  const iniciais =
    (usuario?.nome ?? '')
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((s) => s[0].toUpperCase())
      .join('') || 'U';

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-logo">
          <IconeLogo />
          <span>PriceBrother</span>
        </div>
        <nav className="app-nav" aria-label="Principal">
          <Link to="/dashboard" className="app-nav-item ativo" aria-current="page">
            <IconeInicio /> Início
          </Link>
          <Link to="/produtos/novo" className="app-nav-item">
            <IconePacoteBusca /> Produtos
          </Link>
          {/* Telas ainda não criadas: viram <Link> quando as rotas existirem */}
          <button type="button" className="app-nav-item desativado" aria-disabled="true">
            <IconeAlertas /> Alertas
          </button>
          <button type="button" className="app-nav-item desativado" aria-disabled="true">
            <IconeConfig /> Configurações
          </button>
        </nav>
      </aside>

      <div className="app-conteudo">
        <header className="app-topo">
          <button type="button" className="app-sair" onClick={sair}>
            Sair
          </button>
          <div className="app-avatar" title={usuario?.nome ?? ''}>
            {iniciais}
          </div>
        </header>

        <main className="app-main">
        <div className="dash">
          <div className="dash-titulo">
            <h1>Dashboard</h1>
            <p className="sub">Visão geral dos seus produtos e histórico de preços.</p>
          </div>

          {carga.carregando && <p className="vazio" role="status">Carregando seus produtos…</p>}
          {carga.erro && <p className="erro" role="alert">{carga.erro}</p>}

          {!carga.carregando && !carga.erro && (
            <>
              {carga.avisoResumo && <p className="aviso" role="status">{carga.avisoResumo}</p>}

              <section className="cartoes" aria-label="Resumo">
                <div className="cartao">
                  <IconePacoteBusca className="cartao-icone" tamanho={40} strokeWidth={1.5} />
                  <div className="cartao-corpo">
                    <h2>Produtos monitorados</h2>
                    <p className="cartao-valor">{produtos.length}</p>
                    <Link className="cartao-link" to="/produtos">
                      Ver todos <IconeSeta tamanho={13} />
                    </Link>
                  </div>
                </div>
                <div className="cartao">
                  <IconeAlertas className="cartao-icone" tamanho={40} strokeWidth={1.5} />
                  <div className="cartao-corpo">
                    <h2>Alertas ativos</h2>
                    <p className="cartao-valor">{alertasAtivos}</p>
                    <Link className="cartao-link" to="/alertas">
                      Ver alertas <IconeSeta tamanho={13} />
                    </Link>
                  </div>
                </div>
                <div className="cartao">
                  <IconeGrafico className="cartao-icone" tamanho={40} strokeWidth={1.5} />
                  <div className="cartao-corpo">
                    <h2>Maior economia</h2>
                    <p className="cartao-valor">{maiorEconomia ? moeda(maiorEconomia.valor) : '—'}</p>
                    {maiorEconomia && (
                      <button
                        type="button"
                        className="cartao-link"
                        onClick={() => selecionar(maiorEconomia.id)}
                      >
                        Ver detalhes <IconeSeta tamanho={13} />
                      </button>
                    )}
                  </div>
                </div>
              </section>

              <section className="painel" ref={detalheRef} aria-labelledby="titulo-historico">
                <div className="painel-topo">
                  <div className="painel-titulo">
                    <IconeGrafico className="painel-icone" tamanho={36} strokeWidth={1.5} />
                    <div>
                      <h2 id="titulo-historico">Histórico de variação de preços</h2>
                      <p className="sub">
                        Acompanhe a evolução dos preços dos seus produtos monitorados.
                      </p>
                    </div>
                  </div>
                  <label className="periodo">
                    <span className="sr-only">Período do gráfico</span>
                    <IconeCalendario className="periodo-esq" tamanho={16} />
                    <select value={periodo} onChange={(e) => setPeriodo(Number(e.target.value))}>
                      {PERIODOS.map((p) => (
                        <option key={p.valor} value={p.valor}>
                          {p.rotulo}
                        </option>
                      ))}
                    </select>
                    <IconeSetaBaixo className="periodo-dir" tamanho={16} />
                  </label>
                </div>
                <PainelDetalhe produto={produtoSelecionado} detalhe={detalhe} periodo={periodo} />
              </section>

              <section className="painel" aria-labelledby="titulo-produtos">
                <div className="painel-topo">
                  <div className="painel-titulo">
                    <IconePacoteBusca className="painel-icone" tamanho={36} strokeWidth={1.5} />
                    <div>
                      <h2 id="titulo-produtos">Produtos em monitoramento</h2>
                      <p className="sub">Acompanhe seus produtos e os status dos alertas.</p>
                    </div>
                  </div>
                  <label className="busca">
                    <span className="sr-only">Buscar produto</span>
                    <IconeBusca className="busca-icone" tamanho={16} />
                    <input
                      type="search"
                      placeholder="Buscar produto..."
                      value={busca}
                      onChange={(e) => setBusca(e.target.value)}
                    />
                  </label>
                </div>

                {produtos.length === 0 ? (
                  <p className="vazio">
                    Você ainda não monitora nenhum produto.{' '}
                    <Link to="/produtos/novo">Cadastrar produto</Link>
                  </p>
                ) : visiveis.length === 0 ? (
                  <p className="vazio">Nenhum produto encontrado para essa busca.</p>
                ) : (
                  <div className="tabela-rolagem">
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">Produto</th>
                          <th scope="col">Loja</th>
                          <th scope="col">Preço atual</th>
                          <th scope="col">Preço-alvo</th>
                          <th scope="col">Status do alerta</th>
                          <th scope="col" className="col-acoes">
                            Ações
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {visiveis.map((p) => {
                          const r = resumo[p.produto_id];
                          const status = statusDoAlerta(r?.preco_atual, p.preco_alvo);
                          const selecionado = p.produto_id === selecionadoId;
                          const menuDoProduto = menuAberto === p.produto_id;
                          return (
                            <tr key={p.produto_id} className={selecionado ? 'linha-selecionada' : ''}>
                              <td>
                                <div className="produto-celula">
                                  <span className="miniatura">
                                    {p.imagem_url ? (
                                      <img src={p.imagem_url} alt="" />
                                    ) : (
                                      <IconePacote tamanho={18} />
                                    )}
                                  </span>
                                  <span className="produto-texto">
                                    <button
                                      type="button"
                                      className="produto-botao"
                                      aria-pressed={selecionado}
                                      onClick={() => selecionar(p.produto_id)}
                                    >
                                      {p.nome}
                                    </button>
                                    {p.categoria && (
                                      <span className="produto-categoria">{p.categoria}</span>
                                    )}
                                  </span>
                                </div>
                              </td>
                              <td>{p.loja?.nome ?? '—'}</td>
                              <td>{moeda(r?.preco_atual)}</td>
                              <td>{moeda(p.preco_alvo)}</td>
                              <td>
                                <span className={`selo selo-ponto selo-${status.classe}`}>
                                  {status.rotulo}
                                </span>
                              </td>
                              <td className="col-acoes">
                                <div className="menu-wrap" data-menu>
                                  <button
                                    type="button"
                                    className="kebab"
                                    aria-label={`Ações de ${p.nome}`}
                                    aria-haspopup="menu"
                                    aria-expanded={menuDoProduto}
                                    onClick={() =>
                                      setMenuAberto(menuDoProduto ? null : p.produto_id)
                                    }
                                  >
                                    <IconeKebab tamanho={20} />
                                  </button>
                                  {menuDoProduto && (
                                    <div className="menu-flutuante" role="menu">
                                      <button
                                        type="button"
                                        role="menuitem"
                                        onClick={() => {
                                          setMenuAberto(null);
                                          selecionar(p.produto_id);
                                        }}
                                      >
                                        Ver histórico
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              <section className="painel" aria-labelledby="titulo-alertas">
                <div className="painel-topo">
                  <div className="painel-titulo">
                    <IconeAlertas className="painel-icone" tamanho={36} strokeWidth={1.5} />
                    <div>
                      <h2 id="titulo-alertas">Alertas recentes</h2>
                      <p className="sub">Os últimos alertas disparados para os seus produtos.</p>
                    </div>
                  </div>
                </div>
                {alertas.erro ? (
                  <p className="erro" role="alert">{alertas.erro}</p>
                ) : alertas.itens.length === 0 ? (
                  <p className="vazio">Nenhum alerta disparado até agora.</p>
                ) : (
                  <ul className="alertas">
                    {alertas.itens.map((a) => {
                      const naLista = produtos.some((p) => p.produto_id === a.produto.id);
                      return (
                        <li key={a.id}>
                          <p className="alerta-tipo">{TIPO_ALERTA[a.tipo] ?? a.tipo}</p>
                          <p className="alerta-texto">{a.mensagem}</p>
                          <p className="alerta-rodape">
                            <time dateTime={a.data_envio}>{dataHora(a.data_envio)}</time>
                            {naLista && (
                              <button type="button" onClick={() => selecionar(a.produto.id)}>
                                Ver histórico de {a.produto.nome}
                              </button>
                            )}
                          </p>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </section>
            </>
          )}
        </div>
        </main>
      </div>
    </div>
  );
}

export default Dashboard;
