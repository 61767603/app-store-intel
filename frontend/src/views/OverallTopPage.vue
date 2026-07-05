<script setup lang="ts">
import { onMounted } from 'vue'
import { useOverallTopStore } from '../stores/chartData'
import OverallTopTable from '../components/tables/OverallTopTable.vue'

const store = useOverallTopStore()

onMounted(() => store.fetch())
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-5">
      <h2 class="text-base font-semibold text-slate-300">畅销总榜</h2>
      <span class="text-sm px-3 py-1 rounded-lg bg-accent/15 text-accent-glow font-medium">{{ store.data.length }} 个</span>
    </div>
    <OverallTopTable :data="store.data" />
  </div>
</template>
