<template>
  <a-card
    v-if="analysis"
    :title="$t('autonomous.pageAnalysis')"
    class="analysis-card"
    :bordered="false"
  >
    <template #extra>
      <a-tag color="blue">{{ $t('autonomous.badgeProjectCodeAnalyzer') }}</a-tag>
    </template>
    <p class="source-note">{{ $t('autonomous.sourceAnalyzer') }}</p>

    <div class="counts">
      <a-tag color="cyan">{{ $t('autonomous.countFillable') }}: {{ analysis.counts?.fillable ?? 0 }}</a-tag>
      <a-tag color="green">{{ $t('autonomous.countSubmit') }}: {{ analysis.counts?.submit ?? 0 }}</a-tag>
      <a-tag>{{ $t('autonomous.countClickable') }}: {{ analysis.counts?.clickable ?? 0 }}</a-tag>
      <a-tag>{{ $t('autonomous.countNavigation') }}: {{ analysis.counts?.navigation ?? 0 }}</a-tag>
      <a-tag color="purple">{{ $t('autonomous.countToggle') }}: {{ analysis.counts?.toggle ?? 0 }}</a-tag>
      <a-tag>{{ $t('autonomous.countSelect') }}: {{ analysis.counts?.select ?? 0 }}</a-tag>
      <a-tag>{{ $t('autonomous.countOther') }}: {{ analysis.counts?.other ?? 0 }}</a-tag>
      <a-tag>{{ $t('autonomous.countHidden') }}: {{ analysis.total_hidden ?? 0 }}</a-tag>
    </div>

    <a-row :gutter="16" style="margin-top: 12px">
      <a-col :xs="24" :md="16">
        <h4>{{ $t('autonomous.elementsVisible') }}</h4>
        <div
          v-for="(bucket, name) in groupedElements"
          :key="name"
          class="bucket"
        >
          <strong>{{ bucketLabel(name) }} ({{ bucket.length }}):</strong>
          <ul>
            <li
              v-for="el in bucket"
              :key="(el.selector || '') + (el.id || '')"
              class="el-item"
            >
              <div class="el-primary">
                <code>{{ el.selector }}</code>
                — <code>&lt;{{ el.tag }}{{ el.element_type ? ` type="${el.element_type}"` : '' }}&gt;</code>
              </div>
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
          <li
            v-for="act in analysis.recommended_actions"
            :key="act.step"
          >
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
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  bucketLabel,
  groupElementsByBucket,
  toScreenshotUrl,
} from '@/utils/autonomousDisplay';

// The element list rows each render the same attribute set — id,
// name, placeholder, aria_label, semantic_role, text, content_hint,
// label_text, label_source, reason, selector, tag, element_type.
// Typed loosely because both the live SSE workbench and the stored
// history snapshot land here with slightly different extras.
interface ElementShape {
  selector?: string;
  id?: string;
  name?: string;
  tag?: string;
  element_type?: string | null;
  role?: string;
  placeholder?: string;
  aria_label?: string;
  text?: string;
  semantic_role?: string | null;
  label_text?: string | null;
  label_source?: string | null;
  content_hint?: string | null;
  reason?: string;
}

interface AnalysisShape {
  counts?: Record<string, number>;
  total_hidden?: number;
  screenshot_ref?: string | null;
  recommended_actions?: Array<{
    step?: number;
    action_type: string;
    target_selector?: string;
    value?: string | null;
    reason?: string;
  }>;
  [bucket: string]: unknown;
}

const props = defineProps<{
  analysis: AnalysisShape | null;
}>();

const groupedElements = computed(
  () => groupElementsByBucket(props.analysis) as Record<string, ElementShape[]>,
);
</script>

<style scoped>
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
</style>
