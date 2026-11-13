import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AnaliseDetalhe from '../components/AnaliseDetalhe';
import {
  IconeAlertas,
  IconeCalendario,
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
  atualizarMonitoramento,
  buscarHistorico,
  listarAlertas,
  listarProdutos,
  removerMonitoramento,
  resumoAnalise,
} from '../services/dashboardService';
import { formatarPreco, parsePreco } from '../utils/produto';
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
const pct = (valor) =>
  `${Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;



const TIPO_ALERTA = {
  queda_preco: 'Queda de preço',
  preco_alvo: 'Preço-alvo atingido',
};


const CLASSIFICACAO_ANALISE = {
  sem_dados: 'Dados insuficientes',
  sem_queda: 'Sem queda',
  pequena_queda: 'Pequena queda',
  queda_relevante: 'Queda relevante',
  grande_queda: 'Grande queda',
};

function variacaoRelatorio(item) {
  const candidatas = [
    { valor: num(item.variacao_percentual_media), origem: 'vs. média' },
    { valor: num(item.variacao_percentual_anterior), origem: 'vs. coleta anterior' },
  ].filter((candidata) => candidata.valor !== null);
  if (candidatas.length === 0) return { valor: null, origem: null };
  const quedas = candidatas.filter((candidata) => candidata.valor > 0);
  if (quedas.length > 0) {
    return quedas.reduce((maior, atual) => (atual.valor > maior.valor ? atual : maior));
  }
  return candidatas.find((candidata) => candidata.origem === 'vs. média') ?? candidatas[0];
}

const PERIODOS = [
  { valor: 7, rotulo: 'Últimos 7 dias' },
  { valor: 30, rotulo: 'Últimos 30 dias' },
  { valor: 90, rotulo: 'Últimos 90 dias' },
  { valor: 0, rotulo: 'Todo o histórico' },
];

function statusDoAlerta(precoAtual, precoAlvo, alertaAtivo = true) {
  if (!alertaAtivo) return { rotulo: 'Alerta desativado', classe: 'neutro' };
  const atual = num(precoAtual);
  const alvo = num(precoAlvo);
  if (atual === null) return { rotulo: 'Sem dados', classe: 'neutro' };
  if (alvo === null) return { rotulo: 'Sem preço-alvo', classe: 'neutro' };
  if (atual <= alvo) return { rotulo: 'Preço atingido', classe: 'atingido' };
  return { rotulo: 'Em monitoramento', classe: 'monitorando' };
}

/* ---------- gráfico cronológico de preços (Recharts) ---------- */

function TooltipPreco({ active, payload }) {
  if (!active || !payload?.length) return null;
  const ponto = payload[0].payload;

  return (
    <div className="grafico-tooltip">
      <span>{dataHora(ponto.iso)}</span>
      <strong>{moeda(ponto.preco)}</strong>
    </div>
  );
}

function GraficoPrecos({ pontos, precoAlvo }) {
  // A média acompanha exatamente as coletas visíveis no período selecionado.
  const mediaJanela = pontos.reduce((total, ponto) => total + ponto.preco, 0) / pontos.length;
  const alvoValido = Number.isFinite(precoAlvo) && precoAlvo > 0 ? precoAlvo : null;
  const valores = [
    ...pontos.map((ponto) => ponto.preco),
    mediaJanela,
    ...(alvoValido === null ? [] : [alvoValido]),
  ];
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const margem = minimo === maximo ? Math.max(Math.abs(minimo) * 0.05, 1) : (maximo - minimo) * 0.12;
  const dominioY = [Math.max(0, minimo - margem), maximo + margem];
  const primeiroTempo = pontos[0].t;
  const ultimoTempo = pontos[pontos.length - 1].t;
  const dominioX = primeiroTempo === ultimoTempo
    ? [primeiroTempo - 86400000, ultimoTempo + 86400000]
    : ['dataMin', 'dataMax'];

  return (
    <div className="grafico-container">
      <div
        className="grafico-responsivo"
        role="img"
        aria-label={`Histórico cronológico: ${pontos.length} ${pontos.length === 1 ? 'coleta' : 'coletas'}, média do período ${moeda(mediaJanela)}${alvoValido === null ? '' : ` e preço-alvo ${moeda(alvoValido)}`}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={pontos} margin={{ top: 14, right: 12, bottom: 6, left: 0 }}>
            <CartesianGrid stroke="#e3e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={dominioX}
              tickFormatter={dataCurta}
              tick={{ fill: '#7d8aa3', fontSize: 11 }}
              minTickGap={24}
              tickLine={false}
              axisLine={{ stroke: '#d7deea' }}
            />
            <YAxis
              domain={dominioY}
              tickFormatter={(valor) => brlInteiro.format(valor)}
              tick={{ fill: '#7d8aa3', fontSize: 11 }}
              width={74}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<TooltipPreco />} />
            <ReferenceLine
              y={mediaJanela}
              stroke="#854d0e"
              strokeDasharray="6 4"
              strokeWidth={2}
            />
            {alvoValido !== null && (
              <ReferenceLine
                y={alvoValido}
                stroke="#1f7a3d"
                strokeDasharray="4 4"
                strokeWidth={2}
              />
            )}
            <Line
              type="linear"
              dataKey="preco"
              name="Preço coletado"
              stroke="#3b8cf7"
              strokeWidth={2.5}
              dot={pontos.length <= 40 ? { r: 3, fill: '#3b8cf7', strokeWidth: 0 } : false}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="grafico-legenda" aria-label="Legenda do gráfico">
        <span><i className="legenda-preco" /> Preço coletado</span>
        <span><i className="legenda-media" /> Média do período: {moeda(mediaJanela)}</span>
        {alvoValido !== null && (
          <span><i className="legenda-alvo" /> Preço-alvo: {moeda(alvoValido)}</span>
        )}
      </div>
    </div>
  );
}

const alvoParaCampo = (v) => (num(v) === null ? '' : formatarPreco(Math.round(num(v) * 100)));

function ConfiguracaoMonitoramento({ produto, onAtualizar, onPedirRemocao }) {
  const [campoAlvo, setCampoAlvo] = useState(() => alvoParaCampo(produto.preco_alvo));
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState(null); // { tipo: 'ok' | 'erro', texto }

  const alvoSalvo = alvoParaCampo(produto.preco_alvo);
  const alvoMudou = campoAlvo !== alvoSalvo;

  async function executar(campos, textoOk) {
    setSalvando(true);
    setMsg(null);
    try {
      await onAtualizar(produto.monitoramento_id, campos);
      setMsg({ tipo: 'ok', texto: textoOk });
    } catch (e) {
      setMsg({ tipo: 'erro', texto: e.message });
    } finally {
      setSalvando(false);
    }
  }

  function salvarAlvo(e) {
    e.preventDefault();
    const valor = parsePreco(campoAlvo);
    if (campoAlvo && (valor === null || valor <= 0)) {
      setMsg({ tipo: 'erro', texto: 'Informe um preço-alvo maior que zero.' });
      return;
    }
    executar(
      { precoAlvo: valor },
      valor === null ? 'Preço-alvo removido.' : 'Preço-alvo salvo.'
    );
  }

  return (
    <section className="config" aria-label={`Configurações de ${produto.nome}`}>
      <h3>Configurações do monitoramento</h3>

      <label className="config-alerta">
        <input
          type="checkbox"
          role="switch"
          checked={produto.alerta_ativo}
          disabled={salvando}
          onChange={(e) =>
            executar(
              { alertaAtivo: e.target.checked },
              e.target.checked ? 'Alerta ativado.' : 'Alerta desativado.'
            )
          }
        />
        <span>Receber alertas deste produto por e-mail</span>
      </label>

      <form className="config-alvo" onSubmit={salvarAlvo} noValidate>
        <label htmlFor={`alvo-${produto.monitoramento_id}`}>Preço-alvo</label>
        <input
          id={`alvo-${produto.monitoramento_id}`}
          inputMode="numeric"
          placeholder="R$ 0,00"
          value={campoAlvo}
          disabled={salvando}
          onChange={(e) => setCampoAlvo(formatarPreco(e.target.value))}
        />
        <button type="submit" className="btn-primario" disabled={salvando || !alvoMudou}>
          Salvar
        </button>
        {produto.preco_alvo !== null && produto.preco_alvo !== undefined && (
          <button
            type="button"
            className="btn-link"
            disabled={salvando}
            onClick={() => {
              setCampoAlvo('');
              executar({ precoAlvo: null }, 'Preço-alvo removido.');
            }}
          >
            Limpar
          </button>
        )}
      </form>

      <p className="config-msg" role="status" data-tipo={msg?.tipo}>
        {msg?.texto ?? ''}
      </p>

      <button type="button" className="btn-perigo" onClick={() => onPedirRemocao(produto)}>
        Remover da lista
      </button>
    </section>
  );
}

function ConfirmarRemocao({ produto, removendo, erro, onCancelar, onConfirmar }) {
  const cancelarRef = useRef(null);

  useEffect(() => {
    cancelarRef.current?.focus();
    const esc = (e) => {
      if (e.key === 'Escape' && !removendo) onCancelar();
    };
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [removendo, onCancelar]);

  return (
    <div className="modal-fundo" onMouseDown={() => !removendo && onCancelar()}>
      <div
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="modal-titulo"
        aria-describedby="modal-texto"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 id="modal-titulo">Remover da lista?</h2>
        <p id="modal-texto">
          <strong>{produto.nome}</strong> deixará de aparecer na sua lista e você não receberá mais
          alertas dele. O histórico de preços já coletado não é apagado: se você voltar a monitorar
          este produto, ele estará lá.
        </p>
        {erro && <p className="erro" role="alert">{erro}</p>}
        <div className="modal-acoes">
          <button type="button" ref={cancelarRef} onClick={onCancelar} disabled={removendo}>
            Cancelar
          </button>
          <button type="button" className="btn-perigo-cheio" onClick={onConfirmar} disabled={removendo}>
            {removendo ? 'Removendo…' : 'Remover'}
          </button>
        </div>
      </div>
    </div>
  );
}



function PainelDetalhe({ produto, detalhe, periodo, onAtualizar, onPedirRemocao }) {
  const pontos = useMemo(() => {
    const coletas = detalhe.historico?.coletas ?? [];
    const todos = coletas
      .map((c) => ({
        t: new Date(c.data_hora_coleta).getTime(),
        iso: c.data_hora_coleta,
        preco: Number(c.preco),
      }))
      .filter((ponto) => Number.isFinite(ponto.t) && Number.isFinite(ponto.preco) && ponto.preco > 0)
      .sort((a, b) => a.t - b.t);
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

  const { historico } = detalhe;

  let corpoGrafico;
  if (historico.coletas.length === 0) {
    corpoGrafico = <p className="vazio">Ainda não há preços coletados para este produto.</p>;
  } else if (pontos.length === 0) {
    corpoGrafico = <p className="vazio">Nenhuma coleta no período selecionado.</p>;
  } else {
    corpoGrafico = <GraficoPrecos pontos={pontos} precoAlvo={num(produto.preco_alvo)} />;
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
      </dl>

      <AnaliseDetalhe produtoId={produto.produto_id} />

      <ConfiguracaoMonitoramento
        key={produto.monitoramento_id}
        produto={produto}
        onAtualizar={onAtualizar}
        onPedirRemocao={onPedirRemocao}
      />
    </>
  );
}

/* ---------- página ---------- */

function Dashboard() {
  const { usuario, sair } = useAuth();

  const [carga, setCarga] = useState({ carregando: true, erro: null, avisoResumo: null });
  const [produtos, setProdutos] = useState([]);
  const [resumo, setResumo] = useState({});
  const [relatorio, setRelatorio] = useState({ produtos: [], janela_dias: null, erro: null });
  const [filtroClassificacao, setFiltroClassificacao] = useState('todas');
  const [alertas, setAlertas] = useState({ itens: [], erro: null });
  const [busca, setBusca] = useState('');
  const [periodo, setPeriodo] = useState(30);
  const [selecionadoId, setSelecionadoId] = useState(null);
  const [menuAberto, setMenuAberto] = useState(null); // id do produto com o menu aberto
  const [detalhe, setDetalhe] = useState({
    carregando: false,
    erro: null,
    historico: null,
  });

  const [confirmando, setConfirmando] = useState(null); // produto aguardando confirmação de remoção
  const [remocao, setRemocao] = useState({ removendo: false, erro: null });
  const [aviso, setAviso] = useState(null); // feedback da tabela (kebab / remoção)

  const requisicao = useRef(0);
  const detalheRef = useRef(null);

  const selecionar = useCallback(async (id, { rolar = true } = {}) => {
    setSelecionadoId(id);
    const atual = ++requisicao.current;
    setDetalhe({ carregando: true, erro: null, historico: null });
    if (rolar) detalheRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    try {
      const historico = await buscarHistorico(id);
      if (atual !== requisicao.current) return; // resposta de uma seleção antiga
      setDetalhe({ carregando: false, erro: null, historico });
    } catch (e) {
      if (atual !== requisicao.current) return;
      setDetalhe({ carregando: false, erro: e.message, historico: null });
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
      setRelatorio(
        r.status === 'fulfilled'
          ? { produtos: r.value.produtos, janela_dias: r.value.janela_dias, erro: null }
          : { produtos: [], janela_dias: null, erro: r.reason.message }
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

  // PATCH /monitoramentos/{id}: aplica a resposta do servidor na lista (fonte da verdade)
  const atualizar = useCallback(async (monitoramentoId, campos) => {
    const atualizado = await atualizarMonitoramento(monitoramentoId, campos);
    setProdutos((lista) =>
      lista.map((p) => (p.monitoramento_id === monitoramentoId ? { ...p, ...atualizado } : p))
    );
    return atualizado;
  }, []);

  const alternarAlerta = useCallback(
    async (p) => {
      setMenuAberto(null);
      setAviso(null);
      try {
        await atualizar(p.monitoramento_id, { alertaAtivo: !p.alerta_ativo });
        setAviso({
          tipo: 'ok',
          texto: `Alerta ${p.alerta_ativo ? 'desativado' : 'ativado'} para ${p.nome}.`,
        });
      } catch (e) {
        setAviso({ tipo: 'erro', texto: e.message });
      }
    },
    [atualizar]
  );

  const pedirRemocao = useCallback((p) => {
    setMenuAberto(null);
    setRemocao({ removendo: false, erro: null });
    setConfirmando(p);
  }, []);

  const cancelarRemocao = useCallback(() => setConfirmando(null), []);

  // DELETE /monitoramentos/{id}: só o vínculo some; o histórico do produto fica no banco (RN05)
  async function confirmarRemocao() {
    const p = confirmando;
    setRemocao({ removendo: true, erro: null });
    try {
      await removerMonitoramento(p.monitoramento_id);
    } catch (e) {
      setRemocao({ removendo: false, erro: e.message });
      return;
    }
    const restantes = produtos.filter((x) => x.monitoramento_id !== p.monitoramento_id);
    setProdutos(restantes);
    setResumo((atual) => {
      const resto = { ...atual };
      delete resto[p.produto_id];
      return resto;
    });
    setConfirmando(null);
    setRemocao({ removendo: false, erro: null });
    setAviso({ tipo: 'ok', texto: `${p.nome} foi removido da sua lista.` });
    if (p.produto_id === selecionadoId) {
      if (restantes.length > 0) {
        selecionar(restantes[0].produto_id, { rolar: false });
      } else {
        requisicao.current += 1; // descarta resposta em andamento
        setSelecionadoId(null);
        setDetalhe({ carregando: false, erro: null, historico: null });
      }
    }
  }

  const produtoSelecionado = produtos.find((p) => p.produto_id === selecionadoId) ?? null;

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return produtos;
    return produtos.filter(
      (p) => p.nome.toLowerCase().includes(termo) || p.loja?.nome?.toLowerCase().includes(termo)
    );
  }, [produtos, busca]);

  const alertasAtivos = useMemo(() => produtos.filter((p) => p.alerta_ativo).length, [produtos]);

  const linhasRelatorio = useMemo(() => {
    const porId = new Map(produtos.map((produto) => [produto.produto_id, produto]));
    return relatorio.produtos
      .map((item) => ({
        ...item,
        lojaNome: porId.get(item.produto_id)?.loja?.nome ?? '—',
        variacao: variacaoRelatorio(item),
      }))
      .filter((item) => filtroClassificacao === 'todas' || item.classificacao === filtroClassificacao)
      .sort((a, b) => {
        const quedaA = a.variacao.valor === null ? -Infinity : Math.max(a.variacao.valor, 0);
        const quedaB = b.variacao.valor === null ? -Infinity : Math.max(b.variacao.valor, 0);
        return quedaB - quedaA || a.nome.localeCompare(b.nome, 'pt-BR');
      });
  }, [relatorio.produtos, produtos, filtroClassificacao]);

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
                <PainelDetalhe
                  produto={produtoSelecionado}
                  detalhe={detalhe}
                  periodo={periodo}
                  onAtualizar={atualizar}
                  onPedirRemocao={pedirRemocao}
                />
              </section>

              <section className="painel painel-relatorio" aria-labelledby="titulo-relatorio">
                <div className="painel-topo">
                  <div className="painel-titulo">
                    <IconeGrafico className="painel-icone" tamanho={36} strokeWidth={1.5} />
                    <div>
                      <h2 id="titulo-relatorio">Relatório de análise</h2>
                      <p className="sub">
                        Produtos ordenados pela maior queda de preço
                        {relatorio.janela_dias !== null && (
                          relatorio.janela_dias === 0
                            ? ' em relação a todo o histórico.'
                            : ` na janela de ${relatorio.janela_dias} dias.`
                        )}
                      </p>
                    </div>
                  </div>
                  <label className="relatorio-filtro">
                    <span>Classificação</span>
                    <select
                      value={filtroClassificacao}
                      onChange={(e) => setFiltroClassificacao(e.target.value)}
                    >
                      <option value="todas">Todas as faixas</option>
                      {Object.entries(CLASSIFICACAO_ANALISE).map(([valor, rotulo]) => (
                        <option key={valor} value={valor}>{rotulo}</option>
                      ))}
                    </select>
                  </label>
                </div>

                {relatorio.erro ? (
                  <p className="aviso" role="alert">
                    Não foi possível carregar o relatório: {relatorio.erro}
                  </p>
                ) : linhasRelatorio.length === 0 ? (
                  <p className="vazio">
                    {relatorio.produtos.length === 0
                      ? 'Não há produtos para analisar.'
                      : 'Nenhum produto corresponde à classificação selecionada.'}
                  </p>
                ) : (
                  <div className="tabela-rolagem relatorio-rolagem">
                    <table className="tabela-relatorio">
                      <thead>
                        <tr>
                          <th scope="col">Produto</th>
                          <th scope="col">Loja</th>
                          <th scope="col">Preço atual</th>
                          <th scope="col">Variação</th>
                          <th scope="col">Classificação</th>
                          <th scope="col">Detalhes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {linhasRelatorio.map((item) => (
                          <tr key={item.produto_id}>
                            <td>
                              <button
                                type="button"
                                className="relatorio-produto"
                                onClick={() => selecionar(item.produto_id)}
                              >
                                {item.nome}
                              </button>
                            </td>
                            <td>{item.lojaNome}</td>
                            <td>{moeda(item.preco_atual)}</td>
                            <td>
                              {item.variacao.valor === null ? (
                                '—'
                              ) : (
                                <span className={item.variacao.valor > 0 ? 'relatorio-queda' : ''}>
                                  {item.variacao.valor > 0 ? '−' : item.variacao.valor < 0 ? '+' : ''}
                                  {pct(Math.abs(item.variacao.valor))}
                                  <small>{item.variacao.origem}</small>
                                </span>
                              )}
                            </td>
                            <td>
                              <span className={`selo selo-${item.classificacao === 'queda_relevante' ? 'relevante' : item.classificacao === 'grande_queda' ? 'grande' : item.classificacao === 'pequena_queda' ? 'pequena' : 'neutro'}`}>
                                {CLASSIFICACAO_ANALISE[item.classificacao] ?? item.classificacao}
                              </span>
                            </td>
                            <td>
                              <button
                                type="button"
                                className="relatorio-link"
                                onClick={() => selecionar(item.produto_id)}
                              >
                                Ver no dashboard
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
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

                {aviso && (
                  <p
                    className={aviso.tipo === 'erro' ? 'erro' : 'aviso aviso-ok'}
                    role={aviso.tipo === 'erro' ? 'alert' : 'status'}
                  >
                    {aviso.texto}
                  </p>
                )}

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
                          const status = statusDoAlerta(r?.preco_atual, p.preco_alvo, p.alerta_ativo);
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
                                      <button
                                        type="button"
                                        role="menuitem"
                                        onClick={() => alternarAlerta(p)}
                                      >
                                        {p.alerta_ativo ? 'Desativar alerta' : 'Ativar alerta'}
                                      </button>
                                      <button
                                        type="button"
                                        role="menuitem"
                                        className="menu-perigo"
                                        onClick={() => pedirRemocao(p)}
                                      >
                                        Remover da lista
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

          {confirmando && (
            <ConfirmarRemocao
              produto={confirmando}
              removendo={remocao.removendo}
              erro={remocao.erro}
              onCancelar={cancelarRemocao}
              onConfirmar={confirmarRemocao}
            />
          )}
        </div>
        </main>
      </div>
    </div>
  );
}

export default Dashboard;
