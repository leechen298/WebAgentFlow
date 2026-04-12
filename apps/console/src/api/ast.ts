import apiClient from './client';

/** A node in the server-side Full AST. */
export interface ASTNode {
  node_type: 'element' | 'text';
  tag?: string;
  attrs?: Record<string, string>;
  children?: ASTNode[];
  text?: string;
  visible?: boolean;
}

/** Result of HTML → Full AST parsing. */
export interface FullAST {
  nodes: ASTNode[];
  node_count: number;
}

/** Simplification statistics. */
export interface SimplifyStats {
  node_count: number;
  attrs_removed: number;
  class_tokens_removed: number;
}

/** Result of Full AST → Simplified AST projection. */
export interface SimplifiedAST {
  nodes: ASTNode[];
  stats: SimplifyStats;
}

/** Parse HTML into a Full AST via the server. */
export async function parseHtmlToAST(
  html: string,
  iframeHtml?: Record<string, string>,
): Promise<FullAST> {
  return (await apiClient.post('/ast/parse', {
    html,
    iframe_html: iframeHtml ?? null,
  })) as unknown as FullAST;
}

/** Parse HTML and produce a Simplified AST (structure-preserving, pruned attrs/class). */
export async function simplifyHtmlToAST(
  html: string,
  iframeHtml?: Record<string, string>,
): Promise<SimplifiedAST> {
  return (await apiClient.post('/ast/simplify', {
    html,
    iframe_html: iframeHtml ?? null,
  })) as unknown as SimplifiedAST;
}
