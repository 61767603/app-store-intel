<script setup lang="ts">
import { computed } from 'vue'
import { useSortable } from '../../composables/useSortable'
import AppIcon from '../common/AppIcon.vue'
import RatingStars from '../common/RatingStars.vue'
import PriceBadge from '../common/PriceBadge.vue'
import { formatCount, formatDownloads, formatRevenue } from '../../utils/format'
import type { OverallApp } from '../../types/api'

const props = defineProps<{ data: OverallApp[] }>()
const { sortState, sortData, toggleSort } = useSortable('rank', 'asc')
const sorted = computed(() => sortData(props.data, sortState.key, 'num'))
function arrow(k: string) { return sortState.key !== k ? '' : sortState.dir === 'asc' ? '▲' : '▼' }
</script>

<template>
  <div class="card overflow-hidden !p-0">
    <div class="overflow-x-auto">
      <table class="w-full text-xs border-collapse">
        <thead class="sticky top-0 z-10">
          <tr class="border-b border-slate-700/30 bg-slate-800/30">
            <th @click="toggleSort('rank','num')" class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300"># {{ arrow('rank') }}</th>
            <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">应用</th>
            <th class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider">开发者</th>
            <th @click="toggleSort('rating_avg','num')" class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">评分 {{ arrow('rating_avg') }}</th>
            <th @click="toggleSort('rating_count','num')" class="px-4 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300 pr-5">评分数 {{ arrow('rating_count') }}</th>
            <th @click="toggleSort('price_sort','num')" class="px-4 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300 pl-5">价格 {{ arrow('price_sort') }}</th>
            <th @click="toggleSort('est_downloads','num')" class="px-4 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">预估下载 {{ arrow('est_downloads') }}</th>
            <th @click="toggleSort('est_revenue_high','num')" class="px-4 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">预估收入 {{ arrow('est_revenue_high') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/30">
          <tr v-for="row in sorted" :key="row.app_id" class="hover:bg-slate-800/40 transition-colors">
            <td class="px-4 py-3"><span class="inline-block px-1.5 py-px rounded text-[11px] font-mono font-bold text-slate-400">{{ row.rank }}</span></td>
            <td class="px-4 py-3"><AppIcon :icon-url="row.icon_url" :app-name="row.app_name" :app-id="row.app_id" /></td>
            <td class="px-4 py-3 text-slate-500 max-w-[160px] truncate text-xs">{{ row.developer_name || '-' }}</td>
            <td class="px-4 py-3"><RatingStars :rating="row.rating_avg" /></td>
            <td class="px-4 py-3 text-right text-slate-400 font-mono tabular-nums tracking-tight pr-5">{{ formatCount(row.rating_count) }}</td>
            <td class="px-4 py-3 pl-5"><PriceBadge :price="row.price" /></td>
            <td class="px-4 py-3 text-right text-slate-200 font-mono tabular-nums tracking-tight">{{ formatDownloads(row.est_downloads) }}</td>
            <td class="px-4 py-3 text-right text-slate-200 font-mono tabular-nums tracking-tight">{{ formatRevenue(row.est_revenue_low, row.est_revenue_high) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
