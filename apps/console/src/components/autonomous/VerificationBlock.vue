<template>
  <a-card
    v-if="selfAssessment || supervisor || scorecard"
    :title="$t('autonomous.verification')"
    class="verify-card"
    :bordered="false"
  >
    <a-row :gutter="16">
      <a-col :xs="24" :md="8">
        <a-card size="small" :bordered="true" :title="$t('autonomous.selfVerdict')">
          <template #extra>
            <a-tag color="blue">{{ $t('autonomous.badgeProjectCode') }}</a-tag>
          </template>
          <div v-if="selfAssessment">
            <a-tag :color="verdictColor(selfAssessment.verdict)">
              {{ selfAssessment.verdict }}
            </a-tag>
            <!-- Reconciliation badge: for negative-path scenarios the
                 raw verdict above is "failure" by design — this chip
                 makes it obvious whether that failure is scenario-
                 expected or a real deviation. Uses the rubric's
                 verdict_check.matches_expectation, not the raw verdict. -->
            <a-tag
              v-if="scenarioMatched === true"
              color="green"
              :bordered="false"
            >
              ✓ {{ $t('autonomous.scenarioExpected') }}
            </a-tag>
            <a-tag
              v-else-if="scenarioMatched === false"
              color="red"
              :bordered="false"
            >
              ✗ {{ $t('autonomous.scenarioMismatch') }}
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
          <template #extra>
            <a-tag color="purple">{{ $t('autonomous.badgeProjectLlmAgent') }}</a-tag>
          </template>
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
                  <a-button size="small" @click="copyThinking">
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
          <template #extra>
            <a-tag color="blue">{{ $t('autonomous.badgeProjectCodeSpec') }}</a-tag>
          </template>
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
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { message } from 'ant-design-vue';
import { verdictColor, confidenceColor } from '@/utils/autonomousDisplay';

interface SelfAssessmentShape {
  verdict?: string;
  summary?: string;
  final_url?: string;
  final_title?: string;
}

interface SupervisorShape {
  verdict?: string;
  confidence?: string;
  summary?: string;
  anomalies?: string[];
  suggestions?: string[];
  _thinking?: string;
  _model?: string;
}

interface ScorecardBlockShape {
  score?: number;
}

interface VerdictCheckShape {
  matches_expectation?: boolean;
}

interface ScorecardShape {
  element_recognition?: ScorecardBlockShape;
  action_coverage?: ScorecardBlockShape;
  verdict_accuracy?: ScorecardBlockShape;
  distraction_avoidance?: ScorecardBlockShape;
  supervisor_agreement?: ScorecardBlockShape;
  verdict_check?: VerdictCheckShape;
  [key: string]: unknown;
}

const props = defineProps<{
  selfAssessment: SelfAssessmentShape | null;
  supervisor: SupervisorShape | null;
  scorecard: ScorecardShape | null;
}>();

const scenarioMatched = computed<boolean | null>(() => {
  const vc = props.scorecard?.verdict_check;
  if (!vc || typeof vc.matches_expectation !== 'boolean') return null;
  return vc.matches_expectation;
});

const { t } = useI18n();

const scoreMetrics = computed(() => {
  if (!props.scorecard) return [];
  const sc = props.scorecard;
  return [
    { key: 'element_recognition', label: t('autonomous.scoreElementRecognition'),
      score: sc.element_recognition?.score ?? 0 },
    { key: 'action_coverage', label: t('autonomous.scoreActionCoverage'),
      score: sc.action_coverage?.score ?? 0 },
    { key: 'verdict_accuracy', label: t('autonomous.scoreVerdictAccuracy'),
      score: sc.verdict_accuracy?.score ?? 0 },
    { key: 'distraction_avoidance', label: t('autonomous.scoreDistractionAvoidance'),
      score: sc.distraction_avoidance?.score ?? 0 },
    { key: 'supervisor_agreement', label: t('autonomous.scoreSupervisorAgreement'),
      score: sc.supervisor_agreement?.score ?? 0 },
  ];
});

async function copyThinking(): Promise<void> {
  const text = props.supervisor?._thinking;
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    message.success(t('autonomous.copied'));
  } catch (err) {
    message.error(t('autonomous.copyFailed') + (err as Error).message);
  }
}
</script>

<style scoped>
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
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
}
.score-label {
  flex: 0 0 140px;
  font-size: 12px;
  color: #595959;
}
.raw {
  font-size: 11px;
  max-height: 240px;
  overflow: auto;
  background: #fafafa;
  padding: 6px;
  border-radius: 4px;
}
.thinking-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.thinking-model {
  color: #8c8c8c;
  font-size: 12px;
}
.thinking-text {
  background: #fafafa;
  padding: 8px;
  border-radius: 4px;
  max-height: 320px;
  overflow: auto;
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
