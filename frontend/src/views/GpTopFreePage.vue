<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCountryStore } from '../stores/country'

interface GpTopApp {
  rank: number; app_id: string; title: string
  category_id: string; developer: string; genre: string
  score: number; installs: string
  price: number; free: boolean; icon_url: string
}

const countryStore = useCountryStore()
const data = ref<GpTopApp[]>([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  const res = await window.fetch(`/api/gp/top_free?country=${countryStore.country}`)
  data.value = await res.json()
  loading.value = false
}

onMounted(() => loadData())
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-5">
      <h2 class="text-base font-semibold text-slate-300">📈 免费榜 Top 100</h2>
    </div>

    <div class="card overflow-hidden !p-0">
      <div class="overflow-x-auto">
        <table class="w-full text-xs border-collapse">
          <thead class="sticky top-0 z-10">
            <tr class="border-b border-slate-700/30 bg-slate-800/30">
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">#</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">应用</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">开发者</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">分类</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">评分</th>
              <th class="px-4 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider">安装量</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/30">
            <tr v-for="app in data" :key="app.app_id" class="hover:bg-slate-800/40 transition-colors">
              <td class="px-4 py-3"><span class="inline-block px-1.5 py-px rounded text-[11px] font-mono font-bold text-slate-400">{{ app.rank }}</span></td>
              <td class="px-4 py-3 min-w-[200px]">
                <a :href="`https://play.google.com/store/apps/details?id=${app.app_id}`" target="_blank" class="inline-flex items-center gap-2 text-slate-300 hover:text-accent-glow transition-colors">
                  <img v-if="app.icon_url" :src="app.icon_url" class="w-8 h-8 rounded-lg object-cover" loading="lazy">
                  <span v-else class="w-8 h-8 rounded-lg bg-accent/20 text-accent-glow text-xs font-bold flex items-center justify-center">{{ (app.title||'?')[0] }}</span>
                  <span class="text-xs truncate max-w-[160px]" :title="app.title">{{ app.title || '未知' }}</span>
                </a>
              </td>
              <td class="px-4 py-3 text-slate-500 max-w-[140px] truncate text-xs">{{ app.developer || '-' }}</td>
              <td class="px-4 py-3 text-slate-500 text-xs">{{ app.genre || '-' }}</td>
              <td class="px-4 py-3">
                <span v-if="app.score" class="text-xs" :class="app.score < 3.5 ? 'text-danger' : app.score < 4 ? 'text-warn' : 'text-ok'">
                  ★ {{ app.score.toFixed(1) }}
                </span>
                <span v-else class="text-slate-500 text-xs">-</span>
              </td>
              <td class="px-4 py-3 text-right text-slate-400 font-mono tabular-nums tracking-tight">{{ app.installs || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
