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
      { mutationType: 'attributes', astMatch: { confidence: 'ancestor' } },
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
});
