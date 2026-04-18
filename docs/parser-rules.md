# Initial State Parser — DOM-to-AST Rules

This document specifies the client-side DOM walker in
`apps/extension/src/recorder/initial-state.ts`. When modifying or extending
this parser, the following rules are **mandatory constraints**.

> **Note**: The primary AST pipeline is migrating to server-side HTML →
> Full AST (see [`architecture.md`](./architecture.md)). These client-side
> rules remain in effect for the extension code but new AST capabilities
> should be built server-side in `apps/api/app/services/html_ast_parser.py`.

## Core Principle: Unified Recursion + Fallback

The parser processes each DOM node through a unified recursive flow:

```
walkNode(el):
  1. classifyNode(el)     → unified classification
                            (known component > class/tag/id > native HTML > null)
  2. tryProcess(el, type) → attempt extraction with the matched processor
  3. processor returns empty → fall back to walkChildren generic recursion
  4. walkChildren also empty + visible content exists
                          → localHtml fallback (type: 'custom')
```

**No branch failure may silently discard content.** A processor returning `[]`
means "I cannot handle this, please fall back" — not "this element has no
content".

## Top Principle: DOM Fidelity First

The parser does not "understand the page then rewrite it" — it "faithfully
transcribes the page into a structured intermediate representation".

1. **Original DOM tree relationships first** — output JSON `children` order
   must match original DOM order.
2. **Sibling order first** — never reorder siblings for semantic abstraction.
3. **Node type first** — each DOM node should be preserved according to its
   actual type.
4. **Hidden nodes must be kept** — annotated via `cssState`, never skipped.
5. **Complex nodes must keep localHtml fallback** — when semantic extraction
   is insufficient.
6. **Never restructure original page structure** to form abstractions like
   "title + content" or "group + detail".

## Classification Priority (highest to lowest, first match wins)

1. **Known component library elements** — e.g. `el-select`, `ant-cascader`,
   `van-cell`, `n-date-picker`. Processed as a whole component type, **never
   decomposed into internal DOM structure** (e.g. `el-select` with an internal
   input is still treated as a select). The component classifier
   (`component-classifier.ts`) uses prefix-agnostic detection, covering 12+
   UI libraries.

2. **Identifiable custom structures via class/tag/id** — e.g.
   `class="xx-select"`, `role="listbox"` and other developer-named components,
   classified by pattern matching.

3. **Standard HTML semantic elements** — `<table>`, `<input>`, `<select>`,
   `<button>`, `<a>`, etc., processed according to native semantics.

4. **Unclassifiable elements** — recursively walkChildren to extract child
   node structure. If visible content exists but cannot be extracted,
   produces a `type: 'custom'` node with `localHtml` (max 500 characters).

## Element Type Rules

**Tables**: Extract headers and row data. Each cell in each row goes through
the unified `walkNode` processing path (not plain text extraction). A `table`
node has both `rows` (text summary for frontend display) and `children` (full
structure from walkNode for Agent analysis).

**Iframes**: Same-origin iframes are recursively parsed via `contentDocument`
(following the same rules); cross-origin iframes are silently skipped.
Produces a section node with `blockType: 'iframe-content'`. Multi-level
nested iframes are supported.

**Navigation areas**: Detected via HTML5 semantic tags (`nav`, `aside`,
`header`, `footer`) and ARIA roles (`role="navigation"`, etc.) **outside** the
main content root. Supports nested submenus (e.g. `el-submenu` +
`aria-haspopup`). Leaf nodes are `link` or `button` types with `href`,
`active` state, and `selector`. **Navigation and menu content must never be
skipped or discarded** — they are essential for cross-system operation
scenarios.

**Form containers**: Detected via known form-item patterns (`.el-form-item`,
`.ant-form-item`, etc.), processed as label + control pairs. If the content
area contains multiple interactive elements (≥2 non-simple controls, or ≥3
simple controls), recursively expanded as `group` + `children` rather than
flattened into a single leaf node. If `processFormItem` returns empty (e.g.
`el-form-item__actions` is actually a button container), **falls back** to
generic walkChildren.

## Multi-Frame Initial State Merging

A page may contain multiple frames (top-level + one or more iframes, iframes
may be nested). Each frame independently runs a content script and sends
`RECORDING_INITIAL_STATE`. The background's `setInitialState` (`state.ts`)
handles this as follows:

- **Duplicate sends from the same frameId** (e.g. content.ts two-pass) →
  score-based competitive replacement (keep the higher-scoring one).
- **Different frameIds** → **always merge**. The iframe's stateTree is
  appended as an `iframe-content` section to the existing state. Regardless
  of nesting depth or iframe count, every frame's content is preserved.
- **Never replace instead of merge** — top-level frame navigation/menus and
  iframe business content are equally important; a higher node count or
  score in an iframe must not overwrite the top-level content.

## Visibility Handling

All walk logic uses unified visibility handling — **never skip invisible
elements**. `shouldSkip` only filters `SKIP_TAGS` (script/style/svg and other
purely technical tags) and does not check `isVisible`. Invisible elements
(`display:none`, `visibility:hidden`) are still parsed and annotated via the
`cssState` field.

- `display:none` means not rendered and not clickable (e.g. collapsed menus).
- `visibility:hidden` means occupies space but still receives interaction.

**Different walk types (navigation vs content) must not use different
visibility handling** — all walks share the same rules.

## Truncation Fallback

When `MAX_NODES` (300) or `MAX_NAV_ITEMS` (100) cause collection to be
truncated, **remaining content must not be silently discarded**. Truncated
navigation areas get `localHtml` attached to the section node, preserving
the original HTML for future expansion.

## Information Retention Principle

Prioritize information with analytical value for the Agent to understand
page functionality: what the page does, what interactive elements exist,
what the current state is. Information with no immediate analytical value
but potentially needed later (e.g. complete navigation menu raw HTML) is
stored in `localHtml`, outside the Agent's primary analysis pipeline.

## Prohibited Practices

- **Never skip elements based on assumptions** — no hardcoded skip lists
  (except `SKIP_TAGS`). All elements must be processed (including invisible
  ones). Never assume developers follow semantic HTML conventions.
- **Never decompose known compound components** — `el-select` is one `select`
  node, not `input` + `div` + `ul`. Component boundaries are classification
  boundaries.
- **Never produce empty containers** — section/group nodes with empty children
  must be discarded.
- **Never silently discard content** — any classification failure must fall
  back to generic recursion; if generic recursion also fails and visible
  content exists, must produce localHtml fallback. Truncated content must
  preserve localHtml.
- **Never flatten complex structures** — if a container has multiple
  interactive child elements, must recursively expand into a subtree, not
  flatten into a single leaf + localHtml.
- **Never add specialized logic** — all processing rules must be generic, no
  if-else branches targeting specific component libraries or page structures.
  All walk types share the same filtering and processing rules.
- **Never restructure page structure for semantic tidiness** — do not merge
  parallel siblings into "title + content" blocks, do not alter node
  boundaries for "clarity", do not reorder nodes for "neatness", do not
  swallow intermediate tip/alert/button group/status text to form
  "title + content" patterns.
- **Never degrade complex cells to plain text** — table image columns must
  preserve `src`, action columns must preserve real buttons, `input-number`
  must be preserved as structured controls.
- **Never concatenate multiple buttons into a single string** — buttons must
  be preserved as individual nodes.
- **Never keep only the primary control while ignoring sibling auxiliary
  information** — tip/description/status text within a form-item must be
  preserved.

## Output Structure

- **Container nodes** (`section`, `group`): have `children[]`, `blockType`,
  `label`. **No `selector`**. May carry `localHtml` when truncated.
- **Leaf nodes** (`input`, `select`, `button`, `link`, `custom`, etc.): have
  `selector`, `value`, `label`. **No `children`**.
- **`table` nodes**: can be leaf (`rows[][]`) or container (`children[]`),
  depending on cell complexity.
- **`localHtml`**: only on leaf nodes where semantic extraction is
  insufficient, max 500 characters.
- **`rawHtmlSnapshot`**: standalone debug-only full HTML snapshot, not part
  of the AST.

## Tests

Multi-scenario tests (`apps/extension/src/__tests__/multi-scenario.test.ts`)
cover 8 fixture types: corporate website, admin panel, H5 mobile,
multi-nav docs page, no-semantic-tags page, data dashboard, Element UI
nested menu + iframe, complex nested structures (form-item with embedded
tables/sub-forms, table action columns).

**Any parser change must pass all existing fixture tests. New parsing
behavior must include corresponding fixtures and tests.**

## Reference Test Case

`apps/extension/src/__tests__/fixtures/lottery-page.html` is a full HTML
fixture from an actual user page.
`apps/extension/src/__tests__/fixtures/lottery-page-expected.jsonc` is the
**current (problematic) parser output**, with specific issues annotated via
`//` and `/* */` comments. This is NOT the correct expected output — it is
a problem checklist. New parser changes must address all annotated issues.
