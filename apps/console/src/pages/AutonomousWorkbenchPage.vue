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

        <!-- Spec auto-derived from URL. Users don't pick a spec_id;
             it's inferred by matching the URL path against the
             `url_pattern` of each authored spec. The alert below
             tells the operator which spec (if any) was matched. -->
        <a-alert
          v-if="selectedSpec"
          type="info"
          show-icon
          :message="$t('autonomous.specMatched', {
            id: selectedSpec.spec_id,
            count: selectedSpec.scenarios.length,
          })"
          :description="selectedSpec.description || ''"
          style="margin-bottom: 16px"
        />
        <a-alert
          v-else-if="form.url"
          type="warning"
          show-icon
          :message="$t('autonomous.specNoMatch')"
          style="margin-bottom: 16px"
        />

        <!-- Test scenario — dev fixture concept, see tooltip. Hidden
             entirely when no spec is matched (nothing to pick from). -->
        <a-row :gutter="16" v-if="selectedSpec">
          <a-col :span="24">
            <a-form-item>
              <template #label>
                <span>
                  {{ $t('autonomous.scenarioLabel') }}
                  <a-tooltip :title="$t('autonomous.scenarioHint')" placement="right">
                    <span class="scenario-info-icon">ⓘ</span>
                  </a-tooltip>
                </span>
              </template>
              <a-select
                v-model:value="form.scenario"
                :placeholder="$t('autonomous.scenarioPlaceholder')"
                allow-clear
                :disabled="scenarioOptions.length === 0"
                :options="scenarioOptions"
                @change="onScenarioChange"
              />
              <div v-if="scenarioDescription" class="scenario-hint">
                {{ scenarioDescription }}
              </div>
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
                { value: 'name', label: 'name' },
                { value: 'role', label: 'role' },
                { value: 'status', label: 'status' },
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

        <a-form-item :label="$t('autonomous.toggleValuesLabel')">
          <div
            v-for="(row, idx) in form.toggleValues"
            :key="idx"
            class="fv-row"
          >
            <a-select
              v-model:value="row.key"
              style="width: 160px"
              :options="[
                { value: 'status', label: 'status' },
                { value: 'role', label: 'role' },
                { value: 'name', label: 'name' },
              ]"
            />
            <a-input
              v-model:value="row.value"
              :placeholder="$t('autonomous.toggleValuesPlaceholder')"
              style="flex: 1"
            />
            <a-button type="text" danger @click="removeToggleRow(idx)">×</a-button>
          </div>
          <a-button size="small" @click="addToggleRow">
            {{ $t('autonomous.addToggle') }}
          </a-button>
          <div class="fv-hint">{{ $t('autonomous.toggleValuesHint') }}</div>
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
              <li v-for="el in bucket" :key="el.selector + el.id" class="el-item">
                <!-- Line 1: the stable identifiers — selector and
                     element tag/type. These are what the planner
                     actually operates on. -->
                <div class="el-primary">
                  <code>{{ el.selector }}</code>
                  — <code>&lt;{{ el.tag }}{{ el.element_type ? ` type="${el.element_type}"` : '' }}&gt;</code>
                </div>
                <!-- Line 2: the human-readable hints. Shown only when
                     present so sparse elements don't reserve empty
                     space. `label` is especially valuable — it's the
                     text a human sees next to the input. -->
                <div class="el-secondary">
                  <span v-if="el.label_text" class="el-label">
                    · label="{{ el.label_text }}"<span v-if="el.label_source" class="el-source"> ({{ el.label_source }})</span>
                  </span>
                  <span v-if="el.name">· name="{{ el.name }}"</span>
                  <span v-if="el.placeholder">· placeholder="{{ el.placeholder }}"</span>
                  <span v-if="el.aria_label">· aria_label="{{ el.aria_label }}"</span>
                  <span v-if="el.semantic_role">
                    · semantic_role=<code>{{ el.semantic_role }}</code>
                  </span>
                  <span v-if="el.text">· text="{{ el.text.slice(0, 40) }}"</span>
                  <span v-if="el.content_hint" class="el-content-hint">
                    · content="{{ el.content_hint }}"
                  </span>
                  <span class="reason">· {{ el.reason }}</span>
                </div>
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
              <a-tag :color="confidenceColor(supervisor.confidence)">
                {{ $t('autonomous.confidence') }}: {{ supervisor.confidence }}
              </a-tag>
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
import { computed, reactive, ref, onBeforeUnmount, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { message } from 'ant-design-vue';
import { streamAutonomousRun } from '@/api/autonomousStream';
import { resolveApiConfig } from '@/api/client';
import { listSpecs, type SpecSummary } from '@/api/exploration';

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
interface ToggleRow { key: string; value: string }

// Form starts empty by design. The workbench expects callers to either
// (a) deep-link into it with ?url=…&spec_id=…&scenario=… (e.g. the
// "Run in workbench" buttons on the validation-site IndexPage), or
// (b) pick a spec from the spec_id dropdown once specs are loaded.
// There is no built-in default page, so opening the workbench fresh
// won't silently point at login.
const form = reactive({
  url: '',
  goal: '',
  specId: undefined as string | undefined,
  scenario: undefined as string | undefined,
  headless: true,
  fillValues: [] as FillRow[],
  toggleValues: [] as ToggleRow[],
});

const route = useRoute();

function addFillRow() {
  form.fillValues.push({ key: 'text', value: '' });
}
function removeFillRow(idx: number) {
  form.fillValues.splice(idx, 1);
}

function addToggleRow() {
  form.toggleValues.push({ key: 'status', value: '' });
}
function removeToggleRow(idx: number) {
  form.toggleValues.splice(idx, 1);
}

// ─── Spec auto-matching + scenario prefill ───────────────────
// The operator doesn't pick a spec_id directly — it's derived from
// form.url by matching the URL path against each spec's url_pattern.
// - If exactly one spec matches, selectedSpec is set, the scenario
//   select appears with the spec's scenarios, and fill_values gets
//   populated from scenarios[chosen].inputs.
// - If no spec matches, selectedSpec is null; the scenario area is
//   hidden and the run will execute as exploration-only (no
//   comparator).
// form.specId is kept in the form reactive because the backend still
// expects it in the payload; it's just no longer user-editable.

const specs = ref<SpecSummary[]>([]);
const specsLoaded = ref(false);
const selectedSpec = ref<SpecSummary | null>(null);

const scenarioOptions = computed(() => {
  if (!selectedSpec.value) return [];
  return selectedSpec.value.scenarios.map((sc) => ({
    value: sc.key,
    label: sc.description ? `${sc.key} — ${sc.description.slice(0, 50)}` : sc.key,
  }));
});

const scenarioDescription = computed(() => {
  if (!selectedSpec.value || !form.scenario) return '';
  const sc = selectedSpec.value.scenarios.find((s) => s.key === form.scenario);
  return sc?.description ?? '';
});

async function loadSpecs(): Promise<void> {
  try {
    specs.value = await listSpecs();
  } catch (err) {
    message.warning(t('autonomous.specsLoadFailed') + (err as Error).message);
  } finally {
    specsLoaded.value = true;
    // After the spec catalogue lands, try the URL once (in case the
    // URL was already hydrated from ?url= but specs hadn't loaded yet).
    applyUrl(form.url);
  }
}

// Return the spec whose url_pattern is contained in the given URL's
// path. Keeps the matching dumb — substring, not regex — so spec
// authors don't have to worry about escaping.
function matchSpecByUrl(rawUrl: string): SpecSummary | null {
  if (!rawUrl) return null;
  let path: string;
  try {
    path = new URL(rawUrl).pathname;
  } catch {
    // Allow bare paths like "/users" too, in case an operator types
    // without a host.
    path = rawUrl.startsWith('/') ? rawUrl : '';
  }
  if (!path) return null;
  return (
    specs.value.find((s) => s.url_pattern && path.includes(s.url_pattern)) ?? null
  );
}

// Apply the URL → spec derivation. Called whenever form.url changes
// and also once after specs finish loading. Safe to call with an
// empty URL (clears the spec state).
function applyUrl(url: string): void {
  if (!specsLoaded.value) return;
  const matched = matchSpecByUrl(url);

  if (!matched) {
    selectedSpec.value = null;
    form.specId = undefined;
    form.scenario = undefined;
    form.fillValues = [];
    form.toggleValues = [];
    return;
  }

  // Matched a spec. If it's a different spec from the one we had,
  // or if the current scenario doesn't belong to this spec, reset
  // scenario to the spec's first and repopulate fill_values.
  const changed = selectedSpec.value?.spec_id !== matched.spec_id;
  selectedSpec.value = matched;
  form.specId = matched.spec_id;

  const keys = matched.scenarios.map((sc) => sc.key);
  if (changed || !form.scenario || !keys.includes(form.scenario)) {
    form.scenario = keys[0];
  }
  applyScenarioInputs();
}

function applyScenarioInputs(): void {
  // Replace fillValues + toggleValues with the scenario's inputs /
  // selections. Overwriting (not merging) is deliberate — picking a
  // scenario is a fresh setup, and merging would leave stale rows
  // from the previous scenario around.
  if (!selectedSpec.value || !form.scenario) return;
  const sc = selectedSpec.value.scenarios.find((s) => s.key === form.scenario);
  if (!sc) return;
  form.fillValues = Object.entries(sc.inputs).map(([key, value]) => ({ key, value }));
  const selections = sc.selections ?? {};
  form.toggleValues = Object.entries(selections).map(([key, value]) => ({ key, value }));
}

function onScenarioChange(): void {
  applyScenarioInputs();
}

// Watch form.url. Debounce via a microtask so rapid typing doesn't
// re-run the match logic on every keystroke. In practice the match
// is cheap (string contains) so an explicit debounce isn't needed.
watch(() => form.url, (val) => applyUrl(val));

// Hydrate the form from ?url=&scenario=&goal= query params. spec_id
// is no longer read from the URL directly — it's derived from ?url=
// once specs have loaded. A leftover ?spec_id= is harmless but
// ignored; the URL is the source of truth.
function hydrateFromQuery(): void {
  const q = route.query;
  const pick = (v: unknown) => (typeof v === 'string' ? v : undefined);

  const url = pick(q.url);
  const scenario = pick(q.scenario);
  const goal = pick(q.goal);

  if (url) form.url = url;
  if (goal) form.goal = goal;
  // Keep the scenario string around; applied in applyUrl once the
  // URL has been matched to a spec.
  if (scenario) form.scenario = scenario;
}

onMounted(() => {
  hydrateFromQuery();
  loadSpecs();
});

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

// Supervisor reports its own confidence (high / medium / low). Color
// indicates certainty, not outcome — "high" doesn't mean "pass".
function confidenceColor(c: string | undefined): string {
  if (!c) return 'default';
  const v = c.toLowerCase();
  if (v === 'high') return 'blue';
  if (v === 'medium') return 'cyan';
  if (v === 'low') return 'orange';
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

  // Toggle values keep empty-string values intentionally (Ant Design's
  // "All" radio uses value="" — a meaningful selection, not a skip).
  // Only skip rows whose KEY is empty.
  const toggleValues: Record<string, string> = {};
  for (const row of form.toggleValues) {
    if (row.key) {
      toggleValues[row.key] = row.value ?? '';
    }
  }

  abort = streamAutonomousRun(
    {
      url: form.url,
      goal: form.goal || undefined,
      fill_values: Object.keys(fillValues).length > 0 ? fillValues : undefined,
      toggle_values: Object.keys(toggleValues).length > 0 ? toggleValues : undefined,
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
.fv-hint {
  color: #8c8c8c;
  font-size: 11px;
  margin-top: 6px;
  line-height: 1.4;
}
.headless-hint {
  color: #8c8c8c;
  font-size: 12px;
  margin-left: 8px;
}
.scenario-hint {
  color: #8c8c8c;
  font-size: 11px;
  margin-top: 4px;
  line-height: 1.4;
}
.scenario-info-icon {
  display: inline-block;
  margin-left: 4px;
  color: #1677ff;
  cursor: help;
  font-size: 12px;
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
  margin-bottom: 6px;
}
.el-item {
  line-height: 1.5;
}
.el-primary {
  font-size: 12px;
}
.el-secondary {
  font-size: 11px;
  color: #595959;
  padding-left: 12px;
}
.el-label {
  color: #1677ff;
  font-weight: 500;
}
.el-source {
  color: #8c8c8c;
  font-weight: normal;
  font-size: 10px;
}
.el-content-hint {
  color: #722ed1;
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
