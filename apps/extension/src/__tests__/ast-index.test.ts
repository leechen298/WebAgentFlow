/**
 * Tests for AstIndex — event-to-AST-node matching.
 *
 * Covers:
 *   1. Index building assigns astNodeId to all nodes
 *   2. Exact match when target matches a leaf node's selector
 *   3. Ancestor match when target is inside a leaf node
 *   4. Fallback (confidence: none) when no match found
 *   5. Fallback includes ancestorChain and areaLabel context
 *   6. Index rebuilding clears previous state
 */

import { describe, it, expect, beforeEach } from 'vitest';
import type { StateNode } from '@web-agent-flow/shared-types';
import { AstIndex } from '../recorder/ast-index';

// ── Helpers ────────────────────────────────────────────────────────────────

function makeTree(): StateNode[] {
  return [
    {
      type: 'section',
      label: 'Login Form',
      blockType: 'form-section',
      children: [
        {
          type: 'input',
          label: 'Username',
          selector: '#username',
          value: '',
        },
        {
          type: 'input',
          label: 'Password',
          selector: '#password',
          value: '',
        },
        {
          type: 'button',
          label: 'Submit',
          selector: 'button.submit-btn',
        },
      ],
    },
    {
      type: 'section',
      label: 'Navigation',
      blockType: 'navigation',
      children: [
        {
          type: 'link',
          label: 'Home',
          selector: 'a.nav-home',
          href: '/',
        },
        {
          type: 'link',
          label: 'About',
          selector: 'a.nav-about',
          href: '/about',
        },
      ],
    },
  ];
}

function setupDOM(): void {
  document.body.innerHTML = `
    <div class="page">
      <form id="login-form">
        <h2>Login Form</h2>
        <div class="form-item">
          <label>Username</label>
          <input id="username" type="text" />
        </div>
        <div class="form-item">
          <label>Password</label>
          <input id="password" type="password" />
        </div>
        <button class="submit-btn">Submit</button>
      </form>
      <nav>
        <a class="nav-home" href="/">Home</a>
        <a class="nav-about" href="/about">About</a>
      </nav>
      <div class="unrelated-content">
        <span class="orphan">Some text</span>
      </div>
    </div>
  `;
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('AstIndex', () => {
  let index: AstIndex;
  let tree: StateNode[];

  beforeEach(() => {
    index = new AstIndex();
    tree = makeTree();
    setupDOM();
  });

  describe('build()', () => {
    it('assigns astNodeId to every node in the tree', () => {
      index.build(tree);

      // Root sections
      expect(tree[0].astNodeId).toBe('n0');
      expect(tree[1].astNodeId).toBe('n4');

      // Children of first section
      expect(tree[0].children![0].astNodeId).toBe('n1'); // Username input
      expect(tree[0].children![1].astNodeId).toBe('n2'); // Password input
      expect(tree[0].children![2].astNodeId).toBe('n3'); // Submit button

      // Children of second section
      expect(tree[1].children![0].astNodeId).toBe('n5'); // Home link
      expect(tree[1].children![1].astNodeId).toBe('n6'); // About link
    });

    it('reports correct number of indexed leaf nodes', () => {
      index.build(tree);
      // 5 leaf nodes with selectors: username, password, submit, home, about
      expect(index.size).toBe(5);
    });
  });

  describe('matchElement() — exact match', () => {
    it('matches input#username to the Username AST node', () => {
      index.build(tree);
      const el = document.querySelector('#username')!;
      const match = index.matchElement(el);

      expect(match.confidence).toBe('exact');
      expect(match.nodeId).toBe('n1');
      expect(match.nodePath).toBe('0.0');
      expect(match.nodeType).toBe('input');
      expect(match.nodeLabel).toBe('Username');
    });

    it('matches button.submit-btn to the Submit AST node', () => {
      index.build(tree);
      const el = document.querySelector('button.submit-btn')!;
      const match = index.matchElement(el);

      expect(match.confidence).toBe('exact');
      expect(match.nodeId).toBe('n3');
      expect(match.nodeType).toBe('button');
      expect(match.nodeLabel).toBe('Submit');
    });

    it('matches a.nav-home to the Home link AST node', () => {
      index.build(tree);
      const el = document.querySelector('a.nav-home')!;
      const match = index.matchElement(el);

      expect(match.confidence).toBe('exact');
      expect(match.nodeId).toBe('n5');
      expect(match.nodeType).toBe('link');
      expect(match.nodeLabel).toBe('Home');
    });
  });

  describe('matchElement() — ancestor match', () => {
    it('matches a child of a leaf node via ancestor walk', () => {
      // Add a span inside the submit button
      const btn = document.querySelector('button.submit-btn')!;
      const span = document.createElement('span');
      span.textContent = 'Submit';
      btn.appendChild(span);

      index.build(tree);
      const match = index.matchElement(span);

      expect(match.confidence).toBe('ancestor');
      expect(match.nodeId).toBe('n3');
      expect(match.nodeType).toBe('button');
      expect(match.nodeLabel).toBe('Submit');
    });
  });

  describe('matchElement() — no match (fallback)', () => {
    it('returns confidence:none for unmatched elements', () => {
      index.build(tree);
      const el = document.querySelector('.orphan')!;
      const match = index.matchElement(el);

      expect(match.confidence).toBe('none');
      expect(match.nodeId).toBeUndefined();
      expect(match.ancestorChain).toBeDefined();
      expect(match.ancestorChain).toContain('span');
    });

    it('provides ancestorChain in fallback', () => {
      index.build(tree);
      const el = document.querySelector('.orphan')!;
      const match = index.matchElement(el);

      // Should contain tag chain like "span.orphan > div.unrelated-content > ..."
      expect(match.ancestorChain).toMatch(/span/);
      expect(match.ancestorChain!.split(' > ').length).toBeGreaterThan(1);
    });
  });

  describe('matchElement() — ancestor match stability', () => {
    it('matches deeply nested child to nearest ancestor leaf', () => {
      // Create a deep nesting inside the submit button
      const btn = document.querySelector('button.submit-btn')!;
      const div = document.createElement('div');
      const span = document.createElement('span');
      const icon = document.createElement('i');
      icon.className = 'icon-check';
      span.appendChild(icon);
      div.appendChild(span);
      btn.appendChild(div);

      index.build(tree);
      const match = index.matchElement(icon);

      expect(match.confidence).toBe('ancestor');
      expect(match.nodeId).toBe('n3');
      expect(match.nodeType).toBe('button');
      expect(match.nodeLabel).toBe('Submit');
    });

    it('matches a sibling-added element inside a form-item to the input', () => {
      // Add a validation icon next to the username input
      const input = document.querySelector('#username')!;
      const suffix = document.createElement('span');
      suffix.className = 'input-suffix';
      suffix.textContent = 'ok';
      input.parentElement!.appendChild(suffix);

      index.build(tree);
      // The suffix is a sibling of #username, not inside it
      // It won't match #username directly — should fall through to fallback or ancestor
      const match = index.matchElement(suffix);
      // The suffix is a sibling, not a descendant — walks up to form-item div
      // which doesn't match any indexed selector → eventually confidence: none
      // This is correct: the suffix is not the input
      expect(match.confidence).toBe('none');
      expect(match.ancestorChain).toBeDefined();
    });
  });

  describe('matchElement() — areaLabel does not return self text', () => {
    it('does not return the clicked element own text as areaLabel', () => {
      // Add a title-like element that will be the click target
      document.body.innerHTML = `
        <div class="wrapper">
          <h2 class="title">Section Title</h2>
          <div class="orphan-area">
            <span class="title">Click Me Title</span>
          </div>
        </div>
      `;

      index.build([]); // empty tree so nothing matches
      const clickTarget = document.querySelector('span.title')!;
      const match = index.matchElement(clickTarget);

      expect(match.confidence).toBe('none');
      // areaLabel should NOT be "Click Me Title" (that's self)
      // It should be from a parent, like "Section Title" from the wrapper
      if (match.areaLabel) {
        expect(match.areaLabel).not.toBe('Click Me Title');
      }
    });

    it('finds parent area label correctly', () => {
      document.body.innerHTML = `
        <div class="card">
          <h3>Card Heading</h3>
          <div class="card-body">
            <span class="some-element">target</span>
          </div>
        </div>
      `;

      index.build([]);
      const target = document.querySelector('.some-element')!;
      const match = index.matchElement(target);

      expect(match.confidence).toBe('none');
      expect(match.areaLabel).toBe('Card Heading');
    });
  });

  describe('rebuild', () => {
    it('clears previous index on rebuild', () => {
      index.build(tree);
      expect(index.size).toBe(5);

      // Build with a smaller tree
      const smallTree: StateNode[] = [
        { type: 'button', label: 'Only', selector: 'button.submit-btn' },
      ];
      index.build(smallTree);
      expect(index.size).toBe(1);

      // Previous selectors should not match
      const el = document.querySelector('#username')!;
      const match = index.matchElement(el);
      expect(match.confidence).toBe('none');
    });
  });

  describe('empty/edge cases', () => {
    it('handles empty stateTree without error', () => {
      index.build([]);
      expect(index.size).toBe(0);

      const el = document.querySelector('#username')!;
      const match = index.matchElement(el);
      expect(match.confidence).toBe('none');
    });

    it('handles tree with no selectors (all containers)', () => {
      const containerOnly: StateNode[] = [
        {
          type: 'section',
          label: 'Container Only',
          children: [
            { type: 'group', label: 'Nested Group', children: [] },
          ],
        },
      ];
      index.build(containerOnly);
      expect(index.size).toBe(0); // no leaf selectors

      const el = document.querySelector('#username')!;
      const match = index.matchElement(el);
      expect(match.confidence).toBe('none');
    });
  });
});
