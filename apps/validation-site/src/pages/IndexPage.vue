<template>
  <div class="index-page">
    <header class="site-header">
      <h1>WebAgentFlow · Validation Site</h1>
      <p class="subtitle">
        Self-hosted fixtures for autonomous exploration validation. Each page below is a
        deterministic test target — the application connects here to prove it can analyse,
        plan, act, and self-verify without depending on the public web.
      </p>
    </header>

    <div
      v-for="(pages, category) in byCategory"
      :key="category"
      class="category"
    >
      <h2>{{ category }}</h2>
      <div class="card-grid">
        <article
          v-for="page in pages"
          :key="page.id"
          class="page-card"
        >
          <div class="card-head">
            <h3>{{ page.name }}</h3>
            <span v-if="page.specId" class="badge badge-spec">spec</span>
          </div>
          <p class="desc">{{ page.description }}</p>

          <dl class="meta">
            <div v-if="page.path">
              <dt>Route</dt>
              <dd><code>{{ page.path }}</code></dd>
            </div>
            <div v-if="page.credentials">
              <dt>Credentials</dt>
              <dd><code>{{ page.credentials }}</code></dd>
            </div>
            <div v-if="page.specId">
              <dt>Spec id</dt>
              <dd>
                <code>{{ page.specId }}</code>
                <span class="hint">
                  — see <code>apps/validation-site/specs/{{ page.specId }}.md</code>
                </span>
              </dd>
            </div>
            <div v-if="page.scenarios && page.scenarios.length">
              <dt>Scenarios</dt>
              <dd>
                <span
                  v-for="s in page.scenarios"
                  :key="s"
                  class="badge badge-scenario"
                >{{ s }}</span>
              </dd>
            </div>
          </dl>

          <div class="actions">
            <router-link class="btn btn-primary" :to="page.path">
              Open page
            </router-link>
            <a
              v-if="page.specId"
              class="btn btn-secondary"
              :href="workbenchUrl(page)"
              target="_blank"
              rel="noopener"
            >
              Run in workbench ↗
            </a>
          </div>
        </article>
      </div>
    </div>

    <footer class="site-footer">
      <div>
        <strong>How to exercise these pages autonomously</strong>
        <p>
          Open the Autonomous Workbench at
          <a :href="workbenchRoot" target="_blank" rel="noopener"><code>{{ workbenchRoot }}</code></a>
          and fill in the URL + <code>spec_id</code> + <code>scenario</code> from any card
          above. WebAgentFlow will open the page, analyse it, plan actions, execute, and
          self-verify against the authored spec. You watch it happen — no curl, no
          intermediate operator.
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

// The curated list of validation pages. Add entries here as new fixtures land.
// Keep the shape stable — this structure is read by humans and by future tooling.
interface TestPage {
  id: string;
  category: string;
  name: string;
  path: string;
  description: string;
  specId?: string;
  scenarios?: string[];
  credentials?: string;
}

const PAGES: TestPage[] = [
  {
    id: 'login',
    category: 'Authentication',
    name: 'Login',
    path: '/login',
    description:
      'Sign-in form with username + password inputs, a primary submit button, and a persistent role=alert error region. Two secondary links are present as distractors.',
    specId: 'login',
    scenarios: ['valid_credentials', 'invalid_credentials'],
    credentials: 'admin / 123456',
  },
  {
    id: 'users',
    category: 'Listing & Search',
    name: 'User Directory',
    path: '/users',
    description:
      'Production-style search + table: text inputs, select, radio, date pickers, Cascader, range picker, month/time pickers, Tag-as-filter, plus an Ant Design Table with column sort and column filter. Per-row View buttons are distractions for a "filter this list" task. Only plain-text-input scenarios are covered by the current spec — popup-based controls are deferred to Phase 10.',
    specId: 'users',
    scenarios: ['filter_by_name', 'no_match'],
  },
];

const byCategory = computed<Record<string, TestPage[]>>(() => {
  const g: Record<string, TestPage[]> = {};
  for (const p of PAGES) {
    (g[p.category] ||= []).push(p);
  }
  return g;
});

// Point users to the Autonomous Workbench running in the console app.
// Console default dev port is 5174. If you're running the console elsewhere,
// just ignore this link — it's a hint, not a hard dependency.
const workbenchRoot = 'http://localhost:5174/exploration/autonomous';

function workbenchUrl(_: TestPage): string {
  // No query-param wiring yet. Open the workbench root; user pastes the page
  // URL + spec_id into the form. Keeping it dumb until we actually need deep
  // linking.
  return workbenchRoot;
}
</script>

<style scoped>
.index-page {
  min-height: 100vh;
  padding: 48px 24px 64px;
  background: #f5f7fa;
  color: #1f2937;
}

.site-header {
  max-width: 960px;
  margin: 0 auto 40px;
}
.site-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 600;
}
.subtitle {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.7;
  max-width: 720px;
}

.category {
  max-width: 960px;
  margin: 0 auto 32px;
}
.category h2 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 500;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 8px;
}

.card-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}

.page-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.card-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.desc {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
  margin: 0 0 12px;
}

.meta {
  margin: 0 0 16px;
  font-size: 12px;
  display: grid;
  gap: 6px;
}
.meta > div {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 8px;
}
.meta dt {
  color: #6b7280;
  font-weight: 500;
}
.meta dd {
  margin: 0;
  color: #1f2937;
}
.meta code {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11px;
}
.hint {
  color: #9ca3af;
  font-size: 11px;
  margin-left: 4px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  text-transform: lowercase;
  line-height: 1.4;
}
.badge-spec {
  background: #dbeafe;
  color: #1e40af;
}
.badge-scenario {
  background: #f3f4f6;
  color: #374151;
  margin-right: 4px;
}

.actions {
  margin-top: auto;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn {
  padding: 6px 14px;
  border-radius: 5px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover {
  background: #1d4ed8;
}
.btn-secondary {
  background: #fff;
  color: #2563eb;
  border-color: #bfdbfe;
}
.btn-secondary:hover {
  border-color: #2563eb;
  background: #eff6ff;
}

.site-footer {
  max-width: 960px;
  margin: 48px auto 0;
  padding: 24px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.site-footer strong {
  display: block;
  margin-bottom: 8px;
}
.site-footer p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
}
.site-footer code {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 12px;
}
</style>
