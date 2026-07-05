<script setup lang="ts">
import { onMounted } from 'vue'
import StatsGrid from '../components/stats/StatsGrid.vue'
import CategoryBarChart from '../components/charts/CategoryBarChart.vue'
import GemTypePie from '../components/charts/GemTypePie.vue'
import RevenueScatter from '../components/charts/RevenueScatter.vue'
import { useOverviewStore } from '../stores/overview'
import { useQuietGemsStore, useLowRatingStore } from '../stores/chartData'

const overviewStore = useOverviewStore()
const quietStore = useQuietGemsStore()
const lowStore = useLowRatingStore()

onMounted(async () => {
  await overviewStore.fetch()
  await Promise.all([quietStore.fetch(), lowStore.fetch()])
})
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <h2 class="text-base font-semibold text-slate-300">概览面板</h2>
      <div class="h-px flex-1 bg-slate-800"></div>
      <span v-if="overviewStore.loading" class="text-sm text-indigo-400 animate-pulse">加载中...</span>
    </div>
    <StatsGrid :overview="overviewStore.data" />
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
      <CategoryBarChart :quiet-gems="quietStore.data" :low-rating="lowStore.data" />
      <GemTypePie
        :quiet-count="overviewStore.data?.quiet_count ?? 0"
        :indie-count="overviewStore.data?.indie_count ?? 0"
        :low-rat-count="overviewStore.data?.low_rat_count ?? 0"
      />
    </div>

    <RevenueScatter :gems="quietStore.data" />
  </div>
</template>
