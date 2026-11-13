import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { IconeAlertas, IconeBusca } from '../components/Icones';
import { listarAlertas } from '../services/dashboardService';
import './Dashboard.css';
import './Alertas.css';

const TIPOS = {
  queda_preco: 'Queda de preço',
  preco_alvo: 'Preço-alvo atingido',
};
const dataHora = (valor) => {
  if (!valor || Number.isNaN(new Date(valor).getTime())) return 'Data indisponível';
  return new Date(valor).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

function Alertas() {
  const [itens, setItens] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [busca, setBusca] = useState('');
  const [tipo, setTipo] = useState('todos');
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro('');
    listarAlertas(200).then(
      (dados) => {
        if (!ativo) return;
        setItens(Array.isArray(dados) ? dados : []);
        setCarregando(false);
      },
      (falha) => {
        if (!ativo) return;
        setErro(falha?.message || 'Não foi possível carregar os alertas.');
        setCarregando(false);
      }
    );
    return () => {
      ativo = false;
    };
  }, [tentativa]);

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR');
    return itens.filter((alerta) => {
      const texto = `${alerta.produto?.nome || ''} ${alerta.mensagem || ''} ${TIPOS[alerta.tipo] || alerta.tipo || ''}`
        .toLocaleLowerCase('pt-BR');
      return (tipo === 'todos' || alerta.tipo === tipo) && (!termo || texto.includes(termo));
    });
  }, [itens, busca, tipo]);

  const quedas = itens.filter((alerta) => alerta.tipo === 'queda_preco').length;
  const precosAlvo = itens.filter((alerta) => alerta.tipo === 'preco_alvo').length;

  return (
    <div className="dash pagina-alertas">
      <div className="pagina-cabecalho">
        <div className="dash-titulo">
          <h1>Alertas</h1>
          <p className="sub">Acompanhe os avisos disparados para os produtos que você monitora.</p>
        </div>
        <Link className="alertas-voltar" to="/dashboard">Voltar ao dashboard</Link>
      </div>

      <section className="cartoes alertas-resumo" aria-label="Resumo dos alertas">
        <div className="cartao">
          <IconeAlertas className="cartao-icone" tamanho={36} />
          <div className="cartao-corpo">
            <h2>Alertas encontrados</h2>
            <p className="cartao-valor">{itens.length}</p>
          </div>
        </div>
        <div className="cartao">
          <span className="alertas-indicador alerta-queda" aria-hidden="true">↓</span>
          <div className="cartao-corpo">
            <h2>Quedas de preço</h2>
            <p className="cartao-valor">{quedas}</p>
          </div>
        </div>
        <div className="cartao">
          <span className="alertas-indicador alerta-alvo" aria-hidden="true">✓</span>
          <div className="cartao-corpo">
            <h2>Preços-alvo atingidos</h2>
            <p className="cartao-valor">{precosAlvo}</p>
          </div>
        </div>
      </section>

      <section className="painel" aria-labelledby="titulo-alertas-lista">
        <div className="painel-topo">
          <div className="painel-titulo">
            <IconeAlertas className="painel-icone" tamanho={32} />
            <div>
              <h2 id="titulo-alertas-lista">Histórico de alertas</h2>
              <p className="sub">Exibindo até os 200 alertas mais recentes.</p>
            </div>
          </div>
          <div className="alertas-filtros">
            <label className="busca">
              <span className="sr-only">Buscar alertas</span>
              <IconeBusca className="busca-icone" tamanho={16} />
              <input
                type="search"
                placeholder="Buscar alerta ou produto..."
                value={busca}
                onChange={(evento) => setBusca(evento.target.value)}
              />
            </label>
            <label className="relatorio-filtro">
              <span className="sr-only">Filtrar tipo de alerta</span>
              <select value={tipo} onChange={(evento) => setTipo(evento.target.value)}>
                <option value="todos">Todos os tipos</option>
                <option value="queda_preco">Queda de preço</option>
                <option value="preco_alvo">Preço-alvo atingido</option>
              </select>
            </label>
            <button type="button" className="alertas-atualizar" onClick={() => setTentativa((valor) => valor + 1)} disabled={carregando}>
              {carregando ? 'Atualizando…' : 'Atualizar'}
            </button>
          </div>
        </div>

        {carregando ? (
          <p className="vazio" role="status">Carregando alertas…</p>
        ) : erro ? (
          <div className="erro" role="alert">
            <p>{erro}</p>
            <button type="button" className="btn-link" onClick={() => setTentativa((valor) => valor + 1)}>
              Tentar novamente
            </button>
          </div>
        ) : itens.length === 0 ? (
          <div className="estado-vazio">
            <p className="vazio">Nenhum alerta foi disparado até agora.</p>
            <p className="alertas-orientacao">Quando houver uma queda de preço ou um preço-alvo atingido, os avisos aparecerão aqui.</p>
            <Link className="btn-primario" to="/produtos">Ver produtos monitorados</Link>
          </div>
        ) : filtrados.length === 0 ? (
          <p className="vazio">Nenhum alerta corresponde à busca ou ao tipo selecionado.</p>
        ) : (
          <ul className="alertas lista-alertas">
            {filtrados.map((alerta) => (
              <li key={alerta.id} className="alerta-card">
                <span className={`alerta-sinal ${alerta.tipo === 'preco_alvo' ? 'sinal-alvo' : 'sinal-queda'}`} aria-hidden="true">
                  {alerta.tipo === 'preco_alvo' ? '✓' : '↓'}
                </span>
                <div className="alerta-conteudo">
                  <div className="alerta-cabecalho">
                    <p className="alerta-tipo">{TIPOS[alerta.tipo] || alerta.tipo || 'Alerta'}</p>
                    <time dateTime={alerta.data_envio || undefined}>{dataHora(alerta.data_envio)}</time>
                  </div>
                  {alerta.produto?.nome && <p className="alerta-produto">{alerta.produto.nome}</p>}
                  <p className="alerta-texto">{alerta.mensagem || 'Alerta sem descrição.'}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
        {!carregando && !erro && itens.length > 0 && (
          <p className="alertas-contagem" aria-live="polite">
            Exibindo {filtrados.length} de {itens.length} alerta{itens.length === 1 ? '' : 's'} carregado{itens.length === 1 ? '' : 's'}.
          </p>
        )}
      </section>
    </div>
  );
}

export default Alertas;
