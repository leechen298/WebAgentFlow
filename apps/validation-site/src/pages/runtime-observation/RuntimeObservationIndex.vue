<template>
  <main class="runtime-page" data-testid="runtime-observation-index">
    <header class="runtime-header">
      <router-link class="back-link" to="/" data-testid="runtime-observation-back">
        Back to validation site
      </router-link>
      <p class="eyebrow">M11.2.4.1</p>
      <h1 data-testid="runtime-observation-heading">Runtime Observation Fixtures</h1>
      <p class="summary">
        A shell for WebAgentFlow-owned fixture pages. This page exposes the route namespace,
        planned fixture metadata, reset rules, and stable anchor rules before concrete business
        fixtures land.
      </p>
    </header>

    <section class="boundary-strip" aria-label="Current observation boundary">
      <div>
        <h2>Current MVP observation signals</h2>
        <ul class="chip-list" data-testid="current-mvp-signals">
          <li v-for="signal in currentSignals" :key="signal">{{ signal }}</li>
        </ul>
      </div>
      <div>
        <h2>Current evidence capabilities</h2>
        <ul class="chip-list" data-testid="current-evidence-capabilities">
          <li v-for="capability in evidenceCapabilities" :key="capability">{{ capability }}</li>
        </ul>
      </div>
      <div>
        <h2>Future labels</h2>
        <ul class="chip-list future" data-testid="future-signal-labels">
          <li v-for="label in futureLabels" :key="label">{{ label }}</li>
        </ul>
      </div>
    </section>

    <nav class="category-nav" aria-label="Runtime observation categories" data-testid="category-navigation">
      <router-link
        class="category-link"
        :class="{ active: !activeCategoryId }"
        to="/runtime-observation"
      >
        All
      </router-link>
      <router-link
        v-for="category in routedCategories"
        :key="category.id"
        class="category-link"
        :class="{ active: activeCategoryId === category.id }"
        :to="category.route"
      >
        {{ category.title }}
      </router-link>
      <span class="category-link disabled" aria-disabled="true">
        Mock Backend Runtime Conditions
      </span>
    </nav>

    <section
      v-for="category in visibleCategories"
      :id="category.id"
      :key="category.id"
      class="category-section"
      :data-testid="`runtime-category-${category.id}`"
    >
      <div class="section-heading">
        <div>
          <p class="phase">{{ category.phase }}</p>
          <h2>{{ category.title }}</h2>
        </div>
        <span class="priority">{{ category.priority }}</span>
      </div>
      <p class="section-summary">{{ category.description }}</p>

      <div class="fixture-grid">
        <article
          v-for="fixture in category.fixtures"
          :key="fixture.fixture_id"
          class="fixture-card"
          :data-testid="`fixture-card-${fixture.fixture_id}`"
        >
          <div class="fixture-head">
            <h3>{{ fixture.title }}</h3>
            <span class="status" :class="fixture.status">{{ fixture.status }}</span>
          </div>
          <dl class="fixture-meta">
            <div>
              <dt>Fixture id</dt>
              <dd><code>{{ fixture.fixture_id }}</code></dd>
            </div>
            <div>
              <dt>Platform</dt>
              <dd>{{ fixture.platform }}</dd>
            </div>
            <div>
              <dt>Business complexity</dt>
              <dd><code>{{ fixture.business_complexity }}</code></dd>
            </div>
            <div>
              <dt>Route</dt>
              <dd><code>{{ fixture.route }}</code></dd>
            </div>
            <div>
              <dt>Runtime behaviors</dt>
              <dd>{{ fixture.runtime_behaviors.join(', ') }}</dd>
            </div>
            <div>
              <dt>Runtime conditions</dt>
              <dd>{{ fixture.runtime_conditions.join(', ') }}</dd>
            </div>
          </dl>
          <div class="observation-block">
            <h4>Current MVP expected observation</h4>
            <p>{{ fixture.current_mvp_expected_observation }}</p>
          </div>
          <div class="observation-block future-block">
            <h4>Future expected observation</h4>
            <p>{{ fixture.future_expected_observation }}</p>
          </div>
          <div class="fixture-actions">
            <router-link
              v-if="fixture.status === 'implemented'"
              class="btn btn-primary"
              :to="fixture.route"
              data-testid="fixture-card-link"
            >
              Open fixture
            </router-link>
            <p v-else class="planned-note">
              Planned fixture card only. No business fixture route is linked until implementation lands.
            </p>
          </div>
        </article>
      </div>
    </section>

    <section class="rules-layout" aria-label="Fixture implementation conventions">
      <div class="rule-block" data-testid="stable-anchor-convention">
        <h2>Stable anchor convention</h2>
        <ul>
          <li>Stable heading.</li>
          <li>Stable trigger element.</li>
          <li>Stable result region.</li>
          <li>Stable reset control.</li>
          <li>Stable status label.</li>
          <li><code>data-testid</code> or equivalent deterministic selector.</li>
        </ul>
      </div>
      <div class="rule-block" data-testid="reset-convention">
        <h2>Reset convention</h2>
        <ul>
          <li>Clear inputs and visible errors.</li>
          <li>Close modal, drawer, picker, toast, and alert surfaces.</li>
          <li>Restore initial enabled or disabled button state.</li>
          <li>Restore list seed data and visible status label.</li>
          <li>Stop pending timers before returning to the initial state.</li>
        </ul>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { BASIC_FIXTURES } from './basic/basicFixtures';

type BusinessComplexity =
  | 'simple_business_page'
  | 'medium_business_page'
  | 'complex_business_page'
  | 'very_complex_business_page';

type FixtureStatus = 'planned' | 'implemented' | 'tested' | 'deferred';

interface FixtureCard {
  fixture_id: string;
  title: string;
  platform: 'pc' | 'mobile';
  business_complexity: BusinessComplexity;
  page_type: string;
  route: string;
  phase: string;
  runtime_behaviors: string[];
  runtime_conditions: string[];
  current_mvp_expected_observation: string;
  future_expected_observation: string;
  status: FixtureStatus;
}

interface FixtureCategory {
  id: string;
  title: string;
  route?: string;
  phase: string;
  priority: string;
  description: string;
  fixtures: FixtureCard[];
}

type RoutedFixtureCategory = FixtureCategory & { route: string };

const route = useRoute();

const currentSignals = ['url_changed', 'title_changed', 'network_idle_observed supporting only'];
const evidenceCapabilities = ['wait_result', 'observation_summary'];
const futureLabels = [
  'toast_shown',
  'modal_opened',
  'loading_finished',
  'element_enabled',
  'element_disabled',
  'form_validation_message',
  'list_changed',
  'field_show_hide',
  'mode_switch',
  'component-generated runtime surface relation',
  'mobile picker / action sheet relation',
];

const categories: FixtureCategory[] = [
  {
    id: 'basic',
    title: 'Basic Business Pages',
    route: '/runtime-observation/basic',
    phase: '11.2.4.2',
    priority: 'PC priority',
    description:
      'Simple single-purpose pages that can be exercised with deterministic local state.',
    fixtures: BASIC_FIXTURES as FixtureCard[],
  },
  {
    id: 'medium',
    title: 'Medium Business Pages',
    route: '/runtime-observation/medium',
    phase: '11.2.4.3',
    priority: 'PC priority',
    description:
      'List, table, upload, and export pages that stay within one business object.',
    fixtures: [
      {
        fixture_id: 'medium-user-list',
        title: 'User list table operations',
        platform: 'pc',
        business_complexity: 'medium_business_page',
        page_type: 'user_list',
        route: '/runtime-observation/medium/user-list',
        phase: '11.2.4.3',
        runtime_behaviors: ['partial_list_refresh', 'click_to_drawer'],
        runtime_conditions: ['normal_network', 'empty_result', 'rate_limited_429'],
        current_mvp_expected_observation: 'URL or title changes only if the fixture navigates.',
        future_expected_observation: 'list_changed, modal_opened, and loading_finished.',
        status: 'planned',
      },
      {
        fixture_id: 'medium-file-upload',
        title: 'File upload planning surface',
        platform: 'pc',
        business_complexity: 'medium_business_page',
        page_type: 'file_upload',
        route: '/runtime-observation/medium/file-upload',
        phase: '11.2.4.3',
        runtime_behaviors: ['upload_progress', 'toast_error'],
        runtime_conditions: ['upload_file_type_rejected', 'upload_size_exceeded'],
        current_mvp_expected_observation: 'No current primary signal unless URL or title changes.',
        future_expected_observation: 'loading_finished, toast_shown, and form_validation_message.',
        status: 'planned',
      },
    ],
  },
  {
    id: 'complex',
    title: 'Complex Business Pages',
    route: '/runtime-observation/complex',
    phase: '11.2.4.4',
    priority: 'PC priority',
    description:
      'Single-page workflows with dynamic fields, mode switches, or multiple operation phases.',
    fixtures: [
      {
        fixture_id: 'complex-dynamic-form',
        title: 'Dynamic form fields',
        platform: 'pc',
        business_complexity: 'complex_business_page',
        page_type: 'dynamic_form',
        route: '/runtime-observation/complex/dynamic-form',
        phase: '11.2.4.4',
        runtime_behaviors: ['field_show_hide', 'input_to_validation_message'],
        runtime_conditions: ['backend_validation_error', 'conflict_409'],
        current_mvp_expected_observation: 'No current primary signal unless URL or title changes.',
        future_expected_observation: 'field_show_hide and form_validation_message.',
        status: 'planned',
      },
      {
        fixture_id: 'complex-view-edit-preview',
        title: 'View, edit, preview mode switch',
        platform: 'pc',
        business_complexity: 'complex_business_page',
        page_type: 'view_edit_preview_mode_switch',
        route: '/runtime-observation/complex/mode-switch',
        phase: '11.2.4.4',
        runtime_behaviors: ['mode_switch', 'click_to_modal'],
        runtime_conditions: ['normal_network', 'partial_success'],
        current_mvp_expected_observation: 'No current primary signal unless URL or title changes.',
        future_expected_observation: 'mode_switch and modal_opened.',
        status: 'planned',
      },
    ],
  },
  {
    id: 'mobile',
    title: 'Mobile Single-page Patterns',
    route: '/runtime-observation/mobile',
    phase: '11.2.4.6',
    priority: 'Later priority',
    description:
      'Mobile-only fixture categories are visible in the shell, but concrete mobile fixtures are deferred.',
    fixtures: [
      {
        fixture_id: 'mobile-picker',
        title: 'Mobile picker relation',
        platform: 'mobile',
        business_complexity: 'medium_business_page',
        page_type: 'mobile_picker',
        route: '/runtime-observation/mobile/picker',
        phase: '11.2.4.6',
        runtime_behaviors: ['mobile_picker', 'mobile_action_sheet'],
        runtime_conditions: ['normal_network', 'request_cancelled'],
        current_mvp_expected_observation: 'No current primary signal unless URL or title changes.',
        future_expected_observation: 'mobile picker / action sheet relation.',
        status: 'deferred',
      },
    ],
  },
  {
    id: 'mock-backend',
    title: 'Mock Backend Runtime Conditions',
    phase: '11.2.4.5',
    priority: 'Backend phase',
    description:
      'HTTP delay and error conditions are planned here, but no mock backend is connected in this shell.',
    fixtures: [
      {
        fixture_id: 'backend-slow-save',
        title: 'Slow save response',
        platform: 'pc',
        business_complexity: 'medium_business_page',
        page_type: 'create_edit_form',
        route: '/runtime-observation/backend/slow-save',
        phase: '11.2.4.5',
        runtime_behaviors: ['submit_to_delayed_success', 'click_to_loading_then_result'],
        runtime_conditions: ['slow_save_response', 'server_error_500'],
        current_mvp_expected_observation: 'network_idle_observed may appear as supporting evidence only.',
        future_expected_observation: 'loading_finished, toast_shown, and server validation surfaces.',
        status: 'planned',
      },
    ],
  },
];

const routedCategories = categories.filter(
  (category): category is RoutedFixtureCategory => Boolean(category.route),
);

const activeCategoryId = computed(() => {
  const value = route.params.category;
  return typeof value === 'string' ? value : '';
});

const visibleCategories = computed(() => {
  if (!activeCategoryId.value) return categories;
  const match = categories.find((category) => category.id === activeCategoryId.value);
  return match ? [match] : categories;
});
</script>

<style scoped>
.runtime-page {
  min-height: 100vh;
  padding: 40px 24px 64px;
  background: #f5f7fa;
  color: #1f2937;
}

.runtime-header,
.boundary-strip,
.category-nav,
.category-section,
.rules-layout {
  max-width: 1120px;
  margin-left: auto;
  margin-right: auto;
}

.runtime-header {
  margin-bottom: 28px;
}

.back-link {
  display: inline-flex;
  margin-bottom: 18px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.eyebrow,
.phase {
  margin: 0 0 6px;
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.runtime-header h1 {
  margin: 0 0 10px;
  font-size: 30px;
  line-height: 1.2;
}

.summary {
  max-width: 760px;
  margin: 0;
  color: #4b5563;
  font-size: 14px;
  line-height: 1.7;
}

.boundary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
  padding: 18px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.boundary-strip h2,
.rule-block h2 {
  margin: 0 0 10px;
  font-size: 15px;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.chip-list li {
  padding: 4px 8px;
  border-radius: 4px;
  background: #eef2ff;
  color: #3730a3;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11px;
}

.chip-list.future li {
  background: #f3f4f6;
  color: #4b5563;
}

.category-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}

.category-link {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 7px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.category-link.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.category-link.disabled {
  color: #9ca3af;
  background: #f9fafb;
  cursor: not-allowed;
}

.category-section {
  margin-bottom: 30px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding-bottom: 10px;
  border-bottom: 1px solid #e5e7eb;
}

.section-heading h2 {
  margin: 0;
  font-size: 20px;
}

.priority {
  padding: 4px 8px;
  border-radius: 4px;
  background: #ecfdf5;
  color: #047857;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.section-summary {
  margin: 10px 0 14px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.6;
}

.fixture-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.fixture-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.fixture-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.fixture-head h3 {
  margin: 0;
  font-size: 16px;
}

.status {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: lowercase;
}

.status.planned {
  background: #fef3c7;
  color: #92400e;
}

.status.deferred {
  background: #f3f4f6;
  color: #4b5563;
}

.fixture-meta {
  display: grid;
  gap: 7px;
  margin: 0;
  font-size: 12px;
}

.fixture-meta > div {
  display: grid;
  grid-template-columns: 128px 1fr;
  gap: 10px;
}

.fixture-meta dt {
  color: #6b7280;
  font-weight: 700;
}

.fixture-meta dd {
  margin: 0;
  min-width: 0;
  color: #1f2937;
  overflow-wrap: anywhere;
}

code {
  padding: 1px 5px;
  border-radius: 3px;
  background: #f3f4f6;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11px;
}

.observation-block h4 {
  margin: 0 0 4px;
  font-size: 12px;
  color: #374151;
}

.observation-block p,
.planned-note {
  margin: 0;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.55;
}

.future-block {
  padding-top: 10px;
  border-top: 1px dashed #d1d5db;
}

.planned-note {
  margin-top: auto;
  color: #6b7280;
}

.fixture-actions {
  margin-top: auto;
}

.fixture-actions .btn {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.fixture-actions .btn-primary {
  background: #2563eb;
  color: #fff;
}

.fixture-actions .btn-primary:hover {
  background: #1d4ed8;
}

.rules-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 34px;
}

.rule-block {
  padding: 18px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.rule-block ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.55;
}

@media (max-width: 760px) {
  .runtime-page {
    padding: 28px 16px 48px;
  }

  .boundary-strip,
  .rules-layout {
    grid-template-columns: 1fr;
  }

  .runtime-header h1 {
    font-size: 24px;
  }

  .section-heading {
    display: block;
  }

  .priority {
    display: inline-flex;
    margin-top: 10px;
  }

  .fixture-meta > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
