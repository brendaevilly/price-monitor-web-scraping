// Espelha as regras de app/utils/urls.py (RF05, RN03) para dar resposta imediata.
// O backend continua sendo a validação oficial.
const SUFIXOS_INTERNOS = ['.localhost', '.local', '.internal', '.lan', '.home'];
const LABEL = /^(?!-)[a-z0-9-]{1,63}(?<!-)$/;
const TLD = /^([a-z]{2,63}|xn--[a-z0-9-]{1,59})$/;
const ehIp = (h) => h.startsWith('[') || /^\d{1,3}(\.\d{1,3}){3}$/.test(h);

export const normalizar = (s) =>
  (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();

const SEM_WWW = (h) => (h.startsWith('www.') ? h.slice(4) : h);

/** Retorna { host } (sem www) quando válida, ou { erro } com a mensagem para o usuário. */
export function validarUrlProduto(bruto) {
  const valor = (bruto || '').trim();
  if (!valor) return { erro: 'Informe a URL do produto.' };
  if (valor.length > 2048) return { erro: 'A URL do produto é longa demais.' };

  let url;
  try {
    url = new URL(valor);
  } catch {
    return { erro: 'URL inválida. Use um link completo, como https://www.loja.com.br/produto.' };
  }
  if (!['http:', 'https:'].includes(url.protocol)) return { erro: 'A URL deve começar com http:// ou https://.' };
  if (url.username || url.password) return { erro: 'A URL não pode conter usuário ou senha.' };
  if (!['', '80', '443'].includes(url.port)) return { erro: 'A URL usa uma porta não permitida.' };

  const host = url.hostname.toLowerCase().replace(/\.$/, '');
  if (ehIp(host)) return { erro: 'Endereços IP não são aceitos; informe o domínio da loja.' };
  if (host === 'localhost' || SUFIXOS_INTERNOS.some((s) => host.endsWith(s))) {
    return { erro: 'Apenas endereços públicos de lojas são aceitos.' };
  }
  const partes = host.split('.');
  if (partes.length < 2 || !partes.every((p) => LABEL.test(p)) || !TLD.test(partes[partes.length - 1])) {
    return { erro: 'O domínio da URL é inválido (ex.: minhaloja.com.br).' };
  }
  // RN03: precisa ser a página de um produto, não a home da loja.
  if (url.pathname === '/' && !url.search) {
    return { erro: 'Informe a URL da página do produto, não a página inicial da loja.' };
  }
  return { host: SEM_WWW(host) };
}

/** True se o host é o domínio da loja ou subdomínio dele (mesma regra do backend). */
export function urlPertenceALoja(host, dominioLoja) {
  const d = SEM_WWW((dominioLoja || '').toLowerCase());
  return host === d || host.endsWith(`.${d}`);
}

/** Máscara de moeda: "129990" -> "R$ 1.299,90". Vazio fica vazio. */
export function formatarPreco(digitos) {
  const d = String(digitos).replace(/\D/g, '').replace(/^0+/, '');
  if (!d) return '';
  const c = d.padStart(3, '0');
  const inteiro = c.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `R$ ${inteiro},${c.slice(-2)}`;
}

/** "R$ 1.299,90" -> 1299.9; vazio -> null. */
export function parsePreco(mascarado) {
  const d = String(mascarado).replace(/\D/g, '');
  return d ? Number(d) / 100 : null;
}
