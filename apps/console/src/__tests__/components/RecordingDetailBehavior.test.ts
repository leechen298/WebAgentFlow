import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { message } from 'ant-design-vue';
import RecordingDetailPage from '@/pages/RecordingDetailPage.vue';

const push = vi.fn();
const {
  getNormalizedRecording,
  getRecordingSteps,
  parseHtmlToAST,
  simplifyHtmlToAST,
} = vi.hoisted(() => ({
  getNormalizedRecording: vi.fn(),
  getRecordingSteps: vi.fn(),
  parseHtmlToAST: vi.fn(),
  simplifyHtmlToAST: vi.fn(),
}));

const recording = {
  id: 'rec-1',
  name: 'Recording 1',
  status: 'draft',
  source: 'extension',
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
  events: [
    { id: 'e0', type: 'navigate', timestamp: 1000, url: 'https://example.com' },
    {
      id: 'e1',
      type: 'click',
      timestamp: 2500,
      url: 'https://example.com',
      astMatch: { confidence: 'exact', nodeId: 'n1', nodePath: '0-0' },
    },
  ],
  meta: {
    initialState: {
      pageUrl: 'https://example.com',
      pageTitle: 'Example',
      capturedAt: 1000,
      rawHtmlSnapshot: '<div>Hello</div>',
      stateTree: [
        {
          type: 'section',
          label: 'Main',
          blockType: 'form-section',
          children: [
            { type: 'button', label: 'Submit', localHtml: '<button>Submit</button>' },
            { type: 'table', headers: ['Name'], rows: [['Alice']] },
            { type: 'custom', label: 'List', value: '共2项：Alpha；Beta' },
          ],
        },
      ],
      fields: [
        {
          fieldLabel: 'Name',
          fieldPath: 'Main / Name',
          fieldType: 'table',
          itemCount: 1,
          defaultValueText: '共1行：Name:Alice',
        },
      ],
    },
    domMutations: [
      { mutationType: 'attributes', astMatch: { confidence: 'ancestor' }, detail: { type: 'attributes', attributeName: 'class', oldValue: 'a', newValue: 'b' } },
    ],
  },
};

const recordingsStore = {
  currentRecording: recording,
  loading: false,
  error: null,
  fetchRecording: vi.fn().mockResolvedValue(undefined),
  updateRecording: vi.fn().mockResolvedValue(recording),
  deleteRecording: vi.fn().mockResolvedValue(undefined),
  clearCurrent: vi.fn(),
};

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ params: { id: 'rec-1' } }),
}));

vi.mock('@/stores', () => ({
  useRecordingsStore: () => recordingsStore,
}));

vi.mock('@/api/recordings', () => ({
  getNormalizedRecording,
  getRecordingSteps,
}));

vi.mock('@/api/ast', () => ({
  parseHtmlToAST,
  simplifyHtmlToAST,
}));

function getSetupState(wrapper: ReturnType<typeof mount>) {
  return (wrapper.vm as any).$?.setupState ?? wrapper.vm;
}

describe('RecordingDetailPage behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    recordingsStore.currentRecording = recording;
    getNormalizedRecording.mockResolvedValue({ summary: 'normalized' });
    getRecordingSteps.mockResolvedValue({ steps: [{ timestamp: 1000 }, { timestamp: 2500 }] });
    parseHtmlToAST.mockResolvedValue({ nodes: [{ node_type: 'element', tag: 'div', attrs: { class: 'a b c' }, children: [] }] });
    simplifyHtmlToAST.mockResolvedValue({ nodes: [{ node_type: 'text', text: 'Hello', children: [] }] });
  });

  it('covers tree helpers, formatters, AST loaders, and CRUD behavior', async () => {
    const wrapper = mount(RecordingDetailPage);
    const vm = getSetupState(wrapper);
    vm.formRef = { validate: vi.fn().mockResolvedValue(undefined) };

    expect(vm.stateTreeNodeCount).toBeGreaterThan(0);
    expect(vm.mutationTypeCounts.attributes).toBe(1);
    expect(vm.mutationAstCounts.ancestor).toBe(1);

    expect(vm.flattenTree(recording.meta.initialState.stateTree)).toHaveLength(4);
    expect(vm.countNodes(recording.meta.initialState.stateTree)).toBe(4);
    vm.toggleNode('0');
    vm.expandAllNodes();
    vm.collapseAllNodes();
    vm.toggleDetail('0');
    expect(vm.getNodeLocalHtml(recording.meta.initialState.stateTree[0].children[0])).toContain('Submit');
    expect(vm.getInlineTableColumns(recording.meta.initialState.stateTree[0].children[1])[0].title).toBe('Name');
    expect(vm.stringifyTableCell({ text: 'Alice' })).toBe('Alice');
    expect(vm.getInlineTableRows(recording.meta.initialState.stateTree[0].children[1])[0].col0).toBe('Alice');
    expect(vm.getInlineListItems(recording.meta.initialState.stateTree[0].children[2])).toEqual(['Alpha', 'Beta']);
    expect(vm.collectLeafHtml(recording.meta.initialState.stateTree)).toHaveLength(1);

    vm.openFieldDetailModal(recording.meta.initialState.fields[0]);
    expect(vm.fieldDetailModalOpen).toBe(true);
    expect(vm.parsedTableRows).toHaveLength(1);
    expect(vm.parsedTableColumns[0].title).toBe('Name');
    vm.showNodeJson('0');
    expect(vm.nodeHasLocalHtml(recording.meta.initialState.stateTree[0].children[0])).toBe(true);
    expect(vm.blockTypeColor('form-section')).toBe('green');
    expect(vm.initialFieldTypeColor('table')).toBe('volcano');
    expect(vm.eventTypeColor('click')).toBe('orange');
    expect(vm.astConfidenceColor('ancestor')).toBe('blue');
    expect(vm.formatRelativeTime(2500)).toBe('1.5s');
    expect(vm.segmentHeaderStyle('navigation')).toEqual({ background: '#e6f4ff' });
    expect(vm.compactClass('a b c')).toBe('a.b+1');
    expect(vm.astKeyAttrs({ href: '/x', class: 'a' })).toEqual([{ name: 'href', value: '/x' }]);

    await vm.loadNormalized();
    await vm.loadFullAST();
    await vm.loadSimplifiedAST();
    await vm.loadSteps();
    expect(getNormalizedRecording).toHaveBeenCalledWith('rec-1');
    expect(parseHtmlToAST).toHaveBeenCalled();
    expect(simplifyHtmlToAST).toHaveBeenCalled();
    expect(getRecordingSteps).toHaveBeenCalledWith('rec-1');
    expect(vm.astTreeData).toHaveLength(1);
    expect(vm.simpTreeData).toHaveLength(1);
    vm.expandAstToDepth(2);
    vm.expandSimpToDepth(2);
    expect(vm.formatStepRelativeTime(2500)).toBe('1.5s');
    vm.handleTabChange('normalized');
    vm.handleTabChange('full-ast');
    vm.handleTabChange('simplified-ast');
    vm.handleTabChange('steps');

    vm.showEditModal();
    expect(vm.editModalOpen).toBe(true);
    vm.formData.eventsStr = '{';
    expect(vm.validateJson('events')).toBe(false);
    vm.formData.eventsStr = '[]';
    vm.formData.metaStr = '{}';
    await vm.handleSave();
    expect(recordingsStore.updateRecording).toHaveBeenCalledWith('rec-1', expect.objectContaining({ name: 'Recording 1' }));
    await vm.handleDelete();
    expect(recordingsStore.deleteRecording).toHaveBeenCalledWith('rec-1');
    expect(push).toHaveBeenCalledWith('/recordings');
    vm.goBack();
    expect(push).toHaveBeenCalledWith('/recordings');
  });

  it('covers fallback/error branches for loaders, helpers, and save/delete flows', async () => {
    const wrapper = mount(RecordingDetailPage);
    const vm = getSetupState(wrapper);

    expect(vm.mutationTypeColor('childList')).toBe('green');
    expect(vm.mutationTypeColor('characterData')).toBe('orange');
    expect(vm.mutationTypeColor('weird')).toBe('default');
    expect(vm.getStatusColor('active')).toBe('green');
    expect(vm.getStatusColor('unknown')).toBe('default');
    expect(vm.actionColor('unknown')).toBe('default');
    expect(vm.eventTypeColor('weird')).toBe('default');
    expect(vm.astConfidenceColor('mystery')).toBe('default');
    expect(vm.formatRelativeTime(1000)).toBe('0ms');
    expect(vm.formatStepRelativeTime(1000)).toBe('0s');
    expect(vm.segmentHeaderStyle('unknown')).toEqual({ background: '#fafafa' });
    expect(vm.truncate('abcdef', 3)).toBe('abc…');
    expect(typeof vm.formatDate('2026-04-16T00:00:00Z')).toBe('string');
    expect(vm.astKeyAttrs()).toEqual([]);
    expect(vm.compactClass('one two')).toBe('one.two');
    expect(vm.getInlineTableColumns({ type: 'table', rows: [['x']] })[0].title).toBe('Col 1');
    expect(vm.getInlineTableRows({ type: 'table' })).toEqual([]);
    expect(vm.getInlineListItems({ type: 'list' })).toEqual([]);
    expect(vm.getNodeLocalHtml({ type: 'custom', htmlContent: '<div>x</div>' } as any)).toContain('x');
    expect(vm.nodeHasLocalHtml({ type: 'custom', htmlContent: '<div>x</div>' } as any)).toBe(true);
    expect(vm.collectLeafHtml([{ type: 'custom', label: 'x', htmlContent: '<div>x</div>' } as any])).toHaveLength(1);
    expect(vm.convertASTToTreeData([{ node_type: 'text', text: 'Hello', children: [] }])[0].isLeaf).toBe(true);
    expect(vm.collectKeysToDepth([{ key: '0', children: [{ key: '0-0', children: [] }] }], 1)).toEqual(['0']);
    expect(vm.parsedListItems).toEqual([]);
    expect(vm.fieldDetailTitle).toBe('');

    vm.normalized = null;
    getNormalizedRecording.mockRejectedValueOnce(new Error('normalized failed'));
    await vm.loadNormalized();
    expect(vm.normError).toBe('normalized failed');

    vm.astResult = null;
    parseHtmlToAST.mockRejectedValueOnce(new Error('ast failed'));
    await vm.loadFullAST();
    expect(vm.astError).toBe('ast failed');

    vm.simpResult = null;
    simplifyHtmlToAST.mockRejectedValueOnce(new Error('simp failed'));
    await vm.loadSimplifiedAST();
    expect(vm.simpError).toBe('simp failed');

    vm.stepsResult = null;
    getRecordingSteps.mockRejectedValueOnce(new Error('steps failed'));
    await vm.loadSteps();
    expect(vm.stepsError).toBe('steps failed');

    recordingsStore.fetchRecording.mockRejectedValueOnce(new Error('fetch failed'));
    await vm.fetchRecording();
    expect(message.error).toHaveBeenCalled();

    vm.formRef = { validate: vi.fn().mockRejectedValue(new Error('invalid form')) };
    await vm.handleSave();
    expect(message.error).toHaveBeenCalled();

    recordingsStore.deleteRecording.mockRejectedValueOnce(new Error('delete failed'));
    await vm.handleDelete();
    expect(message.error).toHaveBeenCalled();
  });

  it('covers legacy snapshot, collapsed tree visibility, modal titles, and unmount cleanup', async () => {
    recordingsStore.currentRecording = {
      ...recording,
      events: [
        { id: 'e0', type: 'navigate', timestamp: 1000, url: 'https://example.com' },
        {
          id: 'e1',
          type: 'click',
          timestamp: 2500,
          astMatch: { confidence: 'none', areaLabel: 'main', ancestorChain: 'body > main' },
        },
      ],
      meta: {
        initialState: {
          pageUrl: 'https://legacy.example.com',
          pageTitle: 'Legacy',
          capturedAt: 1000,
          htmlSnapshot: '<main>legacy</main>',
          stateTree: [
            {
              type: 'section',
              label: 'Outer',
              children: [
                {
                  type: 'group',
                  label: 'Inner',
                  children: [{ type: 'input', label: 'Name', value: 'Alice' }],
                },
              ],
            },
          ],
          fields: [
            {
              fieldLabel: 'Items',
              fieldType: 'list',
              itemCount: 2,
              defaultValueText: '共2项：Alpha；Beta',
            },
          ],
        },
      },
    } as any;

    const wrapper = mount(RecordingDetailPage);
    const vm = getSetupState(wrapper);

    expect(vm.rawHtmlSnapshotData).toBe('<main>legacy</main>');
    expect(vm.astMatchCount.none).toBe(1);
    expect(vm.fieldDetailTitle).toBe('');

    vm.openFieldDetailModal(recordingsStore.currentRecording.meta.initialState.fields[0]);
    expect(vm.parsedListItems).toEqual(['Alpha', 'Beta']);
    expect(vm.fieldDetailTitle).toBe('Items（2 项）');

    expect(vm.visibleTreeRows.map((row: any) => row.key)).toEqual(['0', '0-0', '0-0-0']);
    vm.toggleNode('0');
    expect(vm.visibleTreeRows.map((row: any) => row.key)).toEqual(['0']);
    vm.toggleNode('0');
    vm.toggleNode('0-0');
    expect(vm.visibleTreeRows.map((row: any) => row.key)).toEqual(['0', '0-0']);

    wrapper.unmount();
    expect(recordingsStore.clearCurrent).toHaveBeenCalled();

    recordingsStore.currentRecording = recording;
  });

  it('covers empty-json validation and save early return when json is invalid', async () => {
    const wrapper = mount(RecordingDetailPage);
    const vm = getSetupState(wrapper);

    expect(vm.validateJson('events')).toBe(true);
    expect(vm.formErrors.events).toBe('');

    vm.formRef = { validate: vi.fn().mockResolvedValue(undefined) };
    vm.showEditModal();
    vm.formData.eventsStr = '[';
    vm.formData.metaStr = '{}';
    await vm.handleSave();
    expect(recordingsStore.updateRecording).not.toHaveBeenCalled();
    expect(vm.formErrors.events).toBeTruthy();
  });

  it('covers dense helper branches for cell formatting, colors, and minute-based timing', async () => {
    const wrapper = mount(RecordingDetailPage);
    const vm = getSetupState(wrapper);

    expect(vm.stringifyTableCell({ value: 'V' })).toBe('V');
    expect(vm.stringifyTableCell({ src: 'https://example.com/a.png' })).toBe('https://example.com/a.png');
    expect(vm.stringifyTableCell({ actions: [{ label: 'Edit' }, { label: 'Delete' }] })).toBe('Edit | Delete');
    expect(vm.stringifyTableCell({ children: [{ label: 'Alpha' }, { value: 'Beta' }] })).toBe('Alpha Beta');
    expect(vm.stringifyTableCell({ type: 'upload' })).toBe('[upload]');
    expect(vm.stringifyTableCell(1)).toBe('');

    expect(vm.initialFieldTypeColor('upload')).toBe('magenta');
    expect(vm.initialFieldTypeColor('color')).toBe('magenta');
    expect(vm.initialFieldTypeColor('switch')).toBe('blue');
    expect(vm.initialFieldTypeColor('mystery')).toBe('default');
    expect(vm.actionColor('navigate-page')).toBe('geekblue');
    expect(vm.actionColor('fill-field')).toBe('green');
    expect(vm.actionColor('select-field')).toBe('lime');
    expect(vm.actionColor('edit-richtext')).toBe('purple');
    expect(vm.actionColor('click-button')).toBe('orange');
    expect(vm.actionColor('open-dialog')).toBe('gold');
    expect(vm.actionColor('confirm-dialog')).toBe('cyan');
    expect(vm.actionColor('cancel-dialog')).toBe('red');

    vm.stepsResult = { steps: [{ timestamp: 1000 }, { timestamp: 62000 }] };
    expect(vm.formatStepRelativeTime(62000)).toBe('1m1s');

    recordingsStore.currentRecording = {
      ...recording,
      events: [
        { id: 'e0', type: 'navigate', timestamp: 1000, url: 'https://example.com' },
        { id: 'e1', type: 'change', timestamp: 62000 },
      ],
    } as any;
    expect(vm.formatRelativeTime(62000)).toBe('1m1s');
    recordingsStore.currentRecording = recording;
  });

  it('renders template branches: descriptions, timeline, target, AST match, field context, mutations', async () => {
    const stubs = {
      'a-page-header': { template: '<div><slot name="extra" /><slot /></div>' },
      'a-spin': { template: '<div><slot /></div>' },
      'a-card': { template: '<div><slot /></div>' },
      'a-descriptions': { template: '<div><slot /></div>' },
      'a-descriptions-item': { props: ['label', 'span'], template: '<div>{{ label }}<slot /></div>' },
      'a-tabs': { template: '<div><slot /></div>' },
      'a-tab-pane': { props: ['tab'], template: '<div><slot /></div>' },
      'a-tag': { template: '<span><slot /></span>' },
      'a-space': { template: '<div><slot /></div>' },
      'a-button': { template: '<button><slot /><slot name="icon" /></button>' },
      'a-popconfirm': { template: '<div><slot /></div>' },
      'a-textarea': { props: ['value', 'rows', 'readonly'], template: '<textarea>{{ value }}</textarea>' },
      'a-alert': { props: ['message', 'description'], template: '<div>{{ message }}</div>' },
      'a-modal': { props: ['open', 'title'], template: '<div v-if="open"><slot /></div>' },
      'a-form': { template: '<form><slot /></form>' },
      'a-form-item': { props: ['label'], template: '<div><slot /></div>' },
      'a-input': { template: '<input />' },
      'a-input-number': { template: '<input />' },
      'a-select': { template: '<select><slot /></select>' },
      'a-select-option': { template: '<option><slot /></option>' },
      'a-collapse': { template: '<div><slot /></div>' },
      'a-collapse-panel': { props: ['header'], template: '<div>{{ header }}<slot /></div>' },
      'a-empty': { props: ['description'], template: '<div>{{ description }}</div>' },
      'a-statistic': { props: ['title', 'value'], template: '<div>{{ title }}={{ value }}</div>' },
      'a-row': { template: '<div><slot /></div>' },
      'a-col': { template: '<div><slot /></div>' },
      'a-table': { props: ['columns', 'dataSource'], template: '<div><slot /></div>' },
      'a-radio-group': { template: '<div><slot /></div>' },
      'a-radio-button': { template: '<div><slot /></div>' },
      'edit-outlined': { template: '<i />' },
      'delete-outlined': { template: '<i />' },
    };

    // Rich recording with many template branches
    recordingsStore.currentRecording = {
      ...recording,
      events: [
        { id: 'e0', type: 'navigate', timestamp: 1000, url: 'https://example.com', title: 'Example Page' },
        {
          id: 'e1', type: 'click', timestamp: 2500, url: 'https://example.com',
          target: { tag: 'button', text: 'Submit', id: 'btn-submit', role: 'button', label: 'Submit Form' },
          value: 'clicked',
          fieldContext: { fieldLabel: 'Actions', fieldPath: 'Form > Actions', containerType: 'form-item', fieldRequired: true, fieldProp: 'action' },
          astMatch: { confidence: 'exact', nodeId: 'n1', nodePath: '0-1', nodeType: 'button', nodeLabel: 'Submit', areaLabel: 'main' },
          frameInfo: { isIframe: true },
        },
        {
          id: 'e2', type: 'input', timestamp: 3000, url: 'https://example.com',
          target: { tag: 'input' },
          astMatch: { confidence: 'none', areaLabel: 'footer', ancestorChain: 'body > footer' },
        },
      ],
      meta: {
        ...recording.meta,
        capturedHtml: '<html><body><div>Hello</div></body></html>',
        domMutations: [
          {
            mutationType: 'childList',
            target: { tag: 'div', selector: '.container' },
            detail: { type: 'childList', addedCount: 1, removedCount: 0, addedNodes: [{ tag: 'span', text: 'new' }], removedNodes: [] },
            astMatch: { confidence: 'exact', nodeId: 'n2' },
          },
          {
            mutationType: 'characterData',
            target: { tag: 'span' },
            detail: { type: 'characterData', oldValue: 'old', newValue: 'new' },
            astMatch: { confidence: 'none' },
          },
        ],
      },
    } as any;

    const wrapper = mount(RecordingDetailPage, { global: { stubs } });
    const vm = getSetupState(wrapper);

    // Force all tab data to be populated
    vm.activeTab = 'timeline';
    await new Promise(r => setTimeout(r, 0));

    // Template should render timeline events, targets, AST matches, field context, mutations
    const text = wrapper.text();
    expect(text).toContain('rec-1');
    expect(text).toContain('navigate');
    expect(text).toContain('click');
    expect(text).toContain('https://example.com');

    // Switch tabs to exercise different template branches
    vm.activeTab = 'raw';
    await new Promise(r => setTimeout(r, 0));
    vm.activeTab = 'initial-state';
    await new Promise(r => setTimeout(r, 0));
    vm.activeTab = 'dom-mutations';
    await new Promise(r => setTimeout(r, 0));

    recordingsStore.currentRecording = recording;
  });

  it('renders template branches: normalized, steps, AST tree, simplified AST views', async () => {
    const stubs = {
      'a-page-header': { template: '<div><slot /></div>' },
      'a-spin': { template: '<div><slot /></div>' },
      'a-card': { template: '<div><slot /></div>' },
      'a-descriptions': { template: '<div><slot /></div>' },
      'a-descriptions-item': { props: ['label'], template: '<div><slot /></div>' },
      'a-tabs': { template: '<div><slot /></div>' },
      'a-tab-pane': { props: ['tab'], template: '<div><slot /></div>' },
      'a-tag': { template: '<span><slot /></span>' },
      'a-space': { template: '<div><slot /></div>' },
      'a-button': { template: '<button><slot /></button>' },
      'a-popconfirm': { template: '<div><slot /></div>' },
      'a-textarea': { props: ['value'], template: '<textarea>{{ value }}</textarea>' },
      'a-alert': { template: '<div />' },
      'a-modal': { props: ['open'], template: '<div v-if="open"><slot /></div>' },
      'a-form': { template: '<form><slot /></form>' },
      'a-form-item': { template: '<div><slot /></div>' },
      'a-input': { template: '<input />' },
      'a-input-number': { template: '<input />' },
      'a-select': { template: '<select><slot /></select>' },
      'a-select-option': { template: '<option><slot /></option>' },
      'a-collapse': { template: '<div><slot /></div>' },
      'a-collapse-panel': { template: '<div><slot /></div>' },
      'a-empty': { template: '<div />' },
      'a-statistic': { props: ['title', 'value'], template: '<div>{{ title }}</div>' },
      'a-row': { template: '<div><slot /></div>' },
      'a-col': { template: '<div><slot /></div>' },
      'a-table': { props: ['columns', 'dataSource'], template: '<div />' },
      'a-radio-group': { template: '<div><slot /></div>' },
      'a-radio-button': { template: '<div><slot /></div>' },
      'a-tree': { props: ['treeData', 'expandedKeys'], template: '<div />' },
      'edit-outlined': { template: '<i />' },
      'delete-outlined': { template: '<i />' },
    };

    const wrapper = mount(RecordingDetailPage, { global: { stubs } });
    const vm = getSetupState(wrapper);

    // Populate normalized data
    vm.normalized = {
      summary: { event_count_raw: 2, event_count_normalized: 2, contains_iframe: false, contains_richtext: false },
      segments: [{ type: 'navigation', events: [{ type: 'navigate' }] }],
      key_actions: [{ type: 'click', timestamp: 2500, target: 'button' }],
    };
    vm.activeTab = 'normalized';
    await new Promise(r => setTimeout(r, 0));

    // Populate steps data
    vm.stepsResult = {
      steps: [
        {
          timestamp: 2500,
          event_type: 'click',
          event_target_summary: 'button',
          action: 'click-button',
          server_ast_match: { confidence: 'exact', tag: 'button', label: 'Submit' },
          step_descriptions: ['Clicked submit button'],
          no_change_reason: null,
        },
      ],
    };
    vm.activeTab = 'steps';
    await new Promise(r => setTimeout(r, 0));

    // Populate AST data
    vm.astResult = {
      nodes: [
        {
          node_type: 'element',
          tag: 'div',
          attrs: { class: 'container main-panel' },
          children: [
            { node_type: 'element', tag: 'button', attrs: { id: 'submit' }, children: [], text_content: 'Submit' },
            { node_type: 'text', text: 'Hello world', children: [] },
          ],
        },
      ],
    };
    vm.activeTab = 'full-ast';
    await new Promise(r => setTimeout(r, 0));

    vm.simpResult = {
      nodes: [
        { node_type: 'element', tag: 'div', attrs: {}, children: [{ node_type: 'text', text: 'Simple', children: [] }] },
      ],
    };
    vm.activeTab = 'simplified-ast';
    await new Promise(r => setTimeout(r, 0));

    // Open edit modal to cover modal template
    vm.showEditModal();
    await new Promise(r => setTimeout(r, 0));

    // Open field detail modal
    vm.openFieldDetailModal(recording.meta.initialState.fields[0]);
    await new Promise(r => setTimeout(r, 0));

    recordingsStore.currentRecording = recording;
  });

});
