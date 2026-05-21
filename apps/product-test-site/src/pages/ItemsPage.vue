<template>
  <div class="items-shell">
    <header class="items-header">
      <div>
        <p class="page-kicker">Product Test Site</p>
        <h1>项目列表</h1>
      </div>
      <span class="page-badge">本地状态</span>
    </header>

    <main class="items-main" data-testid="items-page">
      <section class="create-panel" aria-labelledby="items-create-title">
        <div class="section-heading">
          <p class="section-label">新增项目</p>
          <h2 id="items-create-title">创建一个列表项</h2>
        </div>

        <form class="item-form" @submit.prevent="createItem">
          <label for="item-name">项目名称</label>
          <div class="input-row">
            <input
              id="item-name"
              v-model="itemName"
              data-testid="item-name-input"
              name="item-name"
              type="text"
              autocomplete="off"
              placeholder="请输入项目名称"
            />
            <button type="submit" data-testid="item-create-button">新增项目</button>
          </div>
        </form>

        <p
          class="operation-status"
          :class="{ 'is-error': statusTone === 'error', 'is-success': statusTone === 'success' }"
          data-testid="operation-status"
          aria-live="polite"
        >
          {{ operationStatus }}
        </p>
      </section>

      <section class="list-panel" aria-labelledby="items-list-title">
        <div class="section-heading">
          <p class="section-label">当前列表</p>
          <h2 id="items-list-title">项目数据</h2>
        </div>

        <ul class="item-list" data-testid="item-list">
          <li
            v-for="item in items"
            :key="item.id"
            class="item-row"
            data-testid="item-row"
            :data-item-id="item.id"
          >
            <span class="item-name" data-testid="item-row-name">{{ item.name }}</span>
            <time class="item-created" :datetime="item.createdAt">{{ item.createdAt }}</time>
          </li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

type Item = {
  id: string;
  name: string;
  createdAt: string;
};

const initialItems: Item[] = [
  { id: 'item-1', name: '默认项目A', createdAt: '2026-05-21 09:00' },
  { id: 'item-2', name: '默认项目B', createdAt: '2026-05-21 09:05' },
];

const items = ref<Item[]>([...initialItems]);
const itemName = ref('');
const operationStatus = ref('等待新增项目。');
const statusTone = ref<'neutral' | 'success' | 'error'>('neutral');
const nextId = ref(initialItems.length + 1);

function formatTimestamp(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0');
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hour = pad(date.getHours());
  const minute = pad(date.getMinutes());

  return `${year}-${month}-${day} ${hour}:${minute}`;
}

function createItem() {
  const name = itemName.value.trim();

  if (!name) {
    operationStatus.value = '请输入项目名称。';
    statusTone.value = 'error';
    return;
  }

  const newItem: Item = {
    id: `item-${nextId.value}`,
    name,
    createdAt: formatTimestamp(new Date()),
  };

  items.value = [...items.value, newItem];
  nextId.value += 1;
  itemName.value = '';
  operationStatus.value = `新增成功：${name}`;
  statusTone.value = 'success';
}
</script>

<style scoped>
.items-shell {
  min-height: 100vh;
  background: #f4f6f8;
  color: #1f2933;
}

.items-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  background: #fff;
  border-bottom: 1px solid #d9e2ec;
}

.page-kicker,
.section-label {
  margin: 0 0 8px;
  color: #174ea6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.items-header h1 {
  margin: 0;
  color: #111827;
  font-size: 24px;
}

.page-badge {
  padding: 6px 12px;
  background: #eef6ff;
  border: 1px solid #b8d6f7;
  border-radius: 6px;
  color: #174ea6;
  font-size: 13px;
}

.items-main {
  display: grid;
  grid-template-columns: minmax(280px, 380px) minmax(0, 1fr);
  gap: 24px;
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px;
  box-sizing: border-box;
}

.create-panel,
.list-panel {
  background: #fff;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.create-panel {
  padding: 24px;
  align-self: start;
}

.list-panel {
  padding: 24px;
}

.section-heading h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.item-form {
  margin-top: 24px;
}

.item-form label {
  display: block;
  margin-bottom: 8px;
  color: #334155;
  font-size: 14px;
  font-weight: 600;
}

.input-row {
  display: flex;
  gap: 10px;
}

.input-row input {
  flex: 1 1 auto;
  min-width: 0;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  color: #111827;
  font-size: 14px;
  box-sizing: border-box;
}

.input-row input:focus {
  outline: 2px solid #8bb8f2;
  outline-offset: 1px;
  border-color: #174ea6;
}

.input-row button {
  flex: 0 0 auto;
  height: 40px;
  padding: 0 16px;
  border: 0;
  border-radius: 6px;
  background: #174ea6;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.input-row button:hover {
  background: #0f3b83;
}

.operation-status {
  min-height: 20px;
  margin: 18px 0 0;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  color: #475569;
  font-size: 14px;
}

.operation-status.is-success {
  background: #effaf3;
  border-color: #9ad3ad;
  color: #12643a;
}

.operation-status.is-error {
  background: #fff2f0;
  border-color: #ffccc7;
  color: #cf1322;
}

.item-list {
  display: grid;
  gap: 10px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
}

.item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 48px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  box-sizing: border-box;
}

.item-name {
  min-width: 0;
  color: #111827;
  font-size: 15px;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.item-created {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 760px) {
  .items-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
    padding: 18px 20px;
  }

  .items-main {
    grid-template-columns: 1fr;
    padding: 20px;
  }

  .input-row,
  .item-row {
    align-items: stretch;
    flex-direction: column;
  }

  .input-row button {
    width: 100%;
  }

  .item-created {
    flex: 0 1 auto;
  }
}
</style>
