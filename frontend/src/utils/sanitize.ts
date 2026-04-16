/**
 * ENGENHARIA CAD - Sanitização de HTML
 * Utilitário para prevenir ataques XSS
 */
import DOMPurify from 'dompurify';

/**
 * Configuração padrão do DOMPurify
 * Permite apenas tags seguras para markdown rendering
 */
const ALLOWED_TAGS = [
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'p', 'span', 'div', 'br', 'hr',
  'ul', 'ol', 'li',
  'strong', 'b', 'em', 'i', 'u',
  'code', 'pre', 'blockquote',
  'a', 'img',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
];

const ALLOWED_ATTR = [
  'href', 'src', 'alt', 'title', 'class', 'style',
  'target', 'rel', 'width', 'height',
];

/**
 * Sanitiza HTML para prevenir XSS
 * @param dirty - HTML potencialmente perigoso
 * @returns HTML seguro
 */
export function sanitizeHTML(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ['target'],
    FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'input', 'button'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
  });
}

/**
 * Sanitiza texto removendo todas as tags HTML
 * Útil para inputs de texto puro
 * @param dirty - Texto com possíveis tags HTML
 * @returns Texto limpo sem HTML
 */
export function sanitizeText(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
  });
}

/**
 * Escapa caracteres especiais HTML
 * Alternativa leve quando não precisa de DOMPurify completo
 * @param text - Texto para escapar
 * @returns Texto com caracteres HTML escapados
 */
export function escapeHTML(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (char) => map[char]);
}

/**
 * Valida e sanitiza URL
 * @param url - URL potencialmente perigosa
 * @returns URL segura ou string vazia se inválida
 */
export function sanitizeURL(url: string): string {
  try {
    const parsed = new URL(url);
    // Permitir apenas protocolos seguros
    if (!['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
      return '';
    }
    return parsed.href;
  } catch {
    // Se não for uma URL válida, pode ser relativa
    if (url.startsWith('/') && !url.startsWith('//')) {
      return url;
    }
    return '';
  }
}

export default {
  sanitizeHTML,
  sanitizeText,
  escapeHTML,
  sanitizeURL,
};
