<template>
  <div class="fixture-inner">
    <div class="search-controls">
      <div class="field inline">
        <input v-model="query" type="text" data-testid="basic-search-query" :disabled="loading" />
        <select v-model="categoryFilter" data-testid="basic-search-category-filter" :disabled="loading">
          <option value="all">{{ t('runtimeFixtures.search.filterAll') }}</option>
          <option value="alpha">{{ t('runtimeFixtures.search.filterAlpha') }}</option>
          <option value="beta">{{ t('runtimeFixtures.search.filterBeta') }}</option>
        </select>
        <button
          class="btn btn-primary"
          data-testid="basic-fixture-primary-trigger"
          :disabled="loading"
          @click="onSearch"
        >
          {{ t('runtimeFixtures.search.submit') }}
        </button>
        <button
          class="btn btn-secondary"
          data-testid="basic-search-clear-filters"
          :disabled="loading"
          @click="onClear"
        >
          {{ t('runtimeFixtures.search.clear') }}
        </button>
      </div>
    </div>

    <div class="secondary-actions" data-testid="basic-fixture-secondary-trigger">
      <button class="btn btn-secondary" data-testid="basic-search-secondary-action" @click="onSaved">
        {{ t('runtimeFixtures.search.savedSearches') }}
      </button>
    </div>

    <div v-if="loading" class="loading" data-testid="basic-search-loading">
      {{ t('runtimeFixtures.search.loading') }}
    </div>

    <div v-else-if="results.length > 0" class="results" data-testid="basic-search-result-list">
      <div class="result-count" data-testid="basic-search-result-count">
        {{ t('runtimeFixtures.search.resultCount', { n: results.length }) }}
      </div>
      <ul>
        <li v-for="(item, idx) in results" :key="idx">
          <strong>{{ item.name }}</strong> — {{ item.category }} — {{ item.status }}
        </li>
      </ul>
    </div>

    <div v-else-if="searched" class="empty" data-testid="basic-search-empty">
      {{ t('runtimeFixtures.search.emptyResult') }}
    </div>

    <div v-if="hint" class="hint-surface">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useFixtureTimer } from '../useFixtureTimer';

const emit = defineEmits<{
  (e: 'update:status', v: 'idle' | 'loading' | 'success' | 'error'): void;
  (e: 'update:result', v: string): void;
}>();

defineExpose({ reset });

const { t } = useI18n();
const { setDelay, clearAll } = useFixtureTimer();

const DATASET = [
  { name: 'Alpha One', category: 'alpha', status: 'active' },
  { name: 'Alpha Two', category: 'alpha', status: 'pending' },
  { name: 'Beta One', category: 'beta', status: 'active' },
  { name: 'Beta Two', category: 'beta', status: 'disabled' },
  { name: 'Gamma One', category: 'alpha', status: 'active' },
];

const query = ref('');
const categoryFilter = ref('all');
const loading = ref(false);
const searched = ref(false);
const results = ref<typeof DATASET>([]);
const hint = ref('');

function reset() {
  clearAll();
  query.value = '';
  categoryFilter.value = 'all';
  loading.value = false;
  searched.value = false;
  results.value = [];
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onSearch() {
  clearAll();
  hint.value = '';
  loading.value = true;
  searched.value = true;
  results.value = [];
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    loading.value = false;
    if (query.value.trim().toLowerCase() === 'empty') {
      results.value = [];
      emit('update:status', 'idle');
      emit('update:result', t('runtimeFixtures.search.emptyResult'));
    } else {
      results.value = DATASET.filter((item) => {
        const matchesQuery = !query.value.trim() || item.name.toLowerCase().includes(query.value.trim().toLowerCase());
        const matchesCategory = categoryFilter.value === 'all' || item.category === categoryFilter.value;
        return matchesQuery && matchesCategory;
      });
      if (results.value.length > 0) {
        emit('update:status', 'success');
        emit('update:result', t('runtimeFixtures.search.resultCount', { n: results.value.length }));
      } else {
        emit('update:status', 'idle');
        emit('update:result', t('runtimeFixtures.search.emptyResult'));
      }
    }
  });
}

function onClear() {
  clearAll();
  query.value = '';
  categoryFilter.value = 'all';
  loading.value = false;
  searched.value = false;
  results.value = [];
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onSaved() {
  hint.value = t('runtimeFixtures.search.savedHint');
}
</script>

<style scoped>
.fixture-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-controls .field.inline {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-controls input[type='text'] {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  min-width: 180px;
}

.search-controls select {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.secondary-actions {
  display: flex;
  gap: 10px;
}

.loading,
.empty {
  padding: 12px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 13px;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-count {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.results ul {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 13px;
}

.results li {
  margin-bottom: 6px;
}

.hint-surface {
  padding: 10px 12px;
  border-radius: 6px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 13px;
}
</style>
