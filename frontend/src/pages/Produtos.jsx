import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { IconeBusca, IconePacoteBusca } from '../components/Icones';
import { listarProdutos, resumoAnalise } from '../services/dashboardService';
import './Dashboard.css';
import './Produtos.css';

const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const numero = (valor) => (valor === null || valor === undefined ? null : Number(valor));
const moeda = (valor) => {
  const convertido = numero(valor);
  return convertido === null || Number.isNaN(convertido) ? '—' : brl.format(convertido);
};

function statusProduto(produto, precoAtual) {
  if (!produto.alerta_ativo) return { chave: 'desativado', rotulo: 'Alerta desativado', classe: 'neutro' };
  const atual = numero(precoAtual);
  const alvo = numero(produto.preco_alvo);
  if (atual === null) return { chave: 'sem-dados', rotulo: 'Sem dados', classe: 'neutro' };
  if (alvo === null) return { chave: 'sem-alvo', rotulo: 'Sem preço-alvo', classe: 'neutro' };
  if (atual <= alvo) return { chave: 'atingido', rotulo: 'Preço atingido', classe: 'atingido' };
  return { chave: 'monitorando', rotulo: 'Em monitoramento', classe: 'monitorando' };
}

function Produtos() {
  const [produtos, setProdutos] = useState([]);
  const [resumo, setResumo] = useState({});
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [avisoResumo, setAvisoResumo] = useState('');
  const [busca, setBusca] = useState('');
  const [filtro, setFiltro] = useState('todos');
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro('');
    setAvisoResumo('');
    Promise.allSettled([listarProdutos(), resumoAnalise()]).then(([resultadoProdutos, resultadoResumo]) => {
      if (!ativo) return;
      if (resultadoProdutos.status === 'rejected') {
        setErro(resultadoProdutos.reason?.message || 'Não foi possível carregar seus produtos.');
        setCarregando(false);
        return;
      }
      setProdutos(resultadoProdutos.value);
      if (resultadoResumo.status === 'fulfilled') {
        setResumo(Object.fromEntries((resultadoResumo.value.produtos || []).map((item) => [item.produto_id, item])));
      } else {
        setResumo({});
        setAvisoResumo('Os preços atuais não puderam ser carregados. A lista de produtos continua disponível.');
      }
      setCarregando(false);
    });
    return () => {
      ativo = false;
    };
  }, [tentativa]);

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR');
    return produtos.filter((produto) => {
      const precoAtual = resumo[produto.produto_id]?.preco_atual;
      const status = statusProduto(produto, precoAtual);
      const correspondeTexto = !termo ||
        produto.nome?.toLocaleLowerCase('pt-BR').includes(termo) ||
        produto.loja?.nome?.toLocaleLowerCase('pt-BR').includes(termo);
      const correspondeFiltro = filtro === 'todos' ||
        (filtro === 'alertas' && produto.alerta_ativo) ||
        (filtro === 'atingidos' && status.chave === 'atingido') ||
        (filtro === 'sem-alvo' && status.chave === 'sem-alvo');
      return correspondeTexto && correspondeFiltro;
    });
  }, [produtos, resumo, busca, filtro]);

  const alertasAtivos = produtos.filter((produto) => produto.alerta_ativo).length;

  return (
    <div className="dash pagina-produtos">
      <div className="pagina-cabecalho">
        <div className="dash-titulo">
          <h1>Produtos monitorados</h1>
          <p className="sub">Consulte os produtos acompanhados e o status de cada alerta.</p>
        </div>
        <Link className="btn-primario pagina-cta" to="/produtos/novo">
          <span aria-hidden="true">＋</span> Cadastrar produto
        </Link>
      </div>

      <section className="cartoes produtos-resumo" aria-label="Resumo dos produtos">
        <div className="cartao">
          <IconePacoteBusca className="cartao-icone" tamanho={36} />
          <div className="cartao-corpo">
            <h2>Produtos monitorados</h2>
            <p className="cartao-valor">{produtos.length}</p>
          </div>
        </div>
        <div className="cartao">
          <span className="produtos-icone-alerta" aria-hidden="true">●</span>
          <div className="cartao-corpo">
            <h2>Alertas ativos</h2>
            <p className="cartao-valor">{alertasAtivos}</p>
          </div>
        </div>
      </section>

      <section className="painel" aria-labelledby="titulo-lista-produtos">
        <div className="painel-topo">
          <div className="painel-titulo">
            <IconePacoteBusca className="painel-icone" tamanho={32} />
            <div>
              <h2 id="titulo-lista-produtos">Sua lista</h2>
              <p className="sub">Busque por nome do produto ou loja e filtre pelo status.</p>
            </div>
          </div>
          <div className="produtos-filtros">
            <label className="busca">
              <span className="sr-only">Buscar produto ou loja</span>
              <IconeBusca className="busca-icone" tamanho={16} />
              <input
                type="search"
                placeholder="Buscar produto ou loja..."
                value={busca}
                onChange={(evento) => setBusca(evento.target.value)}
              />
            </label>
            <label className="relatorio-filtro">
              <span className="sr-only">Filtrar produtos</span>
              <select value={filtro} onChange={(evento) => setFiltro(evento.target.value)}>
                <option value="todos">Todos os produtos</option>
                <option value="alertas">Alertas ativos</option>
                <option value="atingidos">Preço-alvo atingido</option>
                <option value="sem-alvo">Sem preço-alvo</option>
              </select>
            </label>
          </div>
        </div>

        {avisoResumo && <p className="aviso" role="status">{avisoResumo}</p>}
        {carregando ? (
          <p className="vazio" role="status">Carregando produtos…</p>
        ) : erro ? (
          <div className="erro" role="alert">
            <p>{erro}</p>
            <button type="button" className="btn-link" onClick={() => setTentativa((valor) => valor + 1)}>
              Tentar novamente
            </button>
          </div>
        ) : produtos.length === 0 ? (
          <div className="estado-vazio">
            <p className="vazio">Você ainda não monitora nenhum produto.</p>
            <Link className="btn-primario" to="/produtos/novo">Cadastrar primeiro produto</Link>
          </div>
        ) : visiveis.length === 0 ? (
          <p className="vazio">Nenhum produto corresponde à busca ou ao filtro selecionado.</p>
        ) : (
          <div className="tabela-rolagem">
            <table className="produtos-tabela">
              <thead>
                <tr>
                  <th scope="col">Produto</th>
                  <th scope="col">Loja</th>
                  <th scope="col">Preço atual</th>
                  <th scope="col">Preço-alvo</th>
                  <th scope="col">Status do alerta</th>
                  <th scope="col">Página</th>
                </tr>
              </thead>
              <tbody>
                {visiveis.map((produto) => {
                  const atual = resumo[produto.produto_id]?.preco_atual;
                  const status = statusProduto(produto, atual);
                  return (
                    <tr key={produto.monitoramento_id || produto.produto_id}>
                      <td>
                        <div className="produto-celula">
                          <span className="miniatura">
                            {produto.imagem_url ? <img src={produto.imagem_url} alt="" /> : <IconePacoteBusca tamanho={18} />}
                          </span>
                          <span className="produto-texto">
                            <strong>{produto.nome}</strong>
                            {produto.categoria && <span className="produto-categoria">{produto.categoria}</span>}
                          </span>
                        </div>
                      </td>
                      <td>{produto.loja?.nome || '—'}</td>
                      <td>{moeda(atual)}</td>
                      <td>{moeda(produto.preco_alvo)}</td>
                      <td><span className={`selo selo-ponto selo-${status.classe}`}>{status.rotulo}</span></td>
                      <td>
                        {produto.url_produto ? (
                          <a className="relatorio-link" href={produto.url_produto} target="_blank" rel="noreferrer">Ver na loja</a>
                        ) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!carregando && !erro && produtos.length > 0 && (
          <p className="produtos-contagem" aria-live="polite">
            Exibindo {visiveis.length} de {produtos.length} produto{produtos.length === 1 ? '' : 's'}.
          </p>
        )}
      </section>
    </div>
  );
}

export default Produtos;
