<template>
  <div>
    <a-row :gutter="16">
      <a-col :span="24">
        <a-card title="System Status" :bordered="false">
          <a-space direction="vertical" style="width: 100%">
            <a-alert
              :message="apiStatusMessage"
              :type="apiStatusType"
              :show-icon="true"
            />
            <a-row :gutter="16">
              <a-col :span="6">
                <a-statistic
                  title="Recordings"
                  :value="recordingsCount"
                  :loading="loading"
                >
                  <template #prefix>
                    <video-camera-outlined />
                  </template>
                </a-statistic>
              </a-col>
              <a-col :span="6">
                <a-statistic
                  title="Skills"
                  :value="skillsCount"
                  :loading="loading"
                >
                  <template #prefix>
                    <tool-outlined />
                  </template>
                </a-statistic>
              </a-col>
              <a-col :span="6">
                <a-statistic
                  title="Runs"
                  :value="runsCount"
                  :loading="loading"
                >
                  <template #prefix>
                    <play-circle-outlined />
                  </template>
                </a-statistic>
              </a-col>
              <a-col :span="6">
                <a-button type="primary" @click="refreshData" :loading="loading" style="margin-top: 24px">
                  <template #icon><sync-outlined :spin="loading" /></template>
                  Refresh
                </a-button>
              </a-col>
            </a-row>
          </a-space>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-top: 16px">
      <a-col :span="12">
        <a-card title="Quick Actions" :bordered="false">
          <a-space direction="vertical" style="width: 100%">
            <a-button type="primary" block @click="goToRecordings">
              <template #icon><plus-outlined /></template>
              Manage Recordings
            </a-button>
            <a-button type="default" block @click="goToSkills">
              <template #icon><plus-outlined /></template>
              Manage Skills
            </a-button>
            <a-button type="default" block @click="goToRuns">
              <template #icon><plus-outlined /></template>
              Manage Runs
            </a-button>
          </a-space>
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="About" :bordered="false">
          <p>WebAgentFlow engineering foundation is ready for subsequent feature work.</p>
          <a-divider />
          <h4>Included Apps</h4>
          <ul>
            <li>Console</li>
            <li>API</li>
            <li>Worker</li>
            <li>Extension</li>
          </ul>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import {
  VideoCameraOutlined,
  ToolOutlined,
  PlayCircleOutlined,
  SyncOutlined,
  PlusOutlined
} from '@ant-design/icons-vue';
import { useAppStore, useRecordingsStore, useSkillsStore, useRunsStore } from '@/stores';

const router = useRouter();
const appStore = useAppStore();
const recordingsStore = useRecordingsStore();
const skillsStore = useSkillsStore();
const runsStore = useRunsStore();

const loading = ref(false);

const apiStatusMessage = computed(() => {
  if (appStore.loading) return 'Checking API connectivity...';
  return appStore.apiConnected ? 'Backend API is connected and healthy' : 'Backend API is not reachable';
});

const apiStatusType = computed(() => {
  if (appStore.loading) return 'info';
  return appStore.apiConnected ? 'success' : 'error';
});

const recordingsCount = computed(() => recordingsStore.recordings.length);
const skillsCount = computed(() => skillsStore.skills.length);
const runsCount = computed(() => runsStore.runs.length);

async function refreshData(): Promise<void> {
  loading.value = true;
  try {
    await Promise.all([
      appStore.checkApiHealth(),
      recordingsStore.fetchRecordings().catch(() => {}),
      skillsStore.fetchSkills().catch(() => {}),
      runsStore.fetchRuns().catch(() => {})
    ]);
    message.success('Data refreshed');
  } catch (e) {
    message.error('Failed to refresh data');
  } finally {
    loading.value = false;
  }
}

function goToRecordings(): void {
  void router.push('/recordings');
}

function goToSkills(): void {
  void router.push('/skills');
}

function goToRuns(): void {
  void router.push('/runs');
}

onMounted(() => {
  void refreshData();
});
</script>
