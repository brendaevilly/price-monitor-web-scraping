import { describe, expect, it } from 'vitest';
import { formatarPreco, parsePreco, urlPertenceALoja, validarUrlProduto } from './produto';

describe('validarUrlProduto', () => {
  it('aceita URL de produto e devolve o host sem www', () => {
    expect(validarUrlProduto('https://www.kabum.com.br/produto/123/mouse').host).toBe('kabum.com.br');
  });
  it.each([
    '', 'kabum.com.br/produto', 'ftp://loja.com/x', 'https://localhost/p', 'http://192.168.0.1/p',
    'https://loja.com.br', 'https://loja.com.br/', 'https://loja.com.br:8080/p', 'texto qualquer',
  ])('rejeita "%s"', (u) => expect(validarUrlProduto(u).erro).toBeTruthy());
  it('aceita home com query (mesma regra do backend)', () => {
    expect(validarUrlProduto('https://loja.com.br/?produto=1').host).toBe('loja.com.br');
  });
});

describe('urlPertenceALoja', () => {
  it('aceita o domínio e subdomínios, rejeita outros', () => {
    expect(urlPertenceALoja('kabum.com.br', 'kabum.com.br')).toBe(true);
    expect(urlPertenceALoja('m.kabum.com.br', 'kabum.com.br')).toBe(true);
    expect(urlPertenceALoja('naokabum.com.br', 'kabum.com.br')).toBe(false);
    expect(urlPertenceALoja('amazon.com.br', 'kabum.com.br')).toBe(false);
  });
});

describe('preço', () => {
  it('formata e converte', () => {
    expect(formatarPreco('129990')).toBe('R$ 1.299,90');
    expect(formatarPreco('5')).toBe('R$ 0,05');
    expect(formatarPreco('')).toBe('');
    expect(parsePreco('R$ 1.299,90')).toBe(1299.9);
    expect(parsePreco('')).toBeNull();
  });
});
