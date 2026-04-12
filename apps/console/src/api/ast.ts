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
