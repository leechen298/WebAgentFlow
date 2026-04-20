<template>
  <div class="home-page">
    <a-card :bordered="false" class="hero">
      <h2 class="hero-title">{{ $t('home.title') }}</h2>
      <p class="hero-subtitle">{{ $t('home.subtitle') }}</p>
      <a-tag color="blue" class="phase-tag">{{ $t('home.phaseNotice') }}</a-tag>
    </a-card>

    <a-row :gutter="16" class="entries">
      <a-col :xs="24" :md="12">
        <a-card hoverable class="entry-card" @click="goWorkbench">
          <thunderbolt-outlined class="entry-icon" />
          <div class="entry-title">{{ $t('home.entryWorkbench') }}</div>
          <div class="entry-desc">{{ $t('home.entryWorkbenchDesc') }}</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :md="12">
        <a-card hoverable class="entry-card" @click="goHistory">
          <history-outlined class="entry-icon" />
          <div class="entry-title">{{ $t('home.entryHistory') }}</div>
          <div class="entry-desc">{{ $t('home.entryHistoryDesc') }}</div>
        </a-card>
      </a-col>
    </a-row>

    <a-card :bordered="false" class="recent" :title="$t('home.recentRuns')">
      <template #extra>
        <a-button size="small" type="link" @click="refresh" :loading="loading">
          <sync-outlined :spin="loading" />
          {{ $t('common.refresh') }}
        </a-button>
      </template>
      <a-empty v-if="!loading && runs.length === 0" :description="$t('home.recentRunsEmpty')" />
      <a-list v-else :data-source="runs" :loading="loading" size="small">
        <template #renderItem="{ item }">
          <a-list-item class="run-row" @click="openRun(item)">
            <div class="run-line">
              <a-tag :color="rowColor(item)">{{ rowStatusLabel(item) }}</a-tag>
              <span class="run-spec">{{ item.spec_id || '—' }}</span>
              <span class="run-sep">/</span>
              <span class="run-scenario">{{ item.scenario || '—' }}</span>
              <span class="run-time">{{ formatTime(item.created_at) }}</span>
            </div>
          </a-list-item>
        </template>
      </a-list>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import {
  HistoryOutlined,
  SyncOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue';
import { listAutonomousRuns, type AutonomousRunSummary } from '@/api/exploration';
import {
  effectiveStatus,
  effectiveStatusColor,
  type EffectiveStatus,
} from '@/utils/autonomousDisplay';
import { useI18n } from 'vue-i18n';

const router = useRouter();
const { t } = useI18n();

const runs = ref<AutonomousRunSummary[]>([]);
const loading = ref(false);

async function refresh() {
  loading.value = true;
  try {
    const page = await listAutonomousRuns({ limit: 5 });
    runs.value = page.items;
  } catch {
    // Non-fatal on the landing page — if the API is down the recent-runs
    // card just renders empty; the System Status badge in MainLayout is
    // the authoritative connectivity indicator.
    message.error(t('home.loadRunsFailed'));
  } finally {
    loading.value = false;
  }
}

function goWorkbench() {
  void router.push('/exploration/autonomous');
}

function goHistory() {
  void router.push('/exploration/autonomous/history');
}

function openRun(item: AutonomousRunSummary) {
  void router.push(`/exploration/autonomous/history/${item.run_id}`);
}

function statusFor(item: AutonomousRunSummary): EffectiveStatus {
  return effectiveStatus({
    verdict: item.verdict,
    scenarioMatched: item.scenario_matched,
    passGateStatus: item.pass_gate_status,
  });
}

function rowColor(item: AutonomousRunSummary): string {
  return effectiveStatusColor(statusFor(item));
}

function rowStatusLabel(item: AutonomousRunSummary): string {
  const s = statusFor(item);
  if (!s) return t('status.pending');
  const suffix = s.charAt(0).toUpperCase() + s.slice(1);
  return t(`autonomousHistory.status${suffix}`);
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

onMounted(() => {
  void refresh();
});

defineExpose({ refresh });
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero {
  background: linear-gradient(135deg, #102a43 0%, #1f7a8c 100%);
  color: #fff;
}

.hero :deep(.ant-card-body) {
  color: #fff;
}

.hero-title {
  color: #fff;
  font-size: 24px;
  margin: 0 0 8px;
}

.hero-subtitle {
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  margin: 0 0 12px;
  max-width: 640px;
}

.phase-tag {
  background: rgba(255, 255, 255, 0.18);
  border-color: transparent;
  color: #fff;
}

.entries .entry-card {
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.entries .entry-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.entry-icon {
  font-size: 28px;
  color: #1f7a8c;
  margin-bottom: 8px;
}

.entry-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 4px;
}

.entry-desc {
  font-size: 13px;
  color: #595959;
}

.run-row {
  cursor: pointer;
}

.run-row:hover {
  background: #fafafa;
}

.run-line {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  font-size: 13px;
}

.run-spec {
  font-weight: 500;
  color: #262626;
}

.run-sep {
  color: #bfbfbf;
}

.run-scenario {
  color: #595959;
}

.run-time {
  margin-left: auto;
  color: #8c8c8c;
  font-size: 12px;
}
</style>
