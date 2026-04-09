<template>
  <div>
    <a-page-header
      title="Recording Detail"
      @back="goBack"
    >
      <template #extra>
        <a-space>
          <a-button @click="showEditModal">
            <template #icon><edit-outlined /></template>
            Edit
          </a-button>
          <a-popconfirm
            title="Delete this recording?"
            ok-text="Yes"
            cancel-text="No"
            @confirm="handleDelete"
          >
            <a-button danger>
              <template #icon><delete-outlined /></template>
              Delete
            </a-button>
          </a-popconfirm>
        </a-space>
      </template>
    </a-page-header>

    <a-spin :spinning="loading">
      <a-alert
        v-if="error"
        message="Error"
        :description="error"
        type="error"
        show-icon
        style="margin-bottom: 16px"
      />

      <a-card v-if="recording" :bordered="false" style="margin-top: 16px">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="ID">
            {{ recording.id }}
          </a-descriptions-item>
          <a-descriptions-item label="Name">
            {{ recording.name }}
          </a-descriptions-item>
          <a-descriptions-item label="Status">
            <a-tag :color="getStatusColor(recording.status)">
              {{ recording.status }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Source">
            {{ recording.source }}
          </a-descriptions-item>
          <a-descriptions-item label="Created At">
            {{ formatDate(recording.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="Updated At">
            {{ formatDate(recording.updated_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="Meta" :span="2">
            <a-textarea
              :value="formatJsonString(recording.meta)"
              :rows="4"
              readonly
            />
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <!-- Events Tabs -->
      <a-card v-if="recording" :bordered="false" style="margin-top: 16px">
        <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
          <a-tab-pane key="raw" tab="Raw Events">
            <div style="margin-bottom: 8px; color: #666; font-size: 12px">
              {{ recording.events.length }} raw events
            </div>
            <a-textarea
              :value="formatJsonString(recording.events)"
              :rows="20"
              readonly
              style="font-family: monospace; font-size: 12px"
            />
          </a-tab-pane>

          <a-tab-pane key="initial-state" tab="Initial State">
            <div v-if="initialState">
              <a-descriptions :column="3" size="small" bordered style="margin-bottom: 16px">
                <a-descriptions-item label="Page URL" :span="2">
                  <a :href="initialState.pageUrl" target="_blank" rel="noopener">
                    {{ initialState.pageUrl }}
                  </a>
                </a-descriptions-item>
                <a-descriptions-item label="Page Title">
                  {{ initialState.pageTitle }}
                </a-descriptions-item>
                <a-descriptions-item label="Captured At">
                  {{ new Date(initialState.capturedAt).toLocaleString() }}
                </a-descriptions-item>
                <a-descriptions-item label="Nodes">
                  <a-tag color="blue">{{ stateTreeNodeCount }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item v-if="initialState.pageHeading" label="Page Heading">
                  <span style="font-weight: 600">{{ initialState.pageHeading }}</span>
                </a-descriptions-item>
                <a-descriptions-item v-if="initialState.primaryActions && initialState.primaryActions.length > 0" label="Primary Actions" :span="2">
                  <a-space>
                    <a-tag v-for="action in initialState.primaryActions" :key="action" color="orange">
                      {{ action }}
                    </a-tag>
                  </a-space>
                </a-descriptions-item>
              </a-descriptions>

              <!-- AST Tree View (new format) -->
              <div v-if="flatTreeRows.length > 0" style="margin-bottom: 12px">
                <div
                  v-for="row in flatTreeRows"
                  :key="row.key"
                  :style="{ paddingLeft: row.depth * 20 + 'px' }"
                  class="state-tree-row"
                >
                  <!-- Section / Group nodes (containers) -->
                  <template v-if="row.node.type === 'section' || row.node.type === 'group'">
                    <span style="font-weight: 600; color: #333">
                      <a-tag :color="row.node.type === 'section' ? 'blue' : 'cyan'" style="font-size: 11px">
                        {{ row.node.type }}
                      </a-tag>
                      <a-tag v-if="row.node.blockType" :color="blockTypeColor(row.node.blockType)" style="font-size: 10px">
                        {{ row.node.blockType }}
                      </a-tag>
                      {{ row.node.label || '(unnamed)' }}
                    </span>
                    <a-tag v-if="row.node.required" color="red" style="font-size: 10px; margin-left: 4px">required</a-tag>
                    <span v-if="row.node.fieldProp" style="color: #999; font-size: 11px; margin-left: 8px">
                      prop={{ row.node.fieldProp }}
                    </span>
                    <span v-if="row.node.actions && row.node.actions.length > 0" style="margin-left: 8px">
                      <a-tag v-for="a in row.node.actions" :key="a" color="orange" style="font-size: 10px">{{ a }}</a-tag>
                    </span>
                    <span v-if="row.node.summaryText" style="color: #666; font-size: 11px; margin-left: 8px">
                      {{ truncate(row.node.summaryText, 60) }}
                    </span>
                  </template>

                  <!-- Table nodes -->
                  <template v-else-if="row.node.type === 'table'">
                    <a-tag color="volcano" style="font-size: 11px">table</a-tag>
                    <span v-if="row.node.label" style="font-weight: 500">{{ row.node.label }}</span>
                    <a
                      v-if="row.node.headers && row.node.headers.length > 0"
                      style="color: #1677ff; margin-left: 8px; cursor: pointer"
                      @click="openTableDetailModal(row.node)"
                    >
                      {{ row.node.headers.join(' | ') }}
                    </a>
                    <span v-if="row.node.itemCount" style="color: #999; margin-left: 8px">
                      {{ row.node.itemCount }} rows
                    </span>
                  </template>

                  <!-- List nodes -->
                  <template v-else-if="row.node.type === 'list'">
                    <a-tag color="lime" style="font-size: 11px">list</a-tag>
                    <span v-if="row.node.label" style="font-weight: 500">{{ row.node.label }}</span>
                    <span v-if="row.node.itemCount" style="color: #999; margin-left: 4px">
                      {{ row.node.itemCount }} items
                    </span>
                    <span
                      v-if="row.node.value"
                      style="color: #1677ff; margin-left: 8px; cursor: pointer"
                      @click="openListDetailModal(row.node)"
                    >
                      {{ truncate(row.node.value, 80) }}
                    </span>
                  </template>

                  <!-- Link nodes (navigation) -->
                  <template v-else-if="row.node.type === 'link'">
                    <a-tag color="magenta" style="font-size: 11px">link</a-tag>
                    <a-tag v-if="row.node.active" color="green" style="font-size: 9px">active</a-tag>
                    <span style="font-weight: 500">{{ row.node.label }}</span>
                    <span v-if="row.node.href" style="color: #999; font-size: 11px; margin-left: 8px">
                      → {{ truncate(row.node.href, 60) }}
                    </span>
                  </template>

                  <!-- Button nodes -->
                  <template v-else-if="row.node.type === 'button'">
                    <a-tag color="orange" style="font-size: 11px">button</a-tag>
                    <a-tag v-if="row.node.active" color="green" style="font-size: 9px">active</a-tag>
                    <span style="font-weight: 500">{{ row.node.label }}</span>
                  </template>

                  <!-- Leaf field nodes (input, select, checkbox, etc.) -->
                  <template v-else>
                    <a-tag :color="initialFieldTypeColor(row.node.type)" style="font-size: 11px">
                      {{ row.node.type }}
                    </a-tag>
                    <span v-if="row.node.label" style="font-weight: 500">{{ row.node.label }}</span>
                    <a-tag v-if="row.node.required" color="red" style="font-size: 10px; margin-left: 4px">*</a-tag>
                    <span v-if="row.node.fieldProp" style="color: #999; font-size: 11px; margin-left: 4px">
                      [{{ row.node.fieldProp }}]
                    </span>
                    <span v-if="row.node.value" style="color: #1677ff; margin-left: 8px">
                      = {{ truncate(row.node.value, 60) }}
                    </span>
                    <span v-else-if="row.node.placeholder" style="color: #bbb; font-style: italic; margin-left: 8px">
                      {{ truncate(row.node.placeholder, 50) }}
                    </span>
                    <span v-if="row.node.itemCount" style="color: #999; margin-left: 4px">
                      ({{ row.node.itemCount }})
                    </span>
                    <a-tag
                      v-if="row.node.localHtml || row.node.htmlContent"
                      color="purple"
                      style="font-size: 9px; margin-left: 4px; cursor: pointer"
                      @click="openLocalHtmlModal(row.node)"
                    >
                      localHtml
                    </a-tag>
                  </template>
                </div>
              </div>

              <!-- Legacy flat table (old recordings with fields[]) -->
              <a-table
                v-else-if="initialState.fields && initialState.fields.length > 0"
                :columns="initialStateColumns"
                :data-source="initialState.fields"
                :pagination="false"
                size="small"
                row-key="(r, i) => `${r.fieldLabel}_${r.fieldProp}_${i}`"
                style="margin-bottom: 12px"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'fieldLabel'">
                    <div>{{ record.fieldPath || record.fieldLabel || '—' }}</div>
                    <div
                      v-if="record.sectionLabel && record.fieldPath !== record.sectionLabel"
                      style="color: #999; font-size: 11px"
                    >
                      section: {{ record.sectionLabel }}
                    </div>
                  </template>
                  <template v-else-if="column.key === 'fieldType'">
                    <a-tag :color="initialFieldTypeColor(record.fieldType)">
                      {{ record.fieldType || 'unknown' }}
                    </a-tag>
                  </template>
                  <template v-else-if="column.key === 'itemCount'">
                    <span v-if="record.itemCount">{{ record.itemCount }}</span>
                    <span v-else style="color: #ccc">—</span>
                  </template>
                  <template v-else-if="column.key === 'required'">
                    <a-tag v-if="record.required" color="red" style="font-size: 11px">✓</a-tag>
                    <span v-else style="color: #ccc">—</span>
                  </template>
                  <template v-else-if="column.key === 'defaultValueText'">
                    <a
                      v-if="record.defaultValueText && (record.fieldType === 'table' || record.fieldType === 'list')"
                      style="color: #1677ff"
                      @click="openFieldDetailModal(record)"
                    >
                      {{ truncate(record.defaultValueText, 80) }}
                    </a>
                    <span v-else-if="record.defaultValueText" style="color: #1677ff">
                      {{ truncate(record.defaultValueText, 80) }}
                    </span>
                    <span v-else-if="record.placeholder" style="color: #bbb; font-style: italic">
                      {{ truncate(record.placeholder, 60) }}
                    </span>
                    <span v-else style="color: #ccc">—</span>
                  </template>
                </template>
              </a-table>

              <a-collapse style="margin-top: 12px">
                <a-collapse-panel key="json" header="Semantic State Tree (JSON)">
                  <a-textarea
                    :value="formatJsonString({ stateTree: initialState.stateTree, pageHeading: initialState.pageHeading, primaryActions: initialState.primaryActions })"
                    :rows="16"
                    readonly
                    style="font-family: monospace; font-size: 11px"
                  />
                </a-collapse-panel>
                <a-collapse-panel v-if="leafHtmlCount > 0" key="leaf-html" :header="`Leaf-level Local HTML (${leafHtmlCount} nodes)`">
                  <div style="color: #666; font-size: 12px; margin-bottom: 8px">
                    Small HTML snippets on complex leaf nodes where semantic extraction alone is insufficient.
                  </div>
                  <a-textarea
                    :value="formatJsonString(leafHtmlNodes)"
                    :rows="12"
                    readonly
                    style="font-family: monospace; font-size: 11px"
                  />
                </a-collapse-panel>
                <a-collapse-panel v-if="rawHtmlSnapshotData" key="html" header="Raw HTML Snapshot (debug/fallback)">
                  <div style="margin-bottom: 8px; color: #999; font-size: 12px">
                    Debug/fallback layer — {{ (rawHtmlSnapshotData.length / 1024).toFixed(1) }} KB.
                    Not used in primary analysis pipeline.
                  </div>
                  <a-textarea
                    :value="rawHtmlSnapshotData"
                    :rows="20"
                    readonly
                    style="font-family: monospace; font-size: 11px"
                  />
                </a-collapse-panel>
                <a-collapse-panel key="full-json" header="Full Initial State JSON">
                  <a-textarea
                    :value="formatJsonString(initialState)"
                    :rows="16"
                    readonly
                    style="font-family: monospace; font-size: 11px"
                  />
                </a-collapse-panel>
              </a-collapse>
            </div>

            <div v-else style="color: #999; text-align: center; padding: 32px">
              No initial state captured for this recording.
              <br />
              <span style="font-size: 12px; margin-top: 8px; display: block">
                Initial state is captured automatically by the extension (Task Pack 6.5+).
              </span>
            </div>
          </a-tab-pane>

          <a-tab-pane key="normalized" tab="Normalized Recording">
            <a-spin :spinning="normLoading">
              <a-alert
                v-if="normError"
                :message="normError"
                type="error"
                show-icon
                style="margin-bottom: 12px"
              />

              <div v-if="normalized">
                <!-- Summary banner -->
                <a-descriptions
                  :column="6"
                  size="small"
                  bordered
                  style="margin-bottom: 16px"
                >
                  <a-descriptions-item label="Raw events">
                    {{ normalized.summary.event_count_raw }}
                  </a-descriptions-item>
                  <a-descriptions-item label="Normalized steps">
                    {{ normalized.summary.event_count_normalized }}
                  </a-descriptions-item>
                  <a-descriptions-item label="Segments">
                    {{ normalized.summary.segment_count }}
                  </a-descriptions-item>
                  <a-descriptions-item label="Pages">
                    {{ normalized.summary.page_count }}
                  </a-descriptions-item>
                  <a-descriptions-item label="iFrame">
                    <a-tag :color="normalized.summary.contains_iframe ? 'blue' : 'default'">
                      {{ normalized.summary.contains_iframe ? 'Yes' : 'No' }}
                    </a-tag>
                  </a-descriptions-item>
                  <a-descriptions-item label="Rich text">
                    <a-tag :color="normalized.summary.contains_richtext ? 'purple' : 'default'">
                      {{ normalized.summary.contains_richtext ? 'Yes' : 'No' }}
                    </a-tag>
                  </a-descriptions-item>
                </a-descriptions>

                <!-- Key actions -->
                <a-card size="small" title="Key Actions" style="margin-bottom: 16px">
                  <div v-if="normalized.key_actions.length === 0" style="color: #999">
                    No key actions detected.
                  </div>
                  <a-list
                    v-else
                    size="small"
                    :data-source="normalized.key_actions"
                  >
                    <template #renderItem="{ item }">
                      <a-list-item>
                        <a-space wrap>
                          <a-tag :color="actionColor(item.action_type)">
                            {{ item.action_type }}
                          </a-tag>
                          <span v-if="item.field_label" style="font-weight: 500">
                            {{ item.field_label }}
                          </span>
                          <span v-if="item.button_text" style="color: #666">
                            "{{ item.button_text }}"
                          </span>
                          <span v-if="item.value" style="color: #1677ff">
                            = {{ truncate(item.value, 60) }}
                          </span>
                          <a-tag v-if="item.in_iframe" color="cyan" style="font-size: 11px">
                            iframe
                          </a-tag>
                          <a-tag v-if="item.is_richtext" color="purple" style="font-size: 11px">
                            richtext
                          </a-tag>
                        </a-space>
                      </a-list-item>
                    </template>
                  </a-list>
                </a-card>

                <!-- Segments -->
                <div v-for="seg in normalized.segments" :key="seg.index" style="margin-bottom: 12px">
                  <a-card
                    size="small"
                    :title="`[${seg.type}] ${seg.title}`"
                    :headStyle="segmentHeaderStyle(seg.type)"
                  >
                    <div v-if="seg.steps.length === 0" style="color: #999">Empty segment.</div>
                    <a-table
                      v-else
                      :columns="stepColumns"
                      :data-source="seg.steps"
                      :pagination="false"
                      size="small"
                      row-key="timestamp"
                    >
                      <template #bodyCell="{ column, record }">
                        <template v-if="column.key === 'action_type'">
                          <a-tag :color="actionColor(record.action_type)">
                            {{ record.action_type }}
                          </a-tag>
                        </template>
                        <template v-else-if="column.key === 'field_label'">
                          {{ record.field_label || record.button_text || '—' }}
                        </template>
                        <template v-else-if="column.key === 'value'">
                          {{ record.value ? truncate(record.value, 50) : '—' }}
                        </template>
                        <template v-else-if="column.key === 'flags'">
                          <a-space>
                            <a-tag v-if="record.in_iframe" color="cyan" style="font-size: 11px">iframe</a-tag>
                            <a-tag v-if="record.is_richtext" color="purple" style="font-size: 11px">rt</a-tag>
                          </a-space>
                        </template>
                      </template>
                    </a-table>
                  </a-card>
                </div>

                <!-- Raw JSON toggle -->
                <a-collapse style="margin-top: 12px">
                  <a-collapse-panel key="json" header="Normalized JSON (raw)">
                    <a-textarea
                      :value="formatJsonString(normalized)"
                      :rows="20"
                      readonly
                      style="font-family: monospace; font-size: 11px"
                    />
                  </a-collapse-panel>
                </a-collapse>
              </div>

              <div v-else-if="!normLoading && !normError" style="color: #999; text-align: center; padding: 24px">
                Click the tab to load normalized recording.
              </div>
            </a-spin>
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </a-spin>

    <!-- Field Detail Drawer (table / list) -->
    <a-drawer
      v-model:open="fieldDetailModalOpen"
      :title="fieldDetailTitle"
      :width="640"
    >
      <div v-if="fieldDetailRecord">
        <!-- Table view (legacy) -->
        <template v-if="fieldDetailRecord.fieldType === 'table'">
          <a-table
            :columns="parsedTableColumns"
            :data-source="parsedTableRows"
            :pagination="false"
            size="small"
            row-key="(r, i) => i"
          />
        </template>
        <!-- List view (legacy) -->
        <template v-else-if="fieldDetailRecord.fieldType === 'list'">
          <a-list
            size="small"
            :data-source="parsedListItems"
            bordered
          >
            <template #renderItem="{ item, index }">
              <a-list-item>
                <a-space>
                  <a-tag color="blue">{{ index + 1 }}</a-tag>
                  {{ item }}
                </a-space>
              </a-list-item>
            </template>
          </a-list>
        </template>
      </div>

      <!-- StateNode table detail -->
      <div v-else-if="tableDetailNode">
        <a-descriptions :column="2" size="small" bordered style="margin-bottom: 12px">
          <a-descriptions-item v-if="tableDetailNode.label" label="Label">
            {{ tableDetailNode.label }}
          </a-descriptions-item>
          <a-descriptions-item label="Rows">
            {{ tableDetailNode.itemCount ?? tableDetailNode.rows?.length ?? 0 }}
          </a-descriptions-item>
        </a-descriptions>
        <a-table
          v-if="treeTableColumns.length > 0"
          :columns="treeTableColumns"
          :data-source="treeTableRows"
          :pagination="false"
          size="small"
          :row-key="(_r: Record<string, string>, i: number) => i"
          style="margin-top: 8px"
        />
        <div v-else style="color: #999">No table data captured.</div>
      </div>

      <!-- StateNode list detail -->
      <div v-else-if="listDetailNode">
        <a-descriptions :column="2" size="small" bordered style="margin-bottom: 12px">
          <a-descriptions-item v-if="listDetailNode.label" label="Label">
            {{ listDetailNode.label }}
          </a-descriptions-item>
          <a-descriptions-item label="Items">
            {{ listDetailNode.itemCount ?? parsedListDetailItems.length }}
          </a-descriptions-item>
        </a-descriptions>
        <a-list
          size="small"
          :data-source="parsedListDetailItems"
          bordered
          style="margin-top: 8px"
        >
          <template #renderItem="{ item, index }">
            <a-list-item>
              <a-space>
                <a-tag color="lime">{{ index + 1 }}</a-tag>
                {{ item }}
              </a-space>
            </a-list-item>
          </template>
        </a-list>
      </div>
    </a-drawer>

    <!-- Edit Modal -->
    <a-modal
      v-model:open="editModalOpen"
      title="Edit Recording"
      ok-text="Save"
      cancel-text="Cancel"
      :confirm-loading="loading"
      @ok="handleSave"
    >
      <a-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        layout="vertical"
      >
        <a-form-item label="Name" name="name">
          <a-input v-model:value="formData.name" />
        </a-form-item>
        <a-form-item label="Status" name="status">
          <a-select v-model:value="formData.status" style="width: 100%">
            <a-select-option value="draft">Draft</a-select-option>
            <a-select-option value="active">Active</a-select-option>
            <a-select-option value="archived">Archived</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="Source" name="source">
          <a-input v-model:value="formData.source" />
        </a-form-item>
        <a-form-item label="Events (JSON)" name="events">
          <a-textarea
            v-model:value="formData.eventsStr"
            :rows="4"
            @blur="validateJson('events')"
          />
          <div v-if="formErrors.events" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.events }}
          </div>
        </a-form-item>
        <a-form-item label="Meta (JSON)" name="meta">
          <a-textarea
            v-model:value="formData.metaStr"
            :rows="3"
            @blur="validateJson('meta')"
          />
          <div v-if="formErrors.meta" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.meta }}
          </div>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Local HTML Preview Drawer -->
    <a-drawer
      v-model:open="localHtmlModalOpen"
      :title="localHtmlModalTitle"
      :width="640"
    >
      <div style="margin-bottom: 12px; color: #666; font-size: 12px">
        Rendered preview of leaf-level local HTML snippet.
      </div>
      <a-tabs default-active-key="preview">
        <a-tab-pane key="preview" tab="Preview">
          <div
            class="html-preview-container"
            v-html="localHtmlContent"
          />
        </a-tab-pane>
        <a-tab-pane key="raw" tab="Raw HTML">
          <a-textarea
            :value="localHtmlContent"
            :rows="20"
            readonly
            style="font-family: monospace; font-size: 11px"
          />
        </a-tab-pane>
      </a-tabs>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { message, type FormInstance } from 'ant-design-vue';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { useRecordingsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import { getNormalizedRecording } from '@/api/recordings';
import type { RecordingUpdate, RecordingStatus, NormalizedRecording, PageInitialState, InitialFieldSnapshot, StateNode } from '@web-agent-flow/shared-types';

const route = useRoute();
const router = useRouter();
const recordingsStore = useRecordingsStore();

const formRef = ref<FormInstance>();
const editModalOpen = ref(false);
const activeTab = ref('raw');

const normalized = ref<NormalizedRecording | null>(null);
const normLoading = ref(false);
const normError = ref('');

const fieldDetailModalOpen = ref(false);
const fieldDetailRecord = ref<InitialFieldSnapshot | null>(null);
const tableDetailNode = ref<StateNode | null>(null);
const listDetailNode = ref<StateNode | null>(null);
const localHtmlModalOpen = ref(false);
const localHtmlModalTitle = ref('Local HTML Preview');
const localHtmlContent = ref('');

const formData = reactive({
  name: '',
  status: 'draft' as RecordingStatus,
  source: '',
  eventsStr: '[]',
  metaStr: ''
});

const formErrors = reactive({
  events: '',
  meta: ''
});

const rules = {
  name: [{ required: true, message: 'Name is required' }],
  source: [{ required: true, message: 'Source is required' }]
};

const recording = computed(() => recordingsStore.currentRecording);
const loading = computed(() => recordingsStore.loading);
const error = computed(() => recordingsStore.error);

const stepColumns = [
  { title: 'Action', key: 'action_type', width: 160 },
  { title: 'Field / Button', key: 'field_label' },
  { title: 'Value', key: 'value' },
  { title: 'Flags', key: 'flags', width: 100 },
];

const initialStateColumns = [
  { title: 'Label / Path', dataIndex: 'fieldLabel', key: 'fieldLabel', width: 240 },
  { title: 'Prop', dataIndex: 'fieldProp', key: 'fieldProp', width: 120 },
  { title: 'Type', key: 'fieldType', width: 100 },
  { title: 'Count', key: 'itemCount', width: 80 },
  { title: 'Req', key: 'required', width: 60 },
  { title: 'Default / Current Value', key: 'defaultValueText' },
];

const initialState = computed<PageInitialState | null>(() => {
  const meta = recording.value?.meta as Record<string, unknown> | null;
  if (!meta?.initialState) return null;
  return meta.initialState as PageInitialState;
});

interface FlatTreeRow {
  depth: number;
  node: StateNode;
  key: string;
}

function flattenTree(nodes: StateNode[], depth = 0, prefix = ''): FlatTreeRow[] {
  const rows: FlatTreeRow[] = [];
  nodes.forEach((node, i) => {
    const key = `${prefix}${i}`;
    rows.push({ depth, node, key });
    if (node.children) {
      rows.push(...flattenTree(node.children, depth + 1, `${key}-`));
    }
  });
  return rows;
}

function countNodes(nodes: StateNode[]): number {
  let count = 0;
  for (const node of nodes) {
    count++;
    if (node.children) count += countNodes(node.children);
  }
  return count;
}

const flatTreeRows = computed<FlatTreeRow[]>(() => {
  const tree = initialState.value?.stateTree;
  if (!tree || tree.length === 0) return [];
  return flattenTree(tree);
});

const stateTreeNodeCount = computed(() => {
  const tree = initialState.value?.stateTree;
  if (tree && tree.length > 0) return countNodes(tree);
  return initialState.value?.fields?.length ?? 0;
});

// 3-layer architecture helpers
const rawHtmlSnapshotData = computed(() => {
  const s = initialState.value;
  if (!s) return undefined;
  // Support both old (htmlSnapshot) and new (rawHtmlSnapshot) field names
  return (s as Record<string, unknown>).rawHtmlSnapshot as string | undefined
    ?? (s as Record<string, unknown>).htmlSnapshot as string | undefined;
});

function collectLeafHtml(nodes: StateNode[] | undefined): Array<{ label?: string; type: string; localHtml: string }> {
  if (!nodes) return [];
  const result: Array<{ label?: string; type: string; localHtml: string }> = [];
  for (const node of nodes) {
    const html = node.localHtml ?? (node as Record<string, unknown>).htmlContent as string | undefined;
    if (html) {
      result.push({ label: node.label, type: node.type, localHtml: html });
    }
    if (node.children) {
      result.push(...collectLeafHtml(node.children));
    }
  }
  return result;
}

const leafHtmlNodes = computed(() => collectLeafHtml(initialState.value?.stateTree));
const leafHtmlCount = computed(() => leafHtmlNodes.value.length);

const fieldDetailTitle = computed(() => {
  if (tableDetailNode.value) {
    const n = tableDetailNode.value;
    const label = n.label || 'Table';
    const count = n.itemCount ? `（${n.itemCount} 行）` : '';
    return `${label}${count}`;
  }
  if (listDetailNode.value) {
    const n = listDetailNode.value;
    const label = n.label || 'List';
    const count = n.itemCount ? `（${n.itemCount} 项）` : '';
    return `${label}${count}`;
  }
  const r = fieldDetailRecord.value;
  if (!r) return '';
  const label = r.fieldPath || r.fieldLabel || r.fieldType || '';
  const count = r.itemCount ? `（${r.itemCount} ${r.fieldType === 'table' ? '行' : '项'}）` : '';
  return `${label}${count}`;
});

const parsedListDetailItems = computed<string[]>(() => {
  const node = listDetailNode.value;
  if (!node?.value) return [];
  // Try to parse value in format "共N项：item1；item2；..."
  const text = node.value;
  const body = text.replace(/^共\d+项[：:]\s*/, '');
  return body.split(/[；;]/).filter(Boolean).map((s) => s.trim());
});

/**
 * Parse `defaultValueText` for a table field.
 * Format: "共N行：col1:val1 | col2:val2；col1:val2 | ..."
 * Returns { columns, rows } for a-table.
 */
const parsedTableRows = computed<Array<Record<string, string>>>(() => {
  const text = fieldDetailRecord.value?.defaultValueText;
  if (!text) return [];
  // Strip "共N行：" prefix
  const body = text.replace(/^共\d+行[：:]\s*/, '');
  return body.split(/[；;]/).filter(Boolean).map((rowStr) => {
    const record: Record<string, string> = {};
    rowStr.split(' | ').forEach((part, i) => {
      const colonIdx = part.indexOf(':');
      if (colonIdx > 0) {
        const key = part.slice(0, colonIdx).trim();
        const val = part.slice(colonIdx + 1).trim();
        record[key || `col${i}`] = val;
      } else {
        record[`col${i}`] = part.trim();
      }
    });
    return record;
  });
});

const parsedTableColumns = computed(() => {
  const rows = parsedTableRows.value;
  if (rows.length === 0) return [];
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  return keys.map((k) => ({ title: k, dataIndex: k, key: k, ellipsis: true }));
});

const parsedListItems = computed<string[]>(() => {
  const text = fieldDetailRecord.value?.defaultValueText;
  if (!text) return [];
  // Strip "共N项：" prefix
  const body = text.replace(/^共\d+项[：:]\s*/, '');
  return body.split(/[；;]/).filter(Boolean).map((s) => s.trim());
});

const treeTableColumns = computed(() => {
  const node = tableDetailNode.value;
  if (!node) return [];
  if (node.headers && node.headers.length > 0) {
    return node.headers.map((h, i) => ({ title: h, dataIndex: `col${i}`, key: `col${i}`, ellipsis: true }));
  }
  // No headers — infer column count from first row
  const firstRow = node.rows?.[0];
  if (!firstRow) return [];
  return firstRow.map((_, i) => ({ title: `Col ${i + 1}`, dataIndex: `col${i}`, key: `col${i}`, ellipsis: true }));
});

const treeTableRows = computed<Array<Record<string, string>>>(() => {
  const node = tableDetailNode.value;
  if (!node?.rows) return [];
  return node.rows.map((row) => {
    const record: Record<string, string> = {};
    row.forEach((cell, i) => { record[`col${i}`] = cell; });
    return record;
  });
});

function openFieldDetailModal(record: InitialFieldSnapshot): void {
  tableDetailNode.value = null;
  listDetailNode.value = null;
  fieldDetailRecord.value = record;
  fieldDetailModalOpen.value = true;
}

function openTableDetailModal(node: StateNode): void {
  fieldDetailRecord.value = null;
  listDetailNode.value = null;
  tableDetailNode.value = node;
  fieldDetailModalOpen.value = true;
}

function openListDetailModal(node: StateNode): void {
  fieldDetailRecord.value = null;
  tableDetailNode.value = null;
  listDetailNode.value = node;
  fieldDetailModalOpen.value = true;
}

function openLocalHtmlModal(node: StateNode): void {
  const html = node.localHtml ?? (node as Record<string, unknown>).htmlContent as string | undefined;
  if (!html) return;
  localHtmlModalTitle.value = node.label ? `HTML Preview: ${node.label}` : 'HTML Preview';
  localHtmlContent.value = html;
  localHtmlModalOpen.value = true;
}

function blockTypeColor(blockType: string): string {
  const map: Record<string, string> = {
    'form-section': 'green',
    'dialog': 'orange',
    'card-block': 'geekblue',
    'toolbar': 'gold',
    'content-block': 'default',
    'list-block': 'lime',
    'richtext-block': 'purple',
    'repeated-items-block': 'cyan',
    'table-section': 'volcano',
    'navigation': 'magenta',
  };
  return map[blockType] ?? 'default';
}

function initialFieldTypeColor(fieldType?: string): string {
  const map: Record<string, string> = {
    text: 'default',
    number: 'blue',
    select: 'green',
    checkbox: 'orange',
    radio: 'gold',
    richtext: 'purple',
    textarea: 'cyan',
    'date-range': 'geekblue',
    date: 'geekblue',
    time: 'geekblue',
    custom: 'magenta',
    table: 'volcano',
    list: 'lime',
    pagination: 'processing',
    tabs: 'cyan',
    steps: 'gold',
    breadcrumb: 'default',
    descriptions: 'purple',
    dialog: 'orange',
    cascader: 'green',
    autocomplete: 'green',
    switch: 'blue',
    slider: 'blue',
    rate: 'gold',
    upload: 'magenta',
    transfer: 'magenta',
    'code-editor': 'purple',
    color: 'magenta',
  };
  return map[fieldType ?? ''] ?? 'default';
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: 'default',
    active: 'green',
    archived: 'orange'
  };
  return colors[status] || 'default';
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s;
}

function actionColor(at: string): string {
  const map: Record<string, string> = {
    'navigate-page': 'geekblue',
    'fill-field': 'green',
    'select-field': 'lime',
    'edit-richtext': 'purple',
    'click-button': 'orange',
    'open-dialog': 'gold',
    'confirm-dialog': 'cyan',
    'cancel-dialog': 'red',
    'unknown-click': 'default',
  };
  return map[at] || 'default';
}

function segmentHeaderStyle(type: string): Record<string, string> {
  const bg: Record<string, string> = {
    navigation: '#e6f4ff',
    'form-fill': '#f6ffed',
    'dialog-interaction': '#fff7e6',
    'richtext-edit': '#f9f0ff',
    misc: '#fafafa',
  };
  return { background: bg[type] || '#fafafa' };
}

async function fetchRecording(): Promise<void> {
  const id = route.params.id as string;
  if (!id) return;
  try {
    await recordingsStore.fetchRecording(id);
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to load recording');
  }
}

async function loadNormalized(): Promise<void> {
  const id = route.params.id as string;
  if (!id || normalized.value) return;
  normLoading.value = true;
  normError.value = '';
  try {
    normalized.value = await getNormalizedRecording(id);
  } catch (e) {
    normError.value = e instanceof Error ? e.message : 'Failed to load normalized recording';
  } finally {
    normLoading.value = false;
  }
}

function handleTabChange(key: string): void {
  if (key === 'normalized') {
    void loadNormalized();
  }
}

function showEditModal(): void {
  if (!recording.value) return;

  formData.name = recording.value.name;
  formData.status = recording.value.status;
  formData.source = recording.value.source;
  formData.eventsStr = formatJsonString(recording.value.events);
  formData.metaStr = formatJsonString(recording.value.meta);
  formErrors.events = '';
  formErrors.meta = '';
  editModalOpen.value = true;
}

function validateJson(field: 'events' | 'meta'): boolean {
  const str = field === 'events' ? formData.eventsStr : formData.metaStr;
  if (!str.trim()) {
    formErrors[field] = '';
    return true;
  }
  const result = safeParseJson(str);
  if (!result.success) {
    formErrors[field] = result.error;
    return false;
  }
  formErrors[field] = '';
  return true;
}

async function handleSave(): Promise<void> {
  try {
    await formRef.value?.validate();

    if (!validateJson('events') || !validateJson('meta')) {
      return;
    }

    const eventsResult = safeParseJson(formData.eventsStr);
    const metaResult = safeParseJson(formData.metaStr);

    const updateData: RecordingUpdate = {
      name: formData.name,
      status: formData.status,
      source: formData.source,
      events: eventsResult.success ? eventsResult.data as Array<Record<string, unknown>> : undefined,
      meta: metaResult.success ? (metaResult.data as Record<string, unknown>) : null
    };

    await recordingsStore.updateRecording(route.params.id as string, updateData);
    // Invalidate cached normalized result so it's re-fetched after edit
    normalized.value = null;
    message.success('Recording updated');
    editModalOpen.value = false;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to update recording');
  }
}

async function handleDelete(): Promise<void> {
  try {
    await recordingsStore.deleteRecording(route.params.id as string);
    message.success('Recording deleted');
    goBack();
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to delete recording');
  }
}

function goBack(): void {
  void router.push('/recordings');
}

onMounted(() => {
  void fetchRecording();
});

onUnmounted(() => {
  recordingsStore.clearCurrent();
});
</script>

<style scoped>
.state-tree-row {
  padding: 4px 8px;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
  line-height: 24px;
}
.state-tree-row:hover {
  background: #fafafa;
}
.html-preview-container {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 16px;
  min-height: 200px;
  max-height: 500px;
  overflow-y: auto;
  background: #fff;
}
.html-preview-container :deep(*) {
  all: revert;
  box-sizing: border-box;
}
.html-preview-container :deep(style),
.html-preview-container :deep(script) {
  display: none;
}
</style>
