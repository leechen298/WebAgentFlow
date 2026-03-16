<template>
  <main class="popup">
    <div class="badge">MV3</div>
    <h1>WebAgentFlow Recorder</h1>
    <p>Extension shell initialized. Recording logic will be added in a later task pack.</p>
  </main>
</template>

<style scoped>
.popup {
  width: 320px;
  min-height: 220px;
  padding: 24px;
  background:
    radial-gradient(circle at top, rgba(31, 122, 140, 0.18), transparent 45%),
    linear-gradient(180deg, #fffef8 0%, #edf4f4 100%);
  color: #102a43;
  font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
}

.badge {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  background: #d8eef0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

h1 {
  margin: 16px 0 12px;
  font-size: 24px;
}

p {
  margin: 0;
  line-height: 1.5;
}
</style>
