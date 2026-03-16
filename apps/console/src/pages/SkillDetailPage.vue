<template>
  <n-card :title="`Skill ${route.params.id}`">
    <p>Skill detail placeholder.</p>
  </n-card>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';
import { NCard } from 'naive-ui';

const route = useRoute();
</script>
