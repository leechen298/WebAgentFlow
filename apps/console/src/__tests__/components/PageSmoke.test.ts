import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import HomePage from '@/pages/HomePage.vue';
import RecordingsPage from '@/pages/RecordingsPage.vue';
import RecordingDetailPage from '@/pages/RecordingDetailPage.vue';
import SkillsPage from '@/pages/SkillsPage.vue';
import SkillDetailPage from '@/pages/SkillDetailPage.vue';
import RunsPage from '@/pages/RunsPage.vue';
import RunDetailPage from '@/pages/RunDetailPage.vue';
import LearningDebugPage from '@/pages/LearningDebugPage.vue';
import ExplorationWorkbenchPage from '@/pages/ExplorationWorkbenchPage.vue';

const push = vi.fn();
const back = vi.fn();

const sampleRecording = {
  id: 'rec-1',
  name: 'Recording 1',
  status: 'completed',
  source: 'extension',
  events: [{ id: 'e0', type: 'click', timestamp: Date.now(), url: 'https://example.com' }],
  meta: {
    initialState: {
      pageUrl: 'https://example.com',
      pageTitle: 'Example',
      capturedAt: Date.now(),
      stateTree: [{ type: 'section', label: 'Main', children: [{ type: 'button', label: 'Submit' }] }],
    },
    domMutations: [],
  },
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
};

const sampleSkill = {
  id: 'skill-1',
  name: 'Skill 1',
  version: '1.0.0',
  status: 'published',
  recording_id: 'rec-1',
  description: 'A test skill',
  definition: { steps: [] },
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
};

const sampleRun = {
  id: 'run-1',
  skill_id: 'skill-1',
  status: 'succeeded',
  started_at: '2026-04-16T00:00:00Z',
  finished_at: '2026-04-16T00:01:00Z',
  input_payload: { foo: 'bar' },
  result_payload: { ok: true },
  logs: ['done'],
  created_at: '2026-04-16T00:00:00Z',
};

const recordingsStore = {
  recordings: [sampleRecording],
  currentRecording: sampleRecording,
  loadingList: false,
  loading: false,
  error: null,
  hasPrev: false,
  hasNext: true,
  fetchFirstPage: vi.fn().mockResolvedValue(undefined),
  fetchNextPage: vi.fn().mockResolvedValue(undefined),
  fetchPrevPage: vi.fn().mockResolvedValue(undefined),
  fetchRecording: vi.fn().mockResolvedValue(undefined),
  createRecording: vi.fn().mockResolvedValue(sampleRecording),
  updateRecording: vi.fn().mockResolvedValue(sampleRecording),
  deleteRecording: vi.fn().mockResolvedValue(undefined),
  clearCurrentRecording: vi.fn(),
};

const skillsStore = {
  skills: [sampleSkill],
  currentSkill: sampleSkill,
  loadingList: false,
  loading: false,
  error: null,
  hasPrev: false,
  hasNext: true,
  fetchFirstPage: vi.fn().mockResolvedValue(undefined),
  fetchNextPage: vi.fn().mockResolvedValue(undefined),
  fetchPrevPage: vi.fn().mockResolvedValue(undefined),
  fetchSkill: vi.fn().mockResolvedValue(undefined),
  createSkill: vi.fn().mockResolvedValue(sampleSkill),
  updateSkill: vi.fn().mockResolvedValue(sampleSkill),
  deleteSkill: vi.fn().mockResolvedValue(undefined),
  clearCurrentSkill: vi.fn(),
};

const runsStore = {
  runs: [sampleRun],
  currentRun: sampleRun,
  loadingList: false,
  loading: false,
  error: null,
  hasPrev: false,
  hasNext: true,
  fetchFirstPage: vi.fn().mockResolvedValue(undefined),
  fetchNextPage: vi.fn().mockResolvedValue(undefined),
  fetchPrevPage: vi.fn().mockResolvedValue(undefined),
  fetchRun: vi.fn().mockResolvedValue(undefined),
  createRun: vi.fn().mockResolvedValue(sampleRun),
  updateRun: vi.fn().mockResolvedValue(sampleRun),
  deleteRun: vi.fn().mockResolvedValue(undefined),
  clearCurrentRun: vi.fn(),
};

vi.mock('vue-router', () => ({
  useRouter: () => ({ push, back }),
  useRoute: () => ({ params: { id: 'rec-1' } }),
}));

vi.mock('@/stores', () => ({
  useAppStore: () => ({
    apiConnected: true,
    loading: false,
    checkApiHealth: vi.fn().mockResolvedValue(undefined),
  }),
  useRecordingsStore: () => recordingsStore,
  useSkillsStore: () => skillsStore,
  useRunsStore: () => runsStore,
}));

vi.mock('@/api/recordings', () => ({
  getNormalizedRecording: vi.fn().mockResolvedValue({}),
  getRecordingSteps: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/api/ast', () => ({
  parseHtmlToAST: vi.fn().mockResolvedValue({}),
  simplifyHtmlToAST: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/api/learning', () => ({
  inferCandidates: vi.fn().mockResolvedValue({
    candidate_count: 1,
    hint_count: 1,
    written_to_run: 'run-1',
    candidate_elements: [
      {
        priority: 1,
        element_key: 'button:submit',
        inferred_actions: ['click'],
        score: 0.92,
        evidence: { tag: 'button', text_intent: 'submit', icon_intent: ['send'] },
      },
    ],
    interaction_hints: [
      {
        priority: 1,
        element_key: 'button:submit',
        action: 'click',
        reason: 'Primary CTA',
        expected_effect: 'Submit form',
      },
    ],
  }),
  upsertFeedback: vi.fn().mockResolvedValue(undefined),
  listFeedbackByRecording: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/api/exploration', () => ({
  listTasks: vi.fn().mockResolvedValue([
    {
      id: 'task-1',
      name: 'Example Task',
      step_count: 2,
      target_url: 'https://example.com',
      variables: { keyword: 'playwright' },
    },
  ]),
  runExploration: vi.fn().mockResolvedValue({
    success: true,
    total_steps: 2,
    elapsed_ms: 3210,
    final_url: 'https://example.com/result',
    final_title: 'Result',
    final_screenshot_ref: 'data:image/png;base64,AAA',
    summary: 'All good',
    steps: [
      {
        step_index: 1,
        intent: 'search',
        action_type: 'input',
        value: 'playwright',
        target_summary: 'search input',
        execution_result: { ok: true, screenshot_ref: 'data:image/png;base64,BBB' },
        observation: { url_changed: false, title_changed: false, html_changed: true, url: 'https://example.com' },
        success_evaluation: { satisfied: true, confidence: 'high', matched_conditions: ['html_changed'], failed_conditions: [] },
      },
    ],
    supervisor: {
      verdict: 'success',
      confidence: 'high',
      summary: 'Looks valid',
      anomalies: [],
      suggestions: [],
      step_assessments: [{ step_index: 1, status: 'ok', note: 'fine' }],
    },
  }),
  approveRun: vi.fn().mockResolvedValue(undefined),
  rejectRun: vi.fn().mockResolvedValue(undefined),
}));

async function flushAll(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe('Console page smoke coverage', () => {
  beforeEach(() => {
    push.mockReset();
    back.mockReset();
  });

  it('mounts top-level list and home pages', async () => {
    const wrappers = [
      mount(HomePage),
      mount(RecordingsPage),
      mount(SkillsPage),
      mount(RunsPage),
      mount(LearningDebugPage),
      mount(ExplorationWorkbenchPage),
    ];

    await flushAll();

    for (const wrapper of wrappers) {
      expect(wrapper.exists()).toBe(true);
    }
  });

  it('mounts detail pages with mocked route params and data', async () => {
    const wrappers = [
      mount(RecordingDetailPage),
      mount(SkillDetailPage),
      mount(RunDetailPage),
    ];

    await flushAll();

    for (const wrapper of wrappers) {
      expect(wrapper.exists()).toBe(true);
    }
  });
});
