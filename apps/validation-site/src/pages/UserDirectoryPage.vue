<template>
  <div class="directory-page">
    <header class="header">
      <h2>{{ t('users.title') }}</h2>
      <span class="hint">{{ countLabel }}</span>
    </header>

    <!-- Search card: all filters live here. Vertical form layout so
         labels sit above inputs and the grid stays clean across
         resolutions. Buttons pinned to the card footer, right-aligned. -->
    <a-card :title="t('users.searchCardTitle')" class="search-card" :bordered="false">
      <a-form
        id="user-search-form"
        layout="vertical"
      >
        <a-row :gutter="16">
          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.name')">
              <a-input
                id="search-name"
                v-model:value="form.name"
                :placeholder="t('users.placeholders.name')"
                allow-clear
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.email')">
              <a-input
                id="search-email"
                v-model:value="form.email"
                :placeholder="t('users.placeholders.email')"
                allow-clear
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.role')">
              <a-select
                id="search-role"
                v-model:value="form.role"
                :placeholder="t('users.placeholders.anyRole')"
                allow-clear
                :options="roleOptions"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.status')">
              <a-radio-group id="search-status" v-model:value="form.status">
                <a-radio value="">{{ t('users.statusAll') }}</a-radio>
                <a-radio value="active">{{ t('users.statusActive') }}</a-radio>
                <a-radio value="disabled">{{ t('users.statusDisabled') }}</a-radio>
              </a-radio-group>
            </a-form-item>
          </a-col>

          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.registeredFrom')">
              <a-date-picker
                id="search-registered-from"
                v-model:value="form.registeredFrom"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.registeredTo')">
              <a-date-picker
                id="search-registered-to"
                v-model:value="form.registeredTo"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.region')">
              <a-cascader
                id="search-region"
                v-model:value="form.region"
                :options="regionOptions"
                :placeholder="t('users.placeholders.region')"
                change-on-select
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.registeredRange')">
              <a-range-picker
                id="search-registered-range"
                v-model:value="form.registeredRange"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :sm="12" :lg="8">
            <a-form-item :label="t('users.fields.month')">
              <a-month-picker
                id="search-month"
                v-model:value="form.month"
                value-format="YYYY-MM"
                style="width: 100%"
                :placeholder="t('users.placeholders.month')"
              />
            </a-form-item>
          </a-col>

          <!-- Tag-as-filter row spans the full width because the
               click-to-toggle interaction is visually different from
               the other inputs and wants its own breathing room. -->
          <a-col :span="24">
            <a-form-item :label="t('users.fields.department')">
              <a-tag
                v-for="opt in departmentOptions"
                :key="opt"
                :color="form.departments.includes(opt) ? 'blue' : 'default'"
                class="tag-filter"
                @click="toggleDepartment(opt)"
              >
                {{ opt }}
              </a-tag>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>

      <template #actions>
        <div class="card-actions">
          <a-space>
            <a-button id="btn-reset" @click="onReset">
              {{ t('users.actionReset') }}
            </a-button>
            <a-button
              id="btn-search"
              type="primary"
              html-type="submit"
              :loading="loading"
              @click="onSearch"
            >
              {{ t('users.actionSearch') }}
            </a-button>
          </a-space>
        </div>
      </template>
    </a-card>

    <!-- Result card: the table always follows the filter card, so the
         top-to-bottom reading order is "filters → results". -->
    <a-card
      :title="t('users.resultCardTitle')"
      class="result-card"
      :bordered="false"
    >
      <template #extra>
        <span class="result-meta">{{ countLabel }}</span>
      </template>

      <a-table
        :columns="columns"
        :data-source="rows"
        :pagination="false"
        :loading="loading"
        row-key="id"
        size="middle"
        :locale="{ emptyText: emptyText }"
        class="user-table"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'active' ? 'green' : 'red'">
              {{ record.status === 'active'
                ? t('users.statusActive')
                : t('users.statusDisabled') }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'actions'">
            <!-- Per-row button. Planner should NOT pick this when the
                 request is "search users" — View operates on a single
                 row, not on the filter. -->
            <a-button
              type="link"
              size="small"
              :data-user-id="record.id"
              class="btn-view-row"
              @click="onView(record)"
            >
              {{ t('users.actionView') }}
            </a-button>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Detail panel (appears after clicking View on a row). Rendered
         inline rather than as a popup so the analyzer can see it. -->
    <a-card
      v-if="detail"
      class="detail-card"
      :bordered="false"
      data-testid="user-detail"
    >
      <template #title>
        <span>{{ detail.name }}</span>
        <span class="detail-sep"> · </span>
        <span>{{ detail.email }}</span>
      </template>
      <template #extra>
        <a-button size="small" @click="detail = null">
          {{ t('users.detail.close') }}
        </a-button>
      </template>
      <dl>
        <dt>{{ t('users.detail.role') }}</dt><dd>{{ detail.role }}</dd>
        <dt>{{ t('users.detail.status') }}</dt><dd>{{ detail.status }}</dd>
        <dt>{{ t('users.detail.department') }}</dt><dd>{{ detail.department }}</dd>
        <dt>{{ t('users.detail.region') }}</dt><dd>{{ detail.region }}</dd>
        <dt>{{ t('users.detail.registeredAt') }}</dt><dd>{{ detail.registered_at }}</dd>
        <dt>{{ t('users.detail.lastLogin') }}</dt><dd>{{ detail.last_login_at }}</dd>
      </dl>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import axios from 'axios';

const { t } = useI18n();

interface User {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
  status: 'active' | 'disabled';
  registered_at: string;
  region: string;
  department: string;
  last_login_at: string;
}

interface RegionOption {
  value: string;
  label: string;
  children?: RegionOption[];
}

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const rows = ref<User[]>([]);
const total = ref(0);
const detail = ref<User | null>(null);

const roleOptions = ref<{ value: string; label: string }[]>([]);
const departmentOptions = ref<string[]>([]);
const regionOptions = ref<RegionOption[]>([]);

const form = reactive({
  name: '',
  email: '',
  role: undefined as string | undefined,
  status: '',
  registeredFrom: '' as string | undefined,
  registeredTo: '' as string | undefined,
  registeredRange: [] as string[],
  region: [] as string[],
  month: '' as string | undefined,
  departments: [] as string[],
});

const countLabel = computed(() => {
  if (loading.value) return t('users.loading');
  return total.value === 1
    ? t('users.countOne', { n: total.value })
    : t('users.countMany', { n: total.value });
});

// ─── Table columns ───────────────────────────────────────────
// Sort and column-filter are intentionally real Ant Design table
// features so the analyzer sees them in the DOM (a column header
// that opens a filter menu is exactly the popup-style behaviour
// deferred to Phase 10).

const columns = computed(() => [
  {
    title: t('users.columns.id'),
    dataIndex: 'id',
    key: 'id',
    sorter: (a: User, b: User) => a.id - b.id,
    width: 80,
  },
  {
    title: t('users.columns.name'),
    dataIndex: 'name',
    key: 'name',
    sorter: (a: User, b: User) => a.name.localeCompare(b.name),
  },
  { title: t('users.columns.email'), dataIndex: 'email', key: 'email' },
  {
    title: t('users.columns.role'),
    dataIndex: 'role',
    key: 'role',
    filters: [
      { text: 'admin', value: 'admin' },
      { text: 'user', value: 'user' },
      { text: 'guest', value: 'guest' },
    ],
    onFilter: (value: string | number | boolean, record: User) =>
      record.role === value,
  },
  { title: t('users.columns.status'), dataIndex: 'status', key: 'status' },
  {
    title: t('users.columns.registered'),
    dataIndex: 'registered_at',
    key: 'registered_at',
    sorter: (a: User, b: User) =>
      a.registered_at.localeCompare(b.registered_at),
  },
  { title: t('users.columns.department'), dataIndex: 'department', key: 'department' },
  { title: t('users.columns.actions'), key: 'actions', width: 100 },
]);

// ─── Empty-state text ────────────────────────────────────────
// Tracked as ref because the table's `locale.emptyText` reads it
// directly; if we pushed translations through i18n via a computed
// the table wouldn't update the message on state transitions the
// way we want (Loading → No users found → Request failed).
const emptyText = ref(t('users.emptyLoading'));

function setEmpty(key: 'emptyLoading' | 'emptyNoMatch' | 'emptyRequestFailed') {
  emptyText.value = t(`users.${key}`);
}

// ─── Remote calls ────────────────────────────────────────────

async function loadOptions() {
  try {
    const res = await axios.get('/validation-api/users/meta/options');
    const data = res.data?.data;
    if (data) {
      roleOptions.value = data.roles.map((r: string) => ({ value: r, label: r }));
      departmentOptions.value = data.departments;
      regionOptions.value = data.regions;
    }
  } catch (err) {
    console.error('Failed to load options', err);
  }
}

// Derive a query object from form. Empty strings are dropped so the
// backend only sees filters the user actually set.
function buildParams(): Record<string, string> {
  const params: Record<string, string> = {};
  if (form.name) params.name = form.name;
  if (form.email) params.email = form.email;
  if (form.role) params.role = form.role;
  if (form.status) params.status = form.status;

  // Prefer explicit range picker if set, otherwise individual from/to.
  if (form.registeredRange.length === 2) {
    if (form.registeredRange[0]) params.registered_from = form.registeredRange[0];
    if (form.registeredRange[1]) params.registered_to = form.registeredRange[1];
  } else {
    if (form.registeredFrom) params.registered_from = form.registeredFrom;
    if (form.registeredTo) params.registered_to = form.registeredTo;
  }

  if (form.region.length > 0) {
    params.region_prefix = form.region.join('/');
  }
  if (form.month) {
    params.month = form.month;
  }
  if (form.departments.length > 0) {
    params.department = form.departments.join(',');
  }
  return params;
}

function syncUrl() {
  router.replace({ path: '/users', query: buildParams() }).catch(() => {
    /* vue-router rejects identical navigations — ignore. */
  });
}

async function fetchUsers() {
  loading.value = true;
  setEmpty('emptyLoading');
  try {
    const params = buildParams();
    const res = await axios.get('/validation-api/users', { params });
    const data = res.data?.data;
    rows.value = data?.items ?? [];
    total.value = data?.total ?? 0;
    if (rows.value.length === 0) {
      setEmpty('emptyNoMatch');
    }
  } catch (err) {
    console.error('Failed to fetch users', err);
    rows.value = [];
    total.value = 0;
    setEmpty('emptyRequestFailed');
  } finally {
    loading.value = false;
  }
}

// ─── Handlers ────────────────────────────────────────────────

function onSearch() {
  detail.value = null;
  syncUrl();
  fetchUsers();
}

function onReset() {
  form.name = '';
  form.email = '';
  form.role = undefined;
  form.status = '';
  form.registeredFrom = '';
  form.registeredTo = '';
  form.registeredRange = [];
  form.region = [];
  form.month = '';
  form.departments = [];
  detail.value = null;
  syncUrl();
  fetchUsers();
}

function toggleDepartment(d: string) {
  const i = form.departments.indexOf(d);
  if (i >= 0) form.departments.splice(i, 1);
  else form.departments.push(d);
}

async function onView(row: User) {
  try {
    const res = await axios.get(`/validation-api/users/${row.id}`);
    detail.value = res.data?.data ?? row;
  } catch {
    detail.value = row;
  }
}

// ─── Bootstrap ───────────────────────────────────────────────

onMounted(async () => {
  await loadOptions();

  // Restore form from URL query so autonomous runs that land on
  // /users?name=alice reproduce the same filter as the operator would.
  const q = route.query;
  if (typeof q.name === 'string') form.name = q.name;
  if (typeof q.email === 'string') form.email = q.email;
  if (typeof q.role === 'string') form.role = q.role;
  if (typeof q.status === 'string') form.status = q.status;
  if (typeof q.registered_from === 'string') form.registeredFrom = q.registered_from;
  if (typeof q.registered_to === 'string') form.registeredTo = q.registered_to;
  if (typeof q.region_prefix === 'string') form.region = q.region_prefix.split('/');
  if (typeof q.month === 'string') form.month = q.month;
  if (typeof q.department === 'string') {
    form.departments = q.department.split(',').filter(Boolean);
  }

  await fetchUsers();
});
</script>

<style scoped>
/* Intentionally NOT using .page — that class is defined unscoped in
   global.css for the single-centered-card login layout, and Vue's
   scoped styles only override per-property (so un-set properties
   like `display: flex` from the global rule would still cascade).
   .directory-page is unique to this page and safe from cascade. */
.directory-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 24px 48px;
}
.header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 16px;
}
.header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.hint {
  color: #8c8c8c;
  font-size: 12px;
}
.search-card {
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}
.card-actions {
  text-align: right;
  padding: 0 8px;
}
.result-card {
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}
.result-meta {
  color: #8c8c8c;
  font-size: 12px;
}
.tag-filter {
  cursor: pointer;
  user-select: none;
  margin-right: 4px;
  margin-bottom: 4px;
}
.detail-card {
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.detail-sep {
  color: #bfbfbf;
  margin: 0 4px;
}
.detail-card dl {
  display: grid;
  grid-template-columns: 140px 1fr;
  row-gap: 6px;
  margin: 0;
}
.detail-card dt {
  color: #8c8c8c;
  font-size: 12px;
}
.detail-card dd {
  margin: 0;
  font-size: 13px;
}
</style>
