import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { message } from 'ant-design-vue';
import LearningDebugPage from '@/pages/LearningDebugPage.vue';
import ExplorationWorkbenchPage from '@/pages/ExplorationWorkbenchPage.vue';

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
    const wrapper = mount(ExplorationWorkbenchPage);
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
    expect(vm.scoreColor(0.4)).toBe('orange');
    expect(vm.scoreColor(0.1)).toBe('default');
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
    expect(vm.verdictColor('unknown')).toBe('default');

    vm.handleStop();
    expect(message.info).toHaveBeenCalled();

    approveRun.mockRejectedValueOnce(new Error('approve failed'));
    await vm.handleApprove();
    expect(message.error).toHaveBeenCalled();

    rejectRun.mockRejectedValueOnce(new Error('reject failed'));
    await vm.handleReject();
    expect(message.error).toHaveBeenCalled();
  });
});
