/**
 * AST Index — maps DOM elements to Semantic State Tree nodes at event time.
 *
 * After the initial state is captured, this module:
 *   1. Assigns sequential `astNodeId` values to every StateNode in the tree
 *   2. Builds a selector→node-info lookup for leaf nodes
 *   3. Provides `matchElement(el)` to find the best AST match for a DOM element
 *
 * The index is rebuilt each time the initial state is updated (e.g. after
 * navigation or two-pass scoring replacement).
 */

import type { StateNode, AstMatch, AstMatchConfidence } from '@web-agent-flow/shared-types';

export interface AstNodeInfo {
  nodeId: string;
  nodePath: string;
  nodeType: string;
  nodeLabel?: string;
  nodeSelector?: string;
}

/**
 * Walk the StateNode tree, assign `astNodeId` to every node,
 * and collect leaf-node entries with selectors for lookup.
 */
function indexTree(
  nodes: StateNode[],
  parentPath: string,
  counter: { n: number },
  entries: AstNodeInfo[],
): void {
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    const id = `n${counter.n++}`;
    const path = parentPath ? `${parentPath}.${i}` : `${i}`;

    node.astNodeId = id;

    const info: AstNodeInfo = {
      nodeId: id,
      nodePath: path,
      nodeType: node.type,
      nodeLabel: node.label,
      nodeSelector: node.selector,
    };

    // Only leaf nodes with selectors are useful for DOM matching
    if (node.selector) {
      entries.push(info);
    }

    if (node.children) {
      indexTree(node.children, path, counter, entries);
    }
  }
}

export class AstIndex {
  /** All indexed leaf entries (selector present) */
  private entries: AstNodeInfo[] = [];

  /** Quick lookup: selector string → node info */
  private selectorMap = new Map<string, AstNodeInfo>();

  /** Quick lookup: nodeId → node info (includes containers) */
  private idMap = new Map<string, AstNodeInfo>();

  /**
   * Build the index from a stateTree. Mutates nodes by assigning `astNodeId`.
   */
  build(stateTree: StateNode[]): void {
    this.entries = [];
    this.selectorMap.clear();
    this.idMap.clear();

    const allEntries: AstNodeInfo[] = [];
    const counter = { n: 0 };

    // Walk full tree to assign IDs; collect all entries
    this.indexAll(stateTree, '', counter, allEntries);

    // Build lookup maps
    for (const entry of allEntries) {
      this.idMap.set(entry.nodeId, entry);
      if (entry.nodeSelector) {
        this.selectorMap.set(entry.nodeSelector, entry);
      }
    }

    // Keep only entries with selectors for DOM matching
    this.entries = allEntries.filter((e) => e.nodeSelector);
  }

  /**
   * Walk all nodes and assign IDs + collect entries (including containers).
   */
  private indexAll(
    nodes: StateNode[],
    parentPath: string,
    counter: { n: number },
    entries: AstNodeInfo[],
  ): void {
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const id = `n${counter.n++}`;
      const path = parentPath ? `${parentPath}.${i}` : `${i}`;

      node.astNodeId = id;

      const info: AstNodeInfo = {
        nodeId: id,
        nodePath: path,
        nodeType: node.type,
        nodeLabel: node.label,
        nodeSelector: node.selector,
      };

      entries.push(info);

      if (node.children) {
        this.indexAll(node.children, path, counter, entries);
      }
    }
  }

  get size(): number {
    return this.entries.length;
  }

  /**
   * Try to match a DOM element to an AST node.
   *
   * Strategy (in priority order):
   *   1. Exact selector match — the element matches a leaf node's CSS selector
   *   2. Ancestor match — walk up the DOM tree and try each ancestor's selector
   *   3. Fallback — no match; return context info for traceability
   */
  matchElement(element: Element): AstMatch {
    // Strategy 1: Try to find a direct selector match
    const directMatch = this.findByElement(element);
    if (directMatch) {
      return {
        confidence: 'exact',
        nodeId: directMatch.nodeId,
        nodePath: directMatch.nodePath,
        nodeType: directMatch.nodeType,
        nodeLabel: directMatch.nodeLabel,
        nodeSelector: directMatch.nodeSelector,
      };
    }

    // Strategy 2: Walk ancestors
    let current = element.parentElement;
    let depth = 0;
    while (current && current !== document.body && depth < 10) {
      const ancestorMatch = this.findByElement(current);
      if (ancestorMatch) {
        return {
          confidence: 'ancestor',
          nodeId: ancestorMatch.nodeId,
          nodePath: ancestorMatch.nodePath,
          nodeType: ancestorMatch.nodeType,
          nodeLabel: ancestorMatch.nodeLabel,
          nodeSelector: ancestorMatch.nodeSelector,
        };
      }
      current = current.parentElement;
      depth++;
    }

    // Strategy 3: Fallback — no AST match, provide context
    return {
      confidence: 'none',
      ancestorChain: buildAncestorChain(element),
      areaLabel: findNearestAreaLabel(element),
    };
  }

  /**
   * Try to find a matching entry for the given element by checking if
   * the element matches any indexed selector.
   */
  private findByElement(el: Element): AstNodeInfo | null {
    // Fast path: check the selectorMap directly using element's own selector-like id
    const id = el.getAttribute('id');
    if (id) {
      const byId = this.selectorMap.get(`#${id}`);
      if (byId) return byId;
    }

    // Try matching each indexed selector against the element
    for (const entry of this.entries) {
      if (!entry.nodeSelector) continue;
      try {
        if (el.matches(entry.nodeSelector)) {
          return entry;
        }
      } catch {
        // Invalid selector — skip
      }
    }

    return null;
  }
}

/**
 * Build a short ancestor chain string for fallback context.
 * e.g. "span > div.el-form-item__content > div.el-form-item"
 */
function buildAncestorChain(element: Element, maxDepth = 4): string {
  const parts: string[] = [];
  let el: Element | null = element;
  for (let i = 0; i < maxDepth && el && el !== document.body; i++) {
    const tag = el.tagName.toLowerCase();
    const cls = el.classList?.[0] ? `.${el.classList[0]}` : '';
    const id = el.id ? `#${el.id}` : '';
    parts.push(`${tag}${id || cls}`);
    el = el.parentElement;
  }
  return parts.join(' > ');
}

/**
 * Walk up the DOM to find the nearest heading / label that identifies the area.
 * Looks for: section headings, card titles, form-item labels, dialog titles.
 */
function findNearestAreaLabel(element: Element): string | undefined {
  let el: Element | null = element;
  for (let i = 0; i < 15 && el && el !== document.body; i++) {
    // Check for heading children in this container
    const heading = el.querySelector('h1, h2, h3, h4, [class*="title"], [class*="header"]');
    if (heading) {
      const text = heading.textContent?.trim();
      if (text && text.length <= 80) return text;
    }

    // Check for form-item label
    const label = el.querySelector('[class*="label"]');
    if (label) {
      const text = label.textContent?.trim();
      if (text && text.length <= 60 && text.length > 0) return text;
    }

    // Check aria-label
    const ariaLabel = el.getAttribute('aria-label');
    if (ariaLabel) return ariaLabel.slice(0, 80);

    el = el.parentElement;
  }

  return undefined;
}
