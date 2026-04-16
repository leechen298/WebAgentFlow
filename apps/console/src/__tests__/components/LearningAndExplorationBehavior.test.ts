import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { message } from 'ant-design-vue';
import LearningDebugPage from '@/pages/LearningDebugPage.vue';
import ExplorationWorkbenchPage from '@/pages/ExplorationWorkbenchPage.vue';

const renderStubs = {
  'a-page-header': { props: ['title', 'subTitle'], template: '<div>{{ title }}{{ subTitle }}<slot /></div>' },
  'a-card': { props: ['title'], template: '<section>{{ title }}<slot /></section>' },
  'a-form': { template: '<form><slot /></form>' },
  'a-form-item': { props: ['label'], template: '<div>{{ label }}<slot /></div>' },
  'a-select': { template: '<div><slot /></div>' },
  'a-select-option': { props: ['value'], template: '<div><slot /></div>' },
  'a-input': { props: ['placeholder'], template: '<input />' },
  'a-input-number': { template: '<input />' },
  'a-button': { template: '<button><slot /></button>' },
  'a-alert': { props: ['message', 'description'], template: '<div>{{ message }}{{ description }}<slot name="message" /><slot name="description" /></div>' },
  'a-descriptions': { template: '<div><slot /></div>' },
  'a-descriptions-item': { props: ['label'], template: '<div>{{ label }}<slot /></div>' },
  'a-row': { template: '<div><slot /></div>' },
  'a-col': { template: '<div><slot /></div>' },
  'a-timeline': { template: '<div><slot /></div>' },
  'a-timeline-item': { template: '<div><slot /></div>' },
  'a-tag': { template: '<span><slot /></span>' },
  'a-space': { template: '<div><slot /></div>' },
  'a-collapse': { template: '<div><slot /></div>' },
  'a-collapse-panel': { props: ['header'], template: '<div>{{ header }}<slot /></div>' },
  'a-empty': { props: ['description'], template: '<div>{{ description }}</div>' },
  'a-radio-group': { template: '<div><slot /></div>' },
  'a-radio-button': { template: '<div><slot /></div>' },
};

const {
  inferCandidates,
  upsertFeedback,
  listFeedbackByRecording,
  listTasks,
  runExploration,
  approveRun,
  rejectRun,
} = vi.hoisted(() => ({
  inferCandidates: vi.fn(),
  upsertFeedback: vi.fn(),
  listFeedbackByRecording: vi.fn(),
  listTasks: vi.fn(),
  runExploration: vi.fn(),
  approveRun: vi.fn(),
  rejectRun: vi.fn(),
}));

vi.mock('@/api/learning', () => ({
  inferCandidates,
  upsertFeedback,
  listFeedbackByRecording,
}));

vi.mock('@/api/exploration', () => ({
  listTasks,
  runExploration,
  approveRun,
  rejectRun,
}));

function getSetupState(wrapper: ReturnType<typeof mount>) {
  return (wrapper.vm as any).$?.setupState ?? wrapper.vm;
}

describe('learning and exploration behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    inferCandidates.mockResolvedValue({
      recording_id: 'rec-1',
      candidate_count: 1,
      hint_count: 1,
      written_to_run: 'run-1',
      candidate_elements: [
        {
          element_key: 'button:submit',
          inferred_actions: ['click'],
          score: 0.95,
          priority: 1,
          evidence: { tag: 'button', text_intent: 'submit', icon_intent: ['send'], mutation_linkage: true },
        },
      ],
      interaction_hints: [
        {
          element_key: 'button:submit',
          action: 'click',
          reason: 'Primary CTA',
          expected_effect: 'Submit',
          priority: 1,
        },
      ],
    });
    listFeedbackByRecording.mockResolvedValue([{ element_key: 'button:submit', judgment: 'reasonable' }]);
    upsertFeedback.mockResolvedValue(undefined);

    listTasks.mockResolvedValue([
      {
        id: 'task-1',
        name: 'Search',
        step_count: 2,
        target_url: 'https://example.com',
        variables: { keyword: 'playwright' },
      },
    ]);
    runExploration.mockResolvedValue({
      success: true,
      total_steps: 2,
      elapsed_ms: 2500,
      final_url: 'https://example.com/results',
      final_title: 'Results',
      final_screenshot_ref: 'final-shot',
      summary: 'Completed',
      steps: [
        {
          step_index: 1,
          intent: 'search',
          action_type: 'input',
          value: 'playwright',
          target_summary: 'search box',
          execution_result: { ok: true, screenshot_ref: 'step-shot' },
          observation: { html_changed: true, url: 'https://example.com/results' },
          success_evaluation: { satisfied: true, confidence: 'high', matched_conditions: ['html_changed'], failed_conditions: [] },
        },
      ],
      supervisor: {
        verdict: 'success',
        confidence: 'high',
        summary: 'Looks good',
        anomalies: ['none'],
        suggestions: ['ship it'],
        step_assessments: [{ step_index: 1, status: 'ok', note: 'fine' }],
      },
    });
    approveRun.mockResolvedValue(undefined);
    rejectRun.mockResolvedValue(undefined);
  });

  it('covers LearningDebugPage inference, filtering, and feedback persistence', async () => {
    const wrapper = mount(LearningDebugPage);
    const vm = getSetupState(wrapper);

    vm.recordingId = 'rec-1';
    vm.runId = 'run-1';
    await vm.runInference();

    expect(inferCandidates).toHaveBeenCalledWith({
      recording_id: 'rec-1',
      run_id: 'run-1',
      score_threshold: 0.1,
      max_candidates: 200,
    });
    expect(listFeedbackByRecording).toHaveBeenCalledWith('rec-1', 'run-1');
    expect(vm.filteredCandidates).toHaveLength(1);

    vm.filterAction = 'click';
    expect(vm.filteredCandidates).toHaveLength(1);
    vm.filterSignal = 'mutation_linkage';
    expect(vm.filteredCandidates).toHaveLength(1);

    await vm.markJudgment('button:submit', 'unreasonable');
    expect(upsertFeedback).toHaveBeenCalled();

    expect(vm.actionColor('click')).toBe('blue');
    expect(vm.scoreColor(0.9)).toBe('green');
    expect(vm.availableActions).toEqual(['click']);
    expect(vm.stats.textIntent).toBe(1);
    vm.expandedKey = 'button:submit';
    expect(vm.expandedCandidate?.element_key).toBe('button:submit');
    expect(vm.candidateColumns).toHaveLength(12);
    expect(vm.hintColumns).toHaveLength(5);
  });

  it('covers ExplorationWorkbenchPage load/run/task variable/user verdict flow', async () => {
    const wrapper = mount(ExplorationWorkbenchPage, { global: { stubs: renderStubs } });
    const vm = getSetupState(wrapper);

    await vm.loadTasks();
    expect(listTasks).toHaveBeenCalled();

    vm.handleTaskChange('task-1');
    expect(vm.editableVariables.keyword).toBe('playwright');

    vm.selectedTaskId = 'task-1';
    vm.maxSteps = 3;
    await vm.handleRun();
    expect(runExploration).toHaveBeenCalledWith({
      task_id: 'task-1',
      variables: { keyword: 'playwright' },
      headless: false,
      max_steps: 3,
    });
    expect(vm.stepScreenshots).toHaveLength(2);
    expect(vm.selectedScreenshot).toBe('step-shot');

    vm.verdictNote = 'approved';
    await vm.handleApprove();
    expect(approveRun).toHaveBeenCalledWith('mvp-run', 'approved');

    vm.verdictNote = 'rejected';
    await vm.handleReject();
    expect(rejectRun).toHaveBeenCalledWith('mvp-run', 'rejected');

    vm.handleStop();
    vm.handleRerun();
    expect(runExploration).toHaveBeenCalledTimes(2);

    expect(vm.stepColor({
      execution_result: { ok: true },
      success_evaluation: { satisfied: true, confidence: 'high' },
    })).toBe('green');
    expect(vm.evalColor({ satisfied: false, confidence: 'low' })).toBe('orange');
    expect(vm.verdictColor('partial_success')).toBe('orange');
    expect(vm.variableSummary).toContain('keyword=playwright');
    expect(vm.currentStatusLabel).toBeTruthy();
  });

  it('covers LearningDebugPage empty/error/toggle/revert branches', async () => {
    const wrapper = mount(LearningDebugPage);
    const vm = getSetupState(wrapper);

    await vm.runInference();
    expect(inferCandidates).not.toHaveBeenCalled();

    vm.recordingId = 'rec-2';
    inferCandidates.mockRejectedValueOnce(new Error('infer failed'));
    await vm.runInference();
    expect(vm.error).toBe('infer failed');

    inferCandidates.mockResolvedValueOnce({
      recording_id: 'rec-2',
      candidate_count: 1,
      hint_count: 0,
      written_to_run: null,
      candidate_elements: [
        {
          element_key: 'row:1',
          inferred_actions: ['hover'],
          score: 0.2,
          priority: 2,
          evidence: {},
        },
      ],
      interaction_hints: [],
    });
    listFeedbackByRecording.mockRejectedValueOnce(new Error('ignore'));
    await vm.runInference();
    expect(vm.error).toBeNull();
    expect(vm.filteredCandidates).toHaveLength(1);

    vm.judgments = { 'row:1': 'reasonable' };
    await vm.markJudgment('row:1', 'reasonable');
    expect(vm.judgments['row:1']).toBeUndefined();

    upsertFeedback.mockRejectedValueOnce(new Error('save failed'));
    await vm.markJudgment('row:1', 'unreasonable');
    expect(vm.judgments['row:1']).toBeUndefined();
    expect(vm.savingKeys.size).toBe(0);

    vm.filterSignal = 'component_lib';
    expect(vm.filteredCandidates).toHaveLength(0);
    vm.filterSignal = 'unknown';
    expect(vm.filteredCandidates).toHaveLength(1);
    expect(vm.actionColor('unknown')).toBe('default');
    expect(vm.actionColor('input')).toBe('green');
    expect(vm.actionColor('select')).toBe('purple');
    expect(vm.actionColor('toggle')).toBe('orange');
    expect(vm.actionColor('hover')).toBe('cyan');
    expect(vm.scoreColor(0.4)).toBe('orange');
    expect(vm.scoreColor(0.6)).toBe('blue');
    expect(vm.scoreColor(0.1)).toBe('default');
  });

  it('covers LearningDebugPage feedback preload mapping and judgment counters', async () => {
    listFeedbackByRecording.mockResolvedValueOnce([
      { element_key: 'button:submit', judgment: 'reasonable' },
      { element_key: 'button:other', judgment: 'unreasonable' },
    ]);

    const wrapper = mount(LearningDebugPage);
    const vm = getSetupState(wrapper);

    vm.recordingId = 'rec-1';
    await vm.runInference();

    expect(vm.judgments['button:submit']).toBe('reasonable');
    expect(vm.judgments['button:other']).toBe('unreasonable');
    expect(vm.markedReasonable).toBe(1);
    expect(vm.markedUnreasonable).toBe(1);

    vm.expandedKey = 'missing';
    expect(vm.expandedCandidate).toBeNull();
    vm.expandedKey = 'button:submit';
    expect(vm.expandedCandidate?.element_key).toBe('button:submit');
  });

  it('covers ExplorationWorkbenchPage idle/error/fallback branches', async () => {
    const wrapper = mount(ExplorationWorkbenchPage);
    const vm = getSetupState(wrapper);

    vm.tasks = [];
    expect(vm.variableSummary).toBe('—');
    expect(vm.currentStatusLabel).toBeTruthy();
    expect(vm.selectedScreenshot).toBeNull();

    listTasks.mockRejectedValueOnce(new Error('task load failed'));
    await vm.loadTasks();
    expect(vm.error).toContain('task load failed');

    vm.handleTaskChange('missing-task');
    expect(Object.keys(vm.editableVariables)).toHaveLength(0);

    vm.selectedTaskId = null;
    await vm.handleRun();
    expect(runExploration).toHaveBeenCalledTimes(0);

    vm.result = {
      success: false,
      total_steps: 1,
      elapsed_ms: 1000,
      final_url: '',
      final_title: '',
      final_screenshot_ref: 'final-only',
      summary: 'failed',
      steps: [
        {
          step_index: 1,
          intent: 'click',
          action_type: 'click',
          execution_result: { ok: false, error: 'boom', screenshot_ref: 'exec-shot' },
          observation: {},
          success_evaluation: { satisfied: false, confidence: 'high', matched_conditions: [], failed_conditions: ['x'] },
        },
      ],
      supervisor: null,
    };
    expect(vm.stepScreenshots).toHaveLength(2);
    vm.selectedScreenshotIndex = 99;
    expect(vm.selectedScreenshot).toBeNull();
    expect(vm.stepColor(vm.result.steps[0])).toBe('red');
    expect(vm.evalColor({ satisfied: false, confidence: 'high' })).toBe('red');
    expect(vm.evalColor({ satisfied: true, confidence: 'low' })).toBe('green');
    expect(vm.verdictColor('unknown')).toBe('default');
    expect(vm.verdictColor('failure')).toBe('red');
    expect(vm.currentStatusLabel).toBeTruthy();

    vm.handleStop();
    expect(message.info).toHaveBeenCalled();

    approveRun.mockRejectedValueOnce(new Error('approve failed'));
    await vm.handleApprove();
    expect(message.error).toHaveBeenCalled();

    rejectRun.mockRejectedValueOnce(new Error('reject failed'));
    await vm.handleReject();
    expect(message.error).toHaveBeenCalled();
  });

  it('covers ExplorationWorkbenchPage screenshot preference and empty-result guards', async () => {
    const wrapper = mount(ExplorationWorkbenchPage);
    const vm = getSetupState(wrapper);

    vm.result = null;
    await vm.handleApprove();
    await vm.handleReject();
    expect(approveRun).not.toHaveBeenCalled();
    expect(rejectRun).not.toHaveBeenCalled();

    vm.result = {
      success: true,
      total_steps: 2,
      elapsed_ms: 800,
      final_url: 'https://example.com/done',
      final_title: 'Done',
      final_screenshot_ref: 'final-shot',
      summary: 'done',
      steps: [
        {
          step_index: 1,
          intent: 'type',
          action_type: 'input',
          execution_result: { ok: true, screenshot_ref: 'exec-first' },
          observation: { screenshot_ref: 'obs-first' },
          success_evaluation: { satisfied: true, confidence: 'high', matched_conditions: [], failed_conditions: [] },
        },
        {
          step_index: 2,
          intent: 'submit',
          action_type: 'click',
          execution_result: { ok: true },
          observation: {},
          success_evaluation: { satisfied: false, confidence: 'low', matched_conditions: [], failed_conditions: ['x'] },
        },
      ],
      supervisor: {
        verdict: 'failure',
        confidence: 'low',
        summary: 'bad',
        anomalies: [],
        suggestions: [],
        step_assessments: [],
      },
    };

    expect(vm.stepScreenshots).toEqual([
      { label: 'Step 1', src: 'obs-first' },
      { label: 'Final', src: 'final-shot' },
    ]);
    expect(vm.selectedScreenshot).toBe('obs-first');
    vm.selectedScreenshotIndex = 1;
    expect(vm.selectedScreenshot).toBe('final-shot');
    expect(vm.stepColor(vm.result.steps[1])).toBe('orange');
    expect(vm.currentStatusLabel).toBeTruthy();
  });

  it('covers ExplorationWorkbenchPage selected task, running state, and run failure reset', async () => {
    const wrapper = mount(ExplorationWorkbenchPage);
    const vm = getSetupState(wrapper);

    await vm.loadTasks();
    vm.selectedTaskId = 'task-1';
    vm.handleTaskChange('task-1');
    expect(vm.selectedTask?.name).toBe('Search');
    expect(vm.variableSummary).toContain('keyword=playwright');

    vm.running = true;
    expect(vm.currentStatusLabel).toBeTruthy();
    vm.running = false;
    vm.result = { success: true, total_steps: 0, elapsed_ms: 0, final_url: '', final_title: '', final_screenshot_ref: null, summary: '', steps: [], supervisor: null };
    expect(vm.currentStatusLabel).toBeTruthy();

    vm.selectedScreenshotIndex = 7;
    vm.result = { success: true, total_steps: 1, elapsed_ms: 1, final_url: '', final_title: '', final_screenshot_ref: null, summary: '', steps: [], supervisor: null };
    runExploration.mockRejectedValueOnce(new Error('run failed'));
    await vm.handleRun();
    expect(vm.error).toBe('Error: run failed');
    expect(vm.selectedScreenshotIndex).toBe(0);
    expect(vm.running).toBe(false);
  });

  it('covers ExplorationWorkbenchPage variable reset and final-only screenshot fallback', async () => {
    const wrapper = mount(ExplorationWorkbenchPage);
    const vm = getSetupState(wrapper);

    await vm.loadTasks();
    vm.editableVariables.old = 'stale';
    vm.handleTaskChange('task-1');
    expect(vm.editableVariables.old).toBeUndefined();
    expect(vm.tasksLoading).toBe(false);

    vm.result = {
      success: true,
      total_steps: 1,
      elapsed_ms: 50,
      final_url: '',
      final_title: '',
      final_screenshot_ref: 'final-only',
      summary: '',
      steps: [
        {
          step_index: 1,
          intent: 'noop',
          action_type: 'click',
          execution_result: { ok: true },
          observation: {},
          success_evaluation: { satisfied: true, confidence: 'high', matched_conditions: [], failed_conditions: [] },
        },
      ],
      supervisor: {
        verdict: 'success',
        confidence: 'high',
        summary: '',
        anomalies: ['warning'],
        suggestions: ['retry'],
        step_assessments: [{ step_index: 1, status: 'failed', note: 'bad' }, { step_index: 2, status: 'partial', note: 'half' }],
      },
    };
    expect(vm.stepScreenshots).toEqual([{ label: 'Final', src: 'final-only' }]);
    expect(vm.selectedScreenshot).toBe('final-only');
    expect(vm.verdictColor(vm.result.supervisor.verdict)).toBe('green');
  });

  it('renders exploration template branches for running, details, and supervisor content', async () => {
    const wrapper = mount(ExplorationWorkbenchPage, { global: { stubs: renderStubs } });
    const vm = getSetupState(wrapper);

    vm.tasks = [{ id: 'task-1', name: 'Search', step_count: 2, target_url: 'https://example.com', variables: { keyword: 'playwright' } }];
    vm.selectedTaskId = 'task-1';
    vm.editableVariables.keyword = 'playwright';
    vm.running = true;
    await nextTick();
    expect(wrapper.text()).toContain('Search');

    vm.running = false;
    vm.result = {
      success: false,
      total_steps: 1,
      elapsed_ms: 250,
      final_url: 'https://example.com/fail',
      final_title: '',
      final_screenshot_ref: null,
      summary: 'summary',
      steps: [
        {
          step_index: 1,
          intent: 'submit',
          action_type: 'click',
          value: 'go',
          target_summary: 'submit button',
          execution_result: { ok: false, error: 'boom' },
          observation: { url_changed: true, title_changed: true, html_changed: true, url: 'https://example.com/changed' },
          success_evaluation: {
            satisfied: false,
            confidence: 'low',
            matched_conditions: ['html_changed'],
            failed_conditions: ['no_error'],
            uncertain_reason: 'race condition',
          },
          agent_note: 'watch this',
        },
      ],
      supervisor: {
        verdict: 'failure',
        confidence: 'low',
        summary: 'bad result',
        anomalies: ['missing banner'],
        suggestions: ['retry with wait'],
        step_assessments: [{ step_index: 1, status: 'partial', note: 'almost' }],
      },
    };
    await nextTick();

    expect(wrapper.text()).toContain('submit button');
    expect(wrapper.text()).toContain('URL changed');
    expect(wrapper.text()).toContain('Title changed');
    expect(wrapper.text()).toContain('HTML changed');
    expect(wrapper.text()).toContain('race condition');
    expect(wrapper.text()).toContain('watch this');
    expect(wrapper.text()).toContain('missing banner');
    expect(wrapper.text()).toContain('retry with wait');
    expect(wrapper.text()).toContain('Step 1: partial');
  });
});
