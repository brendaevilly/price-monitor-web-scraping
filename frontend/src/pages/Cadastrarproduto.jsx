import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { criarLoja, criarProduto, listarLojas, ProdutoError } from '../services/produtoService';
import { formatarPreco, normalizar, parsePreco, urlPertenceALoja, validarUrlProduto } from '../utils/produto';
import './CadastrarProduto.css';

const msgLojaNaoIdentificada = (loja) =>
  `A URL não pertence à loja "${loja.nome}" (${loja.dominio}). Confira o nome da loja ou o link.`;

function CadastrarProduto() {
  const navigate = useNavigate();
  const { token, sair } = useAuth();
  const nomeRef = useRef(null);

  const [nome, setNome] = useState('');
  const [url, setUrl] = useState('');
  const [loja, setLoja] = useState('');
  const [preco, setPreco] = useState('');
  const [erros, setErros] = useState({});
  const [erroGeral, setErroGeral] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [enviando, setEnviando] = useState(false);

  const limpar = (...campos) => {
    setSucesso('');
    setErros((e) => Object.fromEntries(Object.entries(e).filter(([k]) => !campos.includes(k))));
  };

  function validar() {
    const e = {};
    if (nome.trim().length < 2) e.nome = 'Informe o nome do produto (mínimo 2 caracteres).';
    const u = validarUrlProduto(url);
    if (u.erro) e.url = u.erro;
    if (loja.trim().length < 2) e.loja = 'Informe a loja.';
    const alvo = parsePreco(preco);
    if (preco && !(alvo > 0)) e.preco = 'O preço-alvo deve ser maior que zero.';
    return { erros: e, host: u.host };
  }

  // Descobre a loja pela URL; cria (POST /lojas) só se ela ainda não existir.
  async function obterLoja(host) {
    const lojas = await listarLojas(token);
    const porDominio = lojas.find((l) => urlPertenceALoja(host, l.dominio));
    const porNome = lojas.find((l) => normalizar(l.nome) === normalizar(loja));

    if (porDominio) {
      // Nome informado é de outra loja cadastrada: o usuário errou a loja ou o link.
      if (porNome && porNome.id !== porDominio.id) throw new ProdutoError('', { campos: { loja: msgLojaNaoIdentificada(porNome) } });
      return porDominio;
    }
    // Fluxo 3a: a loja existe, mas a URL é de outro domínio.
    if (porNome) throw new ProdutoError('', { campos: { loja: msgLojaNaoIdentificada(porNome) } });

    try {
      return await criarLoja(token, { nome: loja.trim(), dominio: host });
    } catch (err) {
      if (err.status !== 409) throw err;
      // Outra requisição criou a loja no meio do caminho: busca de novo.
      const atual = (await listarLojas(token)).find((l) => urlPertenceALoja(host, l.dominio));
      if (atual) return atual;
      throw err;
    }
  }

  async function aoEnviar(ev) {
    ev.preventDefault();
    if (enviando) return;
    setErroGeral('');
    setSucesso('');

    const { erros: e, host } = validar();
    setErros(e);
    const primeiro = Object.keys(e)[0];
    if (primeiro) {
      document.getElementById(`campo-${primeiro}`)?.focus();
      return;
    }

    setEnviando(true);
    try {
      const lojaFinal = await obterLoja(host);
      await criarProduto(token, {
        nome: nome.trim(),
        urlProduto: url.trim(),
        lojaId: lojaFinal.id,
        precoAlvo: parsePreco(preco),
      });
      setNome(''); setUrl(''); setLoja(''); setPreco('');
      setSucesso('Produto cadastrado e adicionado ao monitoramento.');
      nomeRef.current?.focus();
    } catch (err) {
      if (err.status === 401) { sair(); return; } // ProtectedRoute leva para /login
      const campos = err.campos || {};
      if (Object.keys(campos).length) {
        setErros(campos);
        document.getElementById(`campo-${Object.keys(campos)[0]}`)?.focus();
      } else {
        setErroGeral(err.message || 'Erro ao cadastrar o produto.');
      }
    } finally {
      setEnviando(false);
    }
  }

  const campo = (id, rotulo, obrigatorio, input) => (
    <div className="cp-campo">
      <label htmlFor={`campo-${id}`} className="cp-rotulo">
        {rotulo}
        {obrigatorio ? <span className="cp-obrigatorio" aria-hidden="true"> *</span> : <span className="cp-opcional"> (opcional)</span>}
      </label>
      {input}
      {erros[id] && <p id={`erro-${id}`} className="cp-erro" role="alert">{erros[id]}</p>}
    </div>
  );

  const comuns = (id) => ({
    id: `campo-${id}`,
    className: 'cp-input',
    'aria-invalid': !!erros[id],
    'aria-describedby': erros[id] ? `erro-${id}` : undefined,
    disabled: enviando,
  });

  return (
    <section className="cp-pagina">
      <button type="button" className="cp-voltar" onClick={() => navigate('/dashboard')}>← Voltar</button>
      <h1 className="cp-titulo">Cadastrar produto</h1>
      <p className="cp-sub">Informe os dados do produto que deseja monitorar</p>

      <form className="cp-card" onSubmit={aoEnviar} noValidate>
        {sucesso && <p className="cp-sucesso" role="status">{sucesso}</p>}
        {erroGeral && <p className="cp-erro-geral" role="alert">{erroGeral}</p>}

        {campo('nome', 'Nome do produto', true,
          <input {...comuns('nome')} ref={nomeRef} value={nome} placeholder="Ex: Console PlayStation 5" autoFocus
            onChange={(e) => { setNome(e.target.value); limpar('nome'); }} />)}

        {campo('url', 'URL do produto', true,
          <input {...comuns('url')} type="url" inputMode="url" value={url} placeholder="https://www.loja.com.br/produto"
            onChange={(e) => { setUrl(e.target.value); limpar('url', 'loja'); }} />)}

        {campo('loja', 'Loja', true,
          <input {...comuns('loja')} value={loja} placeholder="Ex: Amazon, Kabum, Magalu"
            onChange={(e) => { setLoja(e.target.value); limpar('loja'); }} />)}

        {campo('preco', 'Preço-Alvo', false,
          <input {...comuns('preco')} inputMode="numeric" value={preco} placeholder="R$ 0,00"
            onChange={(e) => { setPreco(formatarPreco(e.target.value)); limpar('preco'); }} />)}

        <button type="submit" className="cp-botao" disabled={enviando}>
          {enviando ? 'Cadastrando...' : 'Cadastrar produto'}
        </button>
      </form>
    </section>
  );
}

export default CadastrarProduto;
