<template>
  <div class="page">
    <header class="header">
      <h2>User Directory</h2>
      <span class="hint">{{ loading ? 'Loading…' : `${total} user(s)` }}</span>
    </header>

    <!-- Search form. Grouped by "common" (always-visible text + select +
         radio) and "advanced" (pickers + Cascader + Tag) so users can
         skim it. Both groups submit through the same Search / Reset
         buttons at the bottom. -->
    <a-form
      id="user-search-form"
      layout="horizontal"
      :label-col="{ span: 6 }"
      :wrapper-col="{ span: 18 }"
      class="search-form"
    >
      <a-row :gutter="16">
        <a-col :xs="24" :md="12">
          <a-form-item label="Name">
            <a-input
              id="search-name"
              v-model:value="form.name"
              placeholder="e.g. alice"
              allow-clear
            />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-form-item label="Email">
            <a-input
              id="search-email"
              v-model:value="form.email"
              placeholder="Substring of email"
              allow-clear
            />
          </a-form-item>
        </a-col>

        <a-col :xs="24" :md="12">
          <a-form-item label="Role">
            <a-select
              id="search-role"
              v-model:value="form.role"
              placeholder="Any role"
              allow-clear
              :options="roleOptions"
            />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-form-item label="Status">
            <a-radio-group
              id="search-status"
              v-model:value="form.status"
            >
              <a-radio value="">All</a-radio>
              <a-radio value="active">Active</a-radio>
              <a-radio value="disabled">Disabled</a-radio>
            </a-radio-group>
          </a-form-item>
        </a-col>

        <a-col :xs="24" :md="12">
          <a-form-item label="Registered (from)">
            <a-date-picker
              id="search-registered-from"
              v-model:value="form.registeredFrom"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-form-item label="Registered (to)">
            <a-date-picker
              id="search-registered-to"
              v-model:value="form.registeredTo"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </a-form-item>
        </a-col>

        <a-col :xs="24" :md="12">
          <a-form-item label="Region">
            <a-cascader
              id="search-region"
              v-model:value="form.region"
              :options="regionOptions"
              placeholder="Country / Province / City"
              change-on-select
            />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-form-item label="Registered range">
            <a-range-picker
              id="search-registered-range"
              v-model:value="form.registeredRange"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </a-form-item>
        </a-col>

        <a-col :xs="24" :md="12">
          <a-form-item label="Month">
            <a-month-picker
              id="search-month"
              v-model:value="form.month"
              value-format="YYYY-MM"
              style="width: 100%"
              placeholder="Month (advisory)"
            />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-form-item label="Cut-off time">
            <a-time-picker
              id="search-time"
              v-model:value="form.time"
              value-format="HH:mm"
              style="width: 100%"
              placeholder="Time (advisory)"
            />
          </a-form-item>
        </a-col>

        <a-col :span="24">
          <a-form-item label="Department">
            <!-- Tag-as-filter toggle group. A third distraction type:
                 looks like a read-only label cluster but actually
                 toggles state on click. -->
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

      <a-row>
        <a-col :span="24" style="text-align: right">
          <a-space>
            <!-- Primary action. The planner must pick this as the
                 submit, NOT one of the View buttons in the table and
                 NOT Reset below. -->
            <a-button
              id="btn-search"
              type="primary"
              html-type="submit"
              :loading="loading"
              @click="onSearch"
            >
              Search
            </a-button>
            <!-- Distraction button: same-size secondary, resets state,
                 should never be clicked during a filter flow. -->
            <a-button id="btn-reset" @click="onReset">Reset</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-form>

    <!-- Table with column sort + column filter on Role, plus a
         per-row View action button. -->
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
            {{ record.status }}
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
            View
          </a-button>
        </template>
      </template>
    </a-table>

    <!-- Detail panel (appears after clicking View on a row). Rendered
         inline rather than as a popup so the analyzer can see it. -->
    <section v-if="detail" class="detail" data-testid="user-detail">
      <h3>{{ detail.name }} — {{ detail.email }}</h3>
      <dl>
        <dt>Role</dt><dd>{{ detail.role }}</dd>
        <dt>Status</dt><dd>{{ detail.status }}</dd>
        <dt>Department</dt><dd>{{ detail.department }}</dd>
        <dt>Region</dt><dd>{{ detail.region }}</dd>
        <dt>Registered at</dt><dd>{{ detail.registered_at }}</dd>
        <dt>Last login</dt><dd>{{ detail.last_login_at }}</dd>
      </dl>
      <a-button size="small" @click="detail = null">Close</a-button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';

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
  time: '' as string | undefined,
  departments: [] as string[],
});

// ─── Table columns ───────────────────────────────────────────
// Sort and column-filter are intentionally real Ant Design table
// features so the analyzer sees them in the DOM (a column header
// that opens a filter menu is exactly the popup-style behaviour
// deferred to Phase 10).

const columns = [
  {
    title: 'ID',
    dataIndex: 'id',
    key: 'id',
    sorter: (a: User, b: User) => a.id - b.id,
    width: 80,
  },
  {
    title: 'Name',
    dataIndex: 'name',
    key: 'name',
    sorter: (a: User, b: User) => a.name.localeCompare(b.name),
  },
  { title: 'Email', dataIndex: 'email', key: 'email' },
  {
    title: 'Role',
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
  { title: 'Status', dataIndex: 'status', key: 'status' },
  {
    title: 'Registered',
    dataIndex: 'registered_at',
    key: 'registered_at',
    sorter: (a: User, b: User) =>
      a.registered_at.localeCompare(b.registered_at),
  },
  { title: 'Department', dataIndex: 'department', key: 'department' },
  { title: 'Actions', key: 'actions', width: 100 },
];

// ─── Messages ────────────────────────────────────────────────

const emptyText = ref('Loading…');

function setEmpty(message: string) {
  emptyText.value = message;
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
  if (form.departments.length > 0) {
    // Backend doesn't filter by department today (Phase 10 will add
    // it); sending it so the request still appears in network logs.
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
  setEmpty('Loading…');
  try {
    const params = buildParams();
    const res = await axios.get('/validation-api/users', { params });
    const data = res.data?.data;
    rows.value = data?.items ?? [];
    total.value = data?.total ?? 0;
    if (rows.value.length === 0) {
      setEmpty('No users found');
    }
  } catch (err) {
    console.error('Failed to fetch users', err);
    rows.value = [];
    total.value = 0;
    setEmpty('Request failed');
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
  form.time = '';
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

  await fetchUsers();
});
</script>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}
.header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 16px;
}
.hint {
  color: #8c8c8c;
  font-size: 12px;
}
.search-form {
  background: #fafafa;
  padding: 16px;
  border-radius: 4px;
  margin-bottom: 16px;
}
.tag-filter {
  cursor: pointer;
  user-select: none;
  margin-right: 4px;
  margin-bottom: 4px;
}
.user-table {
  background: #fff;
  border-radius: 4px;
}
.detail {
  margin-top: 16px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}
.detail dl {
  display: grid;
  grid-template-columns: 140px 1fr;
  row-gap: 4px;
  margin: 8px 0;
}
.detail dt {
  color: #8c8c8c;
  font-size: 12px;
}
.detail dd {
  margin: 0;
  font-size: 13px;
}
</style>
