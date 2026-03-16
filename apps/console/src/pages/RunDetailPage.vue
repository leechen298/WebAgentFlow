<template>
  <n-card :title="`Run ${route.params.id}`">
    <p>Run detail placeholder.</p>
  </n-card>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';
import { NCard } from 'naive-ui';

const route = useRoute();
</script>
