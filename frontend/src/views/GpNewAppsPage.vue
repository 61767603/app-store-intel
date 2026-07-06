<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCountryStore } from '../stores/country'
import type { GpNewApp } from '../types/api'

const countryStore = useCountryStore()
const data = ref<GpNewApp[]>([])
const total = ref(0)
const loading = ref(false)

async function loadData() {
  loading.value = true
  const cc = countryStore.country
  const res = await window.fetch(`/api/gp/new_apps?country=${cc}&per_page=200`)
  const json = await res.json()
  data.value = json.data
  total.value = json.total
  loading.value = false
}

onMounted(() => loadData())
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-5">
      <h2 class="text-base font-semibold text-slate-300">🆕 新发现应用</h2>
      <span class="text-xs px-2.5 py-1 rounded-md bg-ok/15 text-ok font-medium">{{ total }} 个</span>
    </div>

    <div class="card overflow-hidden !p-0">
      <div class="overflow-x-auto">
        <table class="w-full text-xs border-collapse">
          <thead class="sticky top-0 z-10">
            <tr class="border-b border-slate-700/30 bg-slate-800/30">
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">首次发现</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">应用</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">开发者</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">分类</th>
              <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">评分</th>
              <th class="px-4 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider">安装量</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/30">
            <tr v-for="app in data" :key="app.app_id" class="hover:bg-slate-800/40 transition-colors">
              <td class="px-4 py-3 text-slate-400 font-mono text-xs">{{ app.first_seen_date }}</td>
              <td class="px-4 py-3 min-w-[200px]">
                <a :href="app.url" target="_blank" class="inline-flex items-center gap-2 text-slate-300 hover:text-accent-glow transition-colors">
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
