<script setup lang="ts">
import AppShell from './components/layout/AppShell.vue'
</script>

<template>
  <AppShell>
    <router-view v-slot="{ Component }">
      <keep-alive>
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </AppShell>
</template>
