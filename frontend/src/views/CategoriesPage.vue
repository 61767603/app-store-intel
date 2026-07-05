<script setup lang="ts">
import { onMounted } from 'vue'
import { useCategoriesStore } from '../stores/chartData'
import { formatRevenue } from '../utils/format'

const store = useCategoriesStore()

onMounted(() => store.fetchAll())
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-5">
      <h2 class="text-base font-semibold text-slate-300">各品类 Top 10</h2>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div
        v-for="cat in store.categories"
        :key="cat.id"
        class="card overflow-hidden !p-0 hover:shadow-glow transition-shadow"
      >
        <div class="bg-accent/15 border-b border-accent/10 px-4 py-3 flex justify-between items-center">
          <span class="text-sm font-semibold text-slate-200">{{ cat.name }}</span>
          <span class="text-xs text-slate-500">{{ cat.count }} 个</span>
        </div>
        <div v-if="store.topByCategory[cat.id]" class="divide-y divide-slate-800/40">
          <a
            v-for="app in store.topByCategory[cat.id]"
            :key="app.app_id"
            :href="`https://itunes.apple.com/app/id${app.app_id}`"
            target="_blank"
            class="flex items-center gap-2.5 px-4 py-2.5 hover:bg-slate-800/40 transition-colors"
          >
            <span class="text-xs text-slate-500 w-5 text-right shrink-0 font-mono">{{ app.rank }}</span>
            <img v-if="app.icon_url" :src="app.icon_url" class="w-6 h-6 rounded object-cover shrink-0" loading="lazy">
            <span v-else class="w-6 h-6 rounded bg-accent/20 text-accent-glow text-xs font-bold flex items-center justify-center shrink-0">{{ (app.app_name || '?')[0] }}</span>
            <div class="flex-1 min-w-0">
              <div class="text-xs text-slate-200 truncate">{{ app.app_name }}</div>
              <div class="text-[10px] text-slate-500 truncate">{{ app.developer_name }}</div>
            </div>
            <span class="text-[10px] text-slate-400 shrink-0 font-mono">{{ formatRevenue(app.est_revenue_low, app.est_revenue_high) }}</span>
          </a>
        </div>
        <div v-else class="px-4 py-8 text-center text-slate-500 text-xs">暂无数据</div>
      </div>
    </div>
  </div>
</template>
