/**
 * Component Classifier — systematic, prefix-agnostic UI component detection.
 *
 * Instead of hardcoding 50+ library-specific class selectors, this module:
 *   1. Strips known library prefixes → matches component name vocabulary
 *   2. Checks ARIA roles (works across ALL libraries)
 *   3. Uses structural heuristics for non-library components (editors, etc.)
 *   4. Falls back to native HTML element detection
 *
 * Priority system resolves nesting: e.g. el-select wraps el-input →
 * select (priority 2) beats input (priority 1).
 */

// ─── Component types ────────────────────────────────────────────────────────

export type ComponentType =
  // Simple form controls (priority 1)
  | 'input' | 'textarea' | 'checkbox' | 'radio' | 'switch' | 'slider' | 'rate' | 'number'
  // Compound form controls (priority 2)
  | 'select' | 'cascader' | 'date' | 'time' | 'autocomplete' | 'color'
  | 'upload' | 'transfer' | 'richtext' | 'code-editor'
  // Structural (priority 3)
  | 'form-item' | 'table' | 'tree' | 'tabs' | 'steps' | 'breadcrumb'
  | 'collapse' | 'descriptions' | 'statistic' | 'pagination'
  | 'dialog' | 'drawer' | 'progress' | 'alert'
  // Layout / skip (priority 0)
  | 'layout' | 'navigation' | 'menu' | 'skip';

// ─── Known library prefixes ─────────────────────────────────────────────────

const KNOWN_PREFIXES = [
  'el-',     // Element UI / Element Plus
  'ant-',    // Ant Design / Ant Design Vue
  'n-',      // Naive UI
  'arco-',   // Arco Design (ByteDance)
  'ivu-',    // iView / View UI
  'van-',    // Vant (mobile)
  'nut-',    // NutUI (JD, mobile)
  't-',      // TDesign (Tencent)
  'semi-',   // Semi Design (ByteDance)
  'v-',      // Vuetify
  'p-',      // PrimeVue
];

// ─── Component name vocabulary → type mapping ───────────────────────────────

const COMPONENT_NAME_MAP: Record<string, ComponentType> = {
  // Form containers
  'form-item': 'form-item',
  'form-group': 'form-item',
  'form-field': 'form-item',
  'field': 'form-item',

  // Simple form controls (priority 1)
  'input': 'input',
  'textarea': 'textarea',
  'checkbox': 'checkbox',
  'checkbox-group': 'checkbox',
  'radio': 'radio',
  'radio-group': 'radio',
  'switch': 'switch',
  'slider': 'slider',
  'rate': 'rate',
  'rating': 'rate',
  'stepper': 'number',

  // Compound form controls (priority 2)
  'select': 'select',
  'cascader': 'cascader',
  'input-number': 'number',
  'inputnumber': 'number',
  'date-editor': 'date',
  'date-picker': 'date',
  'datepicker': 'date',
  'time-picker': 'time',
  'picker': 'date',
  'calendar': 'date',
  'autocomplete': 'autocomplete',
  'auto-complete': 'autocomplete',
  'mentions': 'autocomplete',
  'color-picker': 'color',
  'colorpicker': 'color',
  'upload': 'upload',
  'uploader': 'upload',
  'file-input': 'upload',
  'transfer': 'transfer',
  'picklist': 'transfer',

  // Navigation / chrome
  'pagination': 'pagination',
  'tabs': 'tabs',
  'tab-pane': 'tabs',
  'tabview': 'tabs',
  'steps': 'steps',
  'step': 'steps',
  'breadcrumb': 'breadcrumb',
  'menu': 'menu',
  'menu-item': 'menu',
  'submenu': 'menu',
  'navigation': 'navigation',
  'navigation-drawer': 'navigation',
  'tabbar': 'navigation',

  // Feedback
  'dialog': 'dialog',
  'modal': 'dialog',
  'drawer': 'drawer',
  'sidesheet': 'drawer',
  'progress': 'progress',
  'collapse': 'collapse',
  'expansion-panels': 'collapse',
  'accordion': 'collapse',

  // Data display
  'table': 'table',
  'data-table': 'table',
  'tree': 'tree',
  'treeview': 'tree',
  'descriptions': 'descriptions',
  'statistic': 'statistic',

  // Layout (skip)
  'aside': 'layout',
  'header': 'layout',
  'footer': 'layout',
  'main': 'layout',
  'container': 'layout',
  'layout': 'layout',
  'sider': 'layout',
  'app-bar': 'layout',
};

// ─── ARIA role → type mapping ───────────────────────────────────────────────

const ARIA_ROLE_MAP: Record<string, ComponentType> = {
  'textbox': 'input',
  'spinbutton': 'number',
  'combobox': 'select',
  'listbox': 'select',
  'checkbox': 'checkbox',
  'radio': 'radio',
  'radiogroup': 'radio',
  'switch': 'switch',
  'slider': 'slider',
  'progressbar': 'progress',
  'tablist': 'tabs',
  'tree': 'tree',
  'dialog': 'dialog',
  'alertdialog': 'dialog',
  'menu': 'menu',
  'menubar': 'menu',
  'navigation': 'navigation',
  'table': 'table',
  'grid': 'table',
  'separator': 'layout',
  'tooltip': 'skip',
};

// ─── Component type priority (for nesting resolution) ───────────────────────

const COMPONENT_PRIORITY: Partial<Record<ComponentType, number>> = {
  // Priority 0 — skip / layout
  'layout': 0, 'navigation': 0, 'menu': 0, 'skip': 0,
  // Priority 1 — simple controls
  'input': 1, 'textarea': 1, 'checkbox': 1, 'radio': 1,
  'switch': 1, 'slider': 1, 'rate': 1, 'number': 1,
  // Priority 2 — compound controls
  'select': 2, 'cascader': 2, 'date': 2, 'time': 2,
  'autocomplete': 2, 'color': 2, 'upload': 2, 'transfer': 2,
  'richtext': 2, 'code-editor': 2,
  // Priority 3 — structural
  'form-item': 3, 'table': 3, 'tree': 3, 'tabs': 3,
  'steps': 3, 'breadcrumb': 3, 'collapse': 3,
  'descriptions': 3, 'statistic': 3, 'pagination': 3,
  'dialog': 3, 'drawer': 3, 'progress': 3, 'alert': 3,
};

// ─── Class name → component name extraction ─────────────────────────────────

/**
 * Extract component names from an element's class list by stripping known
 * library prefixes and BEM suffixes (__*, --*).
 */
function extractComponentNames(el: Element): string[] {
  const classList = el.getAttribute('class');
  if (!classList) return [];

  const names: string[] = [];
  for (const cls of classList.split(/\s+/)) {
    if (!cls) continue;

    // Check for MUI-style camelCase classes (MuiSelect-root → select)
    const muiMatch = cls.match(/^Mui(\w+?)[-_]/);
    if (muiMatch) {
      names.push(muiMatch[1].toLowerCase());
      continue;
    }

    // Check known prefixes
    for (const prefix of KNOWN_PREFIXES) {
      if (cls.startsWith(prefix)) {
        // Strip prefix, then strip BEM suffixes (__*, --*)
        let name = cls.slice(prefix.length);
        name = name.replace(/(__|--).*$/, '');
        if (name) names.push(name);
        break;
      }
    }
  }

  return names;
}

function classifyByClassName(el: Element): ComponentType | undefined {
  const names = extractComponentNames(el);
  for (const name of names) {
    const type = COMPONENT_NAME_MAP[name];
    if (type) return type;
  }
  return undefined;
}

// ─── Structural heuristics (editors, etc.) ──────────────────────────────────

function hasToolbarSibling(editableEl: Element): boolean {
  let el: Element | null = editableEl;
  for (let depth = 0; depth < 3 && el; depth++) {
    const parent = el.parentElement;
    if (!parent) break;
    for (const sibling of parent.children) {
      if (sibling === el) continue;
      const role = sibling.getAttribute('role');
      if (role === 'toolbar') return true;
      const cls = (sibling.className || '').toLowerCase();
      if (/toolbar|menubar|ql-toolbar|ck-toolbar|w-e-bar|tox-toolbar/.test(cls)) return true;
    }
    el = parent;
  }
  return false;
}

function classifyByStructure(el: Element): ComponentType | undefined {
  // Rich text editors
  if (el.getAttribute('contenteditable') === 'true') {
    if (el.classList.contains('ProseMirror')) return 'richtext';
    if (el.classList.contains('ql-editor')) return 'richtext';
    if (el.classList.contains('ck-content')) return 'richtext';
    if (el.getAttribute('data-slate-editor') === 'true') return 'richtext';
    if (el.closest('.w-e-text-container')) return 'richtext';
    if (hasToolbarSibling(el)) return 'richtext';
  }
  // TinyMCE (iframe-based)
  if (el.classList.contains('tox-tinymce')) return 'richtext';

  // Code editors
  if (el.classList.contains('monaco-editor')) return 'code-editor';
  if (el.classList.contains('CodeMirror')) return 'code-editor';
  if (el.classList.contains('cm-editor')) return 'code-editor';
  if (el.querySelector('[data-mode-id]')) return 'code-editor';

  return undefined;
}

// ─── Native HTML element detection ──────────────────────────────────────────

function classifyByNativeHTML(el: Element): ComponentType | undefined {
  const tag = el.tagName.toLowerCase();
  switch (tag) {
    case 'input': {
      const type = (el as HTMLInputElement).type || 'text';
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      if (type === 'range') return 'slider';
      if (type === 'number') return 'number';
      if (type === 'file') return 'upload';
      if (type === 'color') return 'color';
      if (type === 'date' || type === 'datetime-local' || type === 'month' || type === 'week') return 'date';
      if (type === 'time') return 'time';
      return 'input';
    }
    case 'textarea': return 'textarea';
    case 'select': return 'select';
    case 'fieldset': return 'form-item';
    case 'table': return 'table';
    case 'nav': return 'navigation';
    case 'dialog': return 'dialog';
    case 'progress': return 'progress';
    case 'meter': return 'progress';
    default: return undefined;
  }
}

// ─── Main classifier ────────────────────────────────────────────────────────

export interface ClassificationResult {
  type: ComponentType;
  source: 'aria' | 'class' | 'structure' | 'native';
}

export function classifyElement(el: Element): ClassificationResult | undefined {
  // 1. ARIA role
  const role = el.getAttribute('role');
  if (role && ARIA_ROLE_MAP[role]) {
    return { type: ARIA_ROLE_MAP[role], source: 'aria' };
  }

  // 2. Component name from class (prefix-agnostic)
  const componentType = classifyByClassName(el);
  if (componentType) return { type: componentType, source: 'class' };

  // 3. Structural heuristics (editors, etc.)
  const structType = classifyByStructure(el);
  if (structType) return { type: structType, source: 'structure' };

  // 4. Native HTML
  const nativeType = classifyByNativeHTML(el);
  if (nativeType) return { type: nativeType, source: 'native' };

  return undefined;
}

// ─── Container content classification (nesting resolution) ──────────────────

/**
 * Classify the primary control type inside a form-item container.
 * Scans content area, finds all classifications, returns highest-priority one.
 * e.g. el-select (priority 2) wraps el-input (priority 1) → returns 'select'
 */
export function classifyContainerContent(contentArea: Element): ComponentType {
  let bestType: ComponentType = 'input';
  let bestPriority = -1;

  const walk = (el: Element, depth: number) => {
    if (depth > 10) return;
    const cls = classifyElement(el);
    if (cls) {
      const prio = COMPONENT_PRIORITY[cls.type] ?? 0;
      // Only consider control-level types (priority 1-2)
      if (prio >= 1 && prio <= 2 && prio > bestPriority) {
        bestType = cls.type;
        bestPriority = prio;
      }
    }
    for (const child of el.children) walk(child, depth + 1);
  };
  walk(contentArea, 0);

  return bestType;
}

// ─── Exported utilities ─────────────────────────────────────────────────────

export function isFormContainer(el: Element): boolean {
  const cls = classifyElement(el);
  if (cls?.type === 'form-item') return true;
  if (el.tagName.toLowerCase() === 'fieldset') return true;
  return false;
}

export function isNavigationChrome(el: Element): boolean {
  if (el.matches('nav, aside, header, footer')) return true;
  const cls = classifyElement(el);
  if (!cls) return false;
  return cls.type === 'navigation' || cls.type === 'menu' || cls.type === 'layout';
}

/**
 * Check if element is internal to a compound component (select, cascader, etc.).
 * Walks up to 5 ancestor levels.
 */
export function isInsideCompound(el: Element): boolean {
  const role = el.getAttribute('role');
  const ariaHasPopup = el.getAttribute('aria-haspopup');
  if (role === 'combobox' || ariaHasPopup === 'listbox' || ariaHasPopup === 'true') return true;

  let current: Element | null = el.parentElement;
  for (let depth = 0; depth < 5 && current; depth++) {
    const tag = current.tagName.toLowerCase();
    if (tag === 'form' || tag === 'body') break;

    const cls = classifyElement(current);
    if (cls) {
      const prio = COMPONENT_PRIORITY[cls.type] ?? 0;
      if (prio === 2) return true; // Inside a compound control
    }

    // Check for listbox sibling (dropdown popup)
    const parent = current.parentElement;
    if (parent) {
      for (const sibling of parent.children) {
        if (sibling === current) continue;
        if (sibling.getAttribute('role') === 'listbox') return true;
      }
    }

    current = current.parentElement;
  }

  return false;
}

/**
 * Walk up the DOM to find the nearest form-item container.
 * Stops at high-level boundaries (form, body, dialog, table).
 */
export function findFormContainer(element: Element): Element | undefined {
  let el: Element | null = element.parentElement;
  let depth = 0;

  while (el && depth < 10) {
    const tag = el.tagName.toLowerCase();

    // Positive match
    if (isFormContainer(el)) return el;

    // Stop — left the local field scope
    if (
      tag === 'form' || tag === 'body' || tag === 'html' ||
      el.getAttribute('role') === 'dialog' ||
      el.getAttribute('role') === 'main'
    ) {
      break;
    }

    // Stop at table/dialog boundaries (classified)
    const cls = classifyElement(el);
    if (cls && (cls.type === 'table' || cls.type === 'dialog')) break;

    el = el.parentElement;
    depth++;
  }

  return undefined;
}

/**
 * Check if an element is a boundary that should stop ancestor traversal.
 * Tables, dialogs, and main content areas are boundaries.
 */
export function isBoundaryElement(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  if (tag === 'form' || tag === 'body' || tag === 'html') return true;
  if (el.getAttribute('role') === 'dialog' || el.getAttribute('role') === 'main') return true;
  const cls = classifyElement(el);
  if (cls && (cls.type === 'table' || cls.type === 'dialog')) return true;
  return false;
}

/**
 * Get extracted component names from an element — useful for label detection.
 * Returns names like ['form-item', 'label'] for class="el-form-item__label".
 */
export function getComponentNames(el: Element): string[] {
  return extractComponentNames(el);
}

export { COMPONENT_PRIORITY };
