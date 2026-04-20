<template>
  <a-card
    v-if="steps.length > 0"
    :title="$t('autonomous.timeline')"
    class="timeline-card"
    :bordered="false"
  >
    <template #extra>
      <a-tag color="blue">{{ $t('autonomous.badgeProjectCodeExplorer') }}</a-tag>
    </template>
    <p class="source-note">{{ $t('autonomous.sourceTimeline') }}</p>
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
          <div v-if="step.actual_value !== undefined && step.actual_value !== null">
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
</template>

<script setup lang="ts">
import { stepColor, toScreenshotUrl } from '@/utils/autonomousDisplay';

// Step rows share shape across live SSE events and saved snapshots.
// Extras like ``plan_reason`` / ``timestamp_ms`` are carried verbatim
// so the template can render them without a prop change later.
interface StepShape {
  step_index?: number;
  action_type?: string;
  ok?: boolean | null;
  target_description?: string;
  value?: string | null;
  actual_value?: string | null;
  url_changed?: boolean;
  url_after?: string;
  title_changed?: boolean;
  title_after?: string;
  error?: string;
  // Loose: live SSE emits this as Record<string, unknown>; stored
  // snapshots may shape it differently. Render-time we stringify.
  result_signals?: unknown;
  screenshot_ref?: string | null;
}

defineProps<{
  steps: StepShape[];
}>();
</script>

<style scoped>
.source-note {
  color: #8c8c8c;
  font-size: 12px;
  margin-top: -8px;
  margin-bottom: 12px;
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
.screenshot {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}
.screenshot-thumb {
  max-width: 400px;
  margin-top: 4px;
}
</style>
