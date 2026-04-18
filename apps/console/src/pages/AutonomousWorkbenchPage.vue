<template>
  <div class="autonomous-workbench">
    <!-- Block 1: Input form -->
    <a-card
      :title="$t('autonomous.runConfig')"
      class="config-card"
      :bordered="false"
    >
      <template #extra>
        <a-tag color="blue">{{ $t('autonomous.badgeProjectCode') }}</a-tag>
      </template>

      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item :label="$t('autonomous.urlLabel')" required>
              <a-input
                v-model:value="form.url"
                :placeholder="$t('autonomous.urlPlaceholder')"
                allow-clear
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item :label="$t('autonomous.goalLabel')">
              <a-input
                v-model:value="form.goal"
                :placeholder="$t('autonomous.goalPlaceholder')"
                allow-clear
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item :label="$t('autonomous.specIdLabel')">
              <a-input
                v-model:value="form.specId"
                :placeholder="$t('autonomous.specIdPlaceholder')"
                allow-clear
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item :label="$t('autonomous.scenarioLabel')">
              <a-select
                v-model:value="form.scenario"
                :placeholder="$t('autonomous.scenarioPlaceholder')"
                allow-clear
                :options="[
                  { value: 'success', label: 'success' },
                  { value: 'failure', label: 'failure' },
                ]"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item :label="$t('autonomous.fillValuesLabel')">
          <div
            v-for="(row, idx) in form.fillValues"
            :key="idx"
            class="fv-row"
          >
            <a-select
              v-model:value="row.key"
              style="width: 160px"
              :options="[
                { value: 'username', label: 'username' },
                { value: 'password', label: 'password' },
                { value: 'email', label: 'email' },
                { value: 'search', label: 'search' },
                { value: 'text', label: 'text' },
              ]"
            />
            <a-input
              v-model:value="row.value"
              :placeholder="$t('autonomous.fillValuesPlaceholder')"
              style="flex: 1"
            />
            <a-button type="text" danger @click="removeFillRow(idx)">×</a-button>
          </div>
          <a-button size="small" @click="addFillRow">
            {{ $t('autonomous.addField') }}
          </a-button>
        </a-form-item>

        <a-row :gutter="16" align="middle">
          <a-col>
            <a-checkbox v-model:checked="form.headless">
              {{ $t('autonomous.headlessLabel') }}
            </a-checkbox>
            <span class="headless-hint">
              ({{ form.headless ? $t('autonomous.headlessOn') : $t('autonomous.headlessOff') }})
            </span>
          </a-col>
        </a-row>

        <a-row style="margin-top: 16px">
          <a-col>
            <a-button
              type="primary"
              size="large"
              :loading="running"
              :disabled="!form.url || running"
              @click="startRun"
            >
              {{ running ? $t('autonomous.running') : $t('autonomous.run') }}
            </a-button>
            <a-button
              v-if="running"
              style="margin-left: 8px"
              @click="abortRun"
            >
              {{ $t('autonomous.abort') }}
            </a-button>
          </a-col>
        </a-row>

        <a-alert
          v-if="errorMessage"
          type="error"
          :message="errorMessage"
          style="margin-top: 16px"
          show-icon
          closable
          @close="errorMessage = ''"
        />
      </a-form>
    </a-card>

    <!-- Block 2: Live status bar -->
    <a-card
      :title="$t('autonomous.liveStatus')"
      class="phase-card"
      :bordered="false"
      style="margin-top: 16px"
    >
      <template #extra>
        <a-tag color="blue">{{ $t('autonomous.badgeProjectCodeSse') }}</a-tag>
      </template>
      <div class="phase-steps">
        <div
          v-for="phase in phaseStates"
          :key="phase.key"
          class="phase-chip"
          :class="`phase-${phase.status}`"
        >
          <span class="phase-dot" />
          <span class="phase-label">{{ $t(`autonomous.${phaseI18nKey(phase.key)}`) }}</span>
          <span v-if="phase.note" class="phase-note">{{ phase.note }}</span>
        </div>
      </div>
      <div v-if="runStartedAt" class="phase-timer">
        {{ $t('autonomous.elapsed') }}: {{ elapsedLabel }}s
      </div>
    </a-card>

    <!-- Block 3: Page analysis -->
    <a-card
      v-if="analysis"
      :title="$t('autonomous.pageAnalysis')"
      class="analysis-card"
      :bordered="false"
      style="margin-top: 16px"
    >
      <template #extra>
        <a-tag color="blue">{{ $t('autonomous.badgeProjectCodeAnalyzer') }}</a-tag>
      </template>
      <p class="source-note">
        {{ $t('autonomous.sourceAnalyzer') }}
      </p>

      <div class="counts">
        <a-tag color="cyan">{{ $t('autonomous.countFillable') }}: {{ analysis.counts?.fillable ?? 0 }}</a-tag>
        <a-tag color="green">{{ $t('autonomous.countSubmit') }}: {{ analysis.counts?.submit ?? 0 }}</a-tag>
        <a-tag>{{ $t('autonomous.countClickable') }}: {{ analysis.counts?.clickable ?? 0 }}</a-tag>
        <a-tag>{{ $t('autonomous.countNavigation') }}: {{ analysis.counts?.navigation ?? 0 }}</a-tag>
        <a-tag>{{ $t('autonomous.countHidden') }}: {{ analysis.total_hidden ?? 0 }}</a-tag>
      </div>

      <a-row :gutter="16" style="margin-top: 12px">
        <a-col :xs="24" :md="16">
          <h4>{{ $t('autonomous.elementsVisible') }}</h4>
          <div v-for="(bucket, name) in groupedElements" :key="name" class="bucket">
            <strong>{{ bucketLabel(name) }} ({{ bucket.length }}):</strong>
            <ul>
              <li v-for="el in bucket" :key="el.selector + el.id">
                <code>{{ el.selector }}</code>
                — <code>&lt;{{ el.tag }}&gt;</code>
                <span v-if="el.semantic_role">
                  · semantic_role=<code>{{ el.semantic_role }}</code>
                </span>
                <span v-if="el.text">· text="{{ el.text.slice(0, 40) }}"</span>
                <span class="reason">· {{ el.reason }}</span>
              </li>
            </ul>
          </div>

          <h4>{{ $t('autonomous.recommendedActions') }}</h4>
          <ol>
            <li v-for="act in analysis.recommended_actions" :key="act.step">
              <strong>{{ act.action_type }}</strong>
              → <code>{{ act.target_selector || '—' }}</code>
              <span v-if="act.value"> = <code>{{ act.value }}</code></span>
              <div class="reason">{{ act.reason }}</div>
            </li>
          </ol>
        </a-col>
        <a-col :xs="24" :md="8">
          <h4>{{ $t('autonomous.initialScreenshot') }}</h4>
          <a-image
            v-if="analysis.screenshot_ref"
            :src="toScreenshotUrl(analysis.screenshot_ref)"
            class="screenshot"
            :preview="{ mask: $t('autonomous.clickToZoom') }"
          />
          <a-empty v-else :description="$t('autonomous.noScreenshot')" />
        </a-col>
      </a-row>
    </a-card>

    <!-- Block 4: Execution timeline -->
    <a-card
      v-if="steps.length > 0"
      :title="$t('autonomous.timeline')"
      class="timeline-card"
      :bordered="false"
      style="margin-top: 16px"
    >
      <template #extra>
        <a-tag color="blue">{{ $t('autonomous.badgeProjectCodeExplorer') }}</a-tag>
      </template>
      <p class="source-note">
        {{ $t('autonomous.sourceTimeline') }}
      </p>
      <a-timeline>
        <a-timeline-item
          v-for="step in steps"
          :key="step.step_index"
          :color="stepColor(step)"
        >
          <div class="step-header">
            <strong>[{{ step.step_index }}] {{ step.action_type }}</strong>
            <a-tag v-if="step.ok === true" color="green">{{ $t('autonomous.stepOk') }}</a-tag>
            <a-tag v-else-if="step.ok === false" color="red">{{ $t('autonomous.stepFailed') }}</a-tag>
            <a-tag v-else color="blue">{{ $t('autonomous.stepRunning') }}</a-tag>
          </div>
          <div class="step-body">
            <div v-if="step.target_description">
              {{ $t('autonomous.stepTarget') }}: <code>{{ step.target_description }}</code>
            </div>
            <div v-if="step.value">
              {{ $t('autonomous.stepValue') }}: <code>{{ step.value }}</code>
            </div>
            <div v-if="step.actual_value !== undefined">
              {{ $t('autonomous.stepActual') }}: <code>{{ step.actual_value }}</code>
            </div>
            <div v-if="step.url_changed">
              {{ $t('autonomous.stepUrl') }} → <code>{{ step.url_after?.slice(0, 120) }}</code>
            </div>
            <div v-if="step.title_changed">
              {{ $t('autonomous.stepTitle') }} → <code>{{ step.title_after }}</code>
            </div>
            <div v-if="step.error" class="error-text">
              {{ $t('autonomous.stepError') }}: {{ step.error }}
            </div>
            <div v-if="step.result_signals">
              {{ $t('autonomous.stepSignals') }}: <code>{{ JSON.stringify(step.result_signals) }}</code>
            </div>
            <a-image
              v-if="step.screenshot_ref"
              :src="toScreenshotUrl(step.screenshot_ref)"
              class="screenshot screenshot-thumb"
              :preview="{ mask: $t('autonomous.clickToZoom') }"
            />
          </div>
        </a-timeline-item>
      </a-timeline>
    </a-card>

    <!-- Block 5: Verification -->
    <a-card
      v-if="selfAssessment || supervisor || scorecard"
      :title="$t('autonomous.verification')"
      class="verify-card"
      :bordered="false"
      style="margin-top: 16px"
    >
      <a-row :gutter="16">
        <a-col :xs="24" :md="8">
          <a-card size="small" :bordered="true" :title="$t('autonomous.selfVerdict')">
            <template #extra><a-tag color="blue">{{ $t('autonomous.badgeProjectCode') }}</a-tag></template>
            <div v-if="selfAssessment">
              <a-tag :color="verdictColor(selfAssessment.verdict)">
                {{ selfAssessment.verdict }}
              </a-tag>
              <div class="summary">{{ selfAssessment.summary }}</div>
              <div v-if="selfAssessment.final_url" class="final-meta">
                {{ $t('autonomous.finalUrl') }}:
                <code>{{ selfAssessment.final_url.slice(0, 120) }}</code>
              </div>
              <div v-if="selfAssessment.final_title" class="final-meta">
                {{ $t('autonomous.finalTitle') }}: {{ selfAssessment.final_title }}
              </div>
            </div>
            <a-empty v-else :description="$t('autonomous.pendingVerdict')" />
          </a-card>
        </a-col>
        <a-col :xs="24" :md="8">
          <a-card size="small" :bordered="true" :title="$t('autonomous.supervisorTitle')">
            <template #extra><a-tag color="purple">{{ $t('autonomous.badgeProjectLlmAgent') }}</a-tag></template>
            <div v-if="supervisor">
              <a-tag :color="verdictColor(supervisor.verdict)">
                {{ supervisor.verdict }}
              </a-tag>
              <a-tag>{{ $t('autonomous.confidence') }}: {{ supervisor.confidence }}</a-tag>
              <div class="summary">{{ supervisor.summary }}</div>
              <div v-if="supervisor.anomalies?.length">
                <strong>{{ $t('autonomous.anomalies') }}:</strong>
                <ul>
                  <li v-for="(a, i) in supervisor.anomalies" :key="i">{{ a }}</li>
                </ul>
              </div>
              <div v-if="supervisor.suggestions?.length">
                <strong>{{ $t('autonomous.suggestions') }}:</strong>
                <ul>
                  <li v-for="(s, i) in supervisor.suggestions" :key="i">{{ s }}</li>
                </ul>
              </div>
              <!-- Reasoning trace from the LLM (contents of <think>...</think>
                   blocks). Renders only when the model emitted one. -->
              <a-collapse v-if="supervisor._thinking" ghost style="margin-top: 8px">
                <a-collapse-panel key="thinking" :header="$t('autonomous.thinkingProcess')">
                  <div class="thinking-toolbar">
                    <a-button size="small" @click="copyText(supervisor._thinking)">
                      {{ $t('autonomous.copyText') }}
                    </a-button>
                    <span v-if="supervisor._model" class="thinking-model">
                      {{ $t('autonomous.model') }}: <code>{{ supervisor._model }}</code>
                    </span>
                  </div>
                  <pre class="thinking-text">{{ supervisor._thinking }}</pre>
                </a-collapse-panel>
              </a-collapse>
            </div>
            <a-empty v-else :description="$t('autonomous.pendingVerdict')" />
          </a-card>
        </a-col>
        <a-col :xs="24" :md="8">
          <a-card size="small" :bordered="true" :title="$t('autonomous.scorecardTitle')">
            <template #extra><a-tag color="blue">{{ $t('autonomous.badgeProjectCodeSpec') }}</a-tag></template>
            <div v-if="scorecard">
              <div
                v-for="metric in scoreMetrics"
                :key="metric.key"
                class="score-row"
              >
                <span class="score-label">{{ metric.label }}</span>
                <a-progress
                  :percent="Math.round(metric.score * 100)"
                  :status="metric.score >= 1 ? 'success' : metric.score >= 0.5 ? 'active' : 'exception'"
                  size="small"
                />
              </div>
              <a-collapse ghost style="margin-top: 8px">
                <a-collapse-panel key="details" :header="$t('autonomous.rawChecks')">
                  <pre class="raw">{{ JSON.stringify(scorecard, null, 2) }}</pre>
                </a-collapse-panel>
              </a-collapse>
            </div>
            <a-empty v-else :description="$t('autonomous.enableSpecHint')" />
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- Block 7: Raw SSE event stream — full audit trail with copy -->
    <a-card
      v-if="rawEvents.length > 0"
      :title="$t('autonomous.sseRawTitle')"
      class="sse-card"
      :bordered="false"
      style="margin-top: 16px"
    >
      <template #extra>
        <a-tag color="blue">{{ $t('autonomous.badgeProjectCodeSse') }}</a-tag>
      </template>
      <p class="source-note">{{ $t('autonomous.sseRawNote') }}</p>
      <div class="sse-toolbar">
        <a-button size="small" @click="copyAllRawEvents">
          {{ $t('autonomous.copyAllEvents') }} ({{ rawEvents.length }})
        </a-button>
        <a-button size="small" @click="showRawModal = true">
          {{ $t('autonomous.openRawModal') }}
        </a-button>
        <span class="sse-count">
          {{ $t('autonomous.sseEventsReceived') }}: {{ rawEvents.length }}
        </span>
      </div>
      <a-collapse accordion ghost style="margin-top: 8px">
        <a-collapse-panel
          v-for="(evt, i) in rawEvents"
          :key="i"
          :header="`[${i}] ${evt.event}  ·  ${evt.relativeMs}ms`"
        >
          <div class="sse-item-toolbar">
            <a-button size="small" @click="copyRawEvent(i)">
              {{ $t('autonomous.copyThisEvent') }}
            </a-button>
          </div>
          <pre class="sse-raw">{{ formatEvent(evt) }}</pre>
        </a-collapse-panel>
      </a-collapse>
    </a-card>

    <!-- Full-screen modal for raw SSE stream (when the inline collapse is too cramped) -->
    <a-modal
      v-model:open="showRawModal"
      :title="$t('autonomous.sseRawTitle')"
      :width="900"
      :footer="null"
    >
      <div class="sse-toolbar" style="margin-bottom: 12px">
        <a-button size="small" @click="copyAllRawEvents">
          {{ $t('autonomous.copyAllEvents') }} ({{ rawEvents.length }})
        </a-button>
        <span class="sse-count">
          {{ $t('autonomous.sseEventsReceived') }}: {{ rawEvents.length }}
        </span>
      </div>
      <pre class="sse-raw-all">{{ allEventsText }}</pre>
    </a-modal>

    <!-- Block 6: Source-origin legend -->
    <a-card
      :title="$t('autonomous.sources')"
      class="source-card"
      :bordered="false"
      size="small"
      style="margin-top: 16px"
    >
      <ul class="source-legend">
        <li>
          <a-tag color="blue">{{ $t('autonomous.badgeProjectCode') }}</a-tag>
          — {{ $t('autonomous.legendProjectCode') }}
        </li>
        <li>
          <a-tag color="purple">{{ $t('autonomous.badgeProjectLlmAgent') }}</a-tag>
          — {{ $t('autonomous.legendProjectLlm') }}
        </li>
        <li>
          <a-tag>{{ $t('autonomous.badgeProjectCodeSpec') }}</a-tag>
          — {{ $t('autonomous.legendSpec') }}
        </li>
        <li>
          <em>—</em>
          {{ $t('autonomous.legendNone') }}
        </li>
      </ul>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { message } from 'ant-design-vue';
import { streamAutonomousRun } from '@/api/autonomousStream';
import { resolveApiConfig } from '@/api/client';

const { t, locale } = useI18n();

// ─── Phase key → i18n key map ────────────────────────────────
// Phase internal keys don't always match English labels (e.g. 'analysis'
// but the label is 'analyze'). Explicit map keeps both sides stable.
const PHASE_I18N_KEY: Record<string, string> = {
  navigate: 'phaseNavigate',
  analysis: 'phaseAnalyze',
  plan: 'phasePlan',
  execute: 'phaseExecute',
  assess: 'phaseSelfAssess',
  supervisor: 'phaseSupervisor',
  verify: 'phaseVerify',
  done: 'phaseDone',
};
function phaseI18nKey(key: string): string {
  return PHASE_I18N_KEY[key] || key;
}

// Map analyzer bucket names to i18n labels. Keeps raw keys in data model.
function bucketLabel(name: string): string {
  const key = `autonomous.count${name.charAt(0).toUpperCase()}${name.slice(1)}`;
  const translated = t(key);
  return translated === key ? name : translated;
}

// ─── Form state ──────────────────────────────────────────────

interface FillRow { key: string; value: string }

const form = reactive({
  url: 'http://127.0.0.1:5175/login',
  goal: '',
  specId: 'login',
  scenario: 'success' as 'success' | 'failure' | undefined,
  headless: true,
  fillValues: [
    { key: 'username', value: 'admin' },
    { key: 'password', value: '123456' },
  ] as FillRow[],
});

function addFillRow() {
  form.fillValues.push({ key: 'text', value: '' });
}
function removeFillRow(idx: number) {
  form.fillValues.splice(idx, 1);
}

// ─── Run state ───────────────────────────────────────────────

const running = ref(false);
const errorMessage = ref('');
const runStartedAt = ref<number | null>(null);
const now = ref<number>(Date.now());
let ticker: ReturnType<typeof setInterval> | null = null;
let abort: (() => void) | null = null;

const elapsedLabel = computed(() => {
  if (!runStartedAt.value) return '0.0';
  return ((now.value - runStartedAt.value) / 1000).toFixed(1);
});

// ─── Phase tracking ──────────────────────────────────────────

interface PhaseState {
  key: string;
  label: string;
  status: 'pending' | 'active' | 'done' | 'failed';
  note?: string;
}

// Phase labels come from i18n in the template via phaseI18nKey(). The
// `label` field below is retained as a fallback debug identifier only.
const phaseOrder: Array<{ key: string; label: string }> = [
  { key: 'navigate', label: 'navigate' },
  { key: 'analysis', label: 'analyze' },
  { key: 'plan', label: 'plan' },
  { key: 'execute', label: 'execute' },
  { key: 'assess', label: 'self-assess' },
  { key: 'supervisor', label: 'supervisor' },
  { key: 'verify', label: 'verify' },
  { key: 'done', label: 'done' },
];

const phaseStates = reactive<PhaseState[]>(
  phaseOrder.map((p) => ({ ...p, status: 'pending' })),
);

function setPhase(key: string, status: PhaseState['status'], note?: string) {
  const phase = phaseStates.find((p) => p.key === key);
  if (phase) {
    phase.status = status;
    if (note !== undefined) phase.note = note;
  }
}
function resetPhases() {
  phaseStates.forEach((p) => { p.status = 'pending'; p.note = undefined; });
}

// ─── Captured output ─────────────────────────────────────────

interface StepData {
  step_index: number;
  action_type: string;
  target_description?: string;
  target_selector?: string;
  value?: string | null;
  ok?: boolean;
  error?: string;
  url_changed?: boolean;
  title_changed?: boolean;
  url_after?: string;
  title_after?: string;
  actual_value?: string;
  screenshot_ref?: string;
  result_signals?: unknown;
}

const analysis = ref<any>(null);
const steps = ref<StepData[]>([]);
const selfAssessment = ref<any>(null);
const supervisor = ref<any>(null);
const scorecard = ref<any>(null);
let stepCountTotal = 0;

// Raw SSE event audit log — every event that arrived from the stream,
// timestamped, for transparency. User can copy individual events or the
// whole stream.
interface RawEvent {
  index: number;
  event: string;
  data: unknown;
  timestampMs: number;   // absolute epoch ms
  relativeMs: number;    // ms since run_started
}
const rawEvents = ref<RawEvent[]>([]);
const showRawModal = ref(false);

const allEventsText = computed(() => {
  return rawEvents.value.map(formatEvent).join('\n\n');
});

function formatEvent(evt: RawEvent): string {
  return `[${evt.index}] event: ${evt.event}\n    t+${evt.relativeMs}ms\n${JSON.stringify(evt.data, null, 2)}`;
}

async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    message.success(t('autonomous.copied'));
  } catch (err) {
    message.error(t('autonomous.copyFailed') + (err as Error).message);
  }
}
async function copyRawEvent(idx: number): Promise<void> {
  const evt = rawEvents.value[idx];
  if (!evt) return;
  await copyText(formatEvent(evt));
}
async function copyAllRawEvents(): Promise<void> {
  await copyText(allEventsText.value);
}

const scoreMetrics = computed(() => {
  if (!scorecard.value) return [];
  return [
    { key: 'element_recognition', label: t('autonomous.scoreElementRecognition'),
      score: scorecard.value.element_recognition?.score ?? 0 },
    { key: 'action_coverage', label: t('autonomous.scoreActionCoverage'),
      score: scorecard.value.action_coverage?.score ?? 0 },
    { key: 'verdict_accuracy', label: t('autonomous.scoreVerdictAccuracy'),
      score: scorecard.value.verdict_accuracy?.score ?? 0 },
    { key: 'distraction_avoidance', label: t('autonomous.scoreDistractionAvoidance'),
      score: scorecard.value.distraction_avoidance?.score ?? 0 },
    { key: 'supervisor_agreement', label: t('autonomous.scoreSupervisorAgreement'),
      score: scorecard.value.supervisor_agreement?.score ?? 0 },
  ];
});

const groupedElements = computed(() => {
  if (!analysis.value) return {};
  const g: Record<string, any[]> = {};
  for (const cat of ['fillable', 'submit', 'clickable', 'navigation']) {
    const arr = analysis.value[cat];
    if (arr && arr.length > 0) g[cat] = arr;
  }
  return g;
});

// ─── Screenshot URL helper ───────────────────────────────────

const apiBase = resolveApiConfig().baseURL;
function toScreenshotUrl(ref: string | null | undefined): string {
  if (!ref) return '';
  // Backend returns paths like "/exploration/screenshots/xxx.png".
  // In proxy mode we prepend "/api" so vite forwards correctly.
  return ref.startsWith('http') ? ref : `${apiBase}${ref}`;
}

// ─── Helpers for UI ──────────────────────────────────────────

function stepColor(step: StepData): string {
  if (step.ok === true) return 'green';
  if (step.ok === false) return 'red';
  return 'blue';
}

function verdictColor(v: string | undefined): string {
  if (!v) return 'default';
  if (['success'].includes(v)) return 'green';
  if (['failure', 'incomplete'].includes(v)) return 'red';
  if (['partial_success', 'no_progress'].includes(v)) return 'orange';
  return 'default';
}

// ─── SSE event handling ──────────────────────────────────────

function resetOutputs() {
  analysis.value = null;
  steps.value = [];
  selfAssessment.value = null;
  supervisor.value = null;
  scorecard.value = null;
  stepCountTotal = 0;
  errorMessage.value = '';
  rawEvents.value = [];
  resetPhases();
}

function handleEvent(evt: { event: string; data: any }) {
  const { event, data } = evt;
  // Capture every event into the audit log before any routing.
  const now = Date.now();
  const rel = runStartedAt.value ? now - runStartedAt.value : 0;
  rawEvents.value.push({
    index: rawEvents.value.length,
    event,
    data,
    timestampMs: now,
    relativeMs: rel,
  });
  switch (event) {
    case 'run_started':
      break;
    case 'navigate_started':
      setPhase('navigate', 'active');
      break;
    case 'navigate_done':
      setPhase('navigate', 'done', data?.title || '');
      break;
    case 'analysis_started':
      setPhase('analysis', 'active');
      break;
    case 'analysis_done':
      analysis.value = data;
      setPhase('analysis', 'done',
        `${data?.total_visible ?? 0} visible / ${data?.total_hidden ?? 0} hidden`);
      break;
    case 'plan_done':
      if (analysis.value) analysis.value.recommended_actions = data.actions;
      stepCountTotal = data.total_actions || 0;
      setPhase('plan', 'done', `${stepCountTotal} actions`);
      setPhase('execute', 'active');
      break;
    case 'step_started': {
      const existing = steps.value.find((s) => s.step_index === data.step_index);
      if (existing) {
        Object.assign(existing, data);
      } else {
        steps.value.push({ ...data });
      }
      break;
    }
    case 'step_done': {
      const idx = steps.value.findIndex((s) => s.step_index === data.step_index);
      if (idx >= 0) steps.value[idx] = { ...steps.value[idx], ...data };
      else steps.value.push(data);
      const completed = steps.value.filter((s) => s.ok !== undefined).length;
      setPhase('execute', 'active', `${completed}/${stepCountTotal}`);
      break;
    }
    case 'self_assessment_done':
      selfAssessment.value = data;
      setPhase('execute', 'done', `${steps.value.length}/${stepCountTotal}`);
      setPhase('assess', 'done', data.verdict);
      setPhase('supervisor', 'active');
      break;
    case 'supervisor_done':
      supervisor.value = data;
      setPhase('supervisor', 'done', data?.verdict || '');
      setPhase('verify', 'active');
      break;
    case 'verification_done':
      if (data?.scorecard) scorecard.value = data.scorecard;
      setPhase('verify', 'done');
      break;
    case 'run_completed':
      setPhase('verify', 'done');
      setPhase('done', 'done');
      running.value = false;
      break;
    case 'run_failed':
      errorMessage.value = data?.error || 'run failed';
      phaseStates.forEach((p) => {
        if (p.status === 'active' || p.status === 'pending') p.status = 'failed';
      });
      running.value = false;
      break;
    default:
      // unknown event — ignore
      break;
  }
}

// ─── Actions ─────────────────────────────────────────────────

function startRun() {
  if (running.value) return;
  if (!form.url) {
    errorMessage.value = t('autonomous.urlRequired');
    return;
  }
  resetOutputs();
  running.value = true;
  runStartedAt.value = Date.now();
  now.value = Date.now();
  if (ticker) clearInterval(ticker);
  ticker = setInterval(() => { now.value = Date.now(); }, 100);

  const fillValues: Record<string, string> = {};
  for (const row of form.fillValues) {
    if (row.key && row.value !== undefined && row.value !== '') {
      fillValues[row.key] = row.value;
    }
  }

  abort = streamAutonomousRun(
    {
      url: form.url,
      goal: form.goal || undefined,
      fill_values: Object.keys(fillValues).length > 0 ? fillValues : undefined,
      headless: form.headless,
      spec_id: form.specId || null,
      scenario: form.scenario || null,
      // Pass the current UI locale so the project-internal Supervisor Agent
      // (the LLM part) responds in the user's language.
      language: String(locale.value),
    },
    {
      onEvent: handleEvent,
      onError: (err) => {
        errorMessage.value = err.message;
        running.value = false;
        if (ticker) { clearInterval(ticker); ticker = null; }
        message.error(t('autonomous.streamFailed') + err.message);
      },
      onDone: () => {
        running.value = false;
        if (ticker) { clearInterval(ticker); ticker = null; }
        abort = null;
      },
    },
  );
}

function abortRun() {
  if (abort) {
    abort();
    message.info(t('autonomous.runAborted'));
  }
}

onBeforeUnmount(() => {
  if (abort) abort();
  if (ticker) clearInterval(ticker);
});
</script>

<style scoped>
.autonomous-workbench {
  max-width: 1400px;
  margin: 0 auto;
}
.config-card,
.phase-card,
.analysis-card,
.timeline-card,
.verify-card,
.source-card,
.sse-card {
  background: #fff;
}
.thinking-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.thinking-model {
  font-size: 11px;
  color: #6b7280;
}
.thinking-text {
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  padding: 10px;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow: auto;
  margin: 0;
}
.sse-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.sse-count {
  font-size: 12px;
  color: #6b7280;
}
.sse-item-toolbar {
  margin-bottom: 8px;
}
.sse-raw,
.sse-raw-all {
  background: #0f172a;
  color: #e2e8f0;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11px;
  line-height: 1.5;
  padding: 12px;
  border-radius: 4px;
  max-height: 400px;
  overflow: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.sse-raw-all {
  max-height: 600px;
}
.fv-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.headless-hint {
  color: #8c8c8c;
  font-size: 12px;
  margin-left: 8px;
}
.phase-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.phase-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #fafafa;
  font-size: 13px;
}
.phase-chip.phase-pending { color: #8c8c8c; }
.phase-chip.phase-active {
  border-color: #1677ff;
  background: #e6f4ff;
  color: #1677ff;
  animation: pulse 1.2s infinite;
}
.phase-chip.phase-done {
  border-color: #52c41a;
  background: #f6ffed;
  color: #389e0d;
}
.phase-chip.phase-failed {
  border-color: #ff4d4f;
  background: #fff1f0;
  color: #cf1322;
}
.phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  display: inline-block;
}
.phase-note {
  font-size: 11px;
  opacity: 0.75;
  margin-left: 4px;
}
.phase-timer {
  margin-top: 8px;
  font-size: 12px;
  color: #8c8c8c;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.source-note {
  color: #8c8c8c;
  font-size: 12px;
  margin-top: -8px;
  margin-bottom: 12px;
}
.counts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.bucket {
  margin-bottom: 8px;
  font-size: 12px;
}
.bucket ul {
  margin: 4px 0 8px 20px;
  padding: 0;
}
.bucket li {
  margin-bottom: 2px;
}
.reason {
  color: #8c8c8c;
  font-size: 11px;
}
.screenshot {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}
.screenshot-thumb {
  max-width: 400px;
  margin-top: 4px;
}
.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.step-body {
  font-size: 12px;
  margin-top: 4px;
  color: #595959;
}
.step-body code {
  background: #f5f5f5;
  padding: 0 4px;
  border-radius: 2px;
}
.error-text {
  color: #cf1322;
  margin-top: 2px;
}
.summary {
  margin-top: 8px;
  font-size: 13px;
  color: #595959;
}
.final-meta {
  font-size: 11px;
  color: #8c8c8c;
  margin-top: 4px;
}
.score-row {
  margin-bottom: 8px;
}
.score-label {
  display: inline-block;
  width: 150px;
  font-size: 12px;
}
.raw {
  font-size: 11px;
  max-height: 300px;
  overflow: auto;
  background: #fafafa;
  padding: 8px;
  border-radius: 4px;
}
.source-legend {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.8;
}
.source-legend li {
  margin-bottom: 4px;
}
</style>
