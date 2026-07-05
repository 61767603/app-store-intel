<script setup lang="ts">
import { computed } from 'vue'
import { useSortable } from '../../composables/useSortable'
import AppIcon from '../common/AppIcon.vue'
import RatingStars from '../common/RatingStars.vue'
import PriceBadge from '../common/PriceBadge.vue'
import RankBadge from '../common/RankBadge.vue'
import PotentialBar from '../common/PotentialBar.vue'
import { formatCount, formatDownloads, formatRevenue } from '../../utils/format'
import type { LowRatingApp } from '../../types/api'

const props = defineProps<{ filtered: LowRatingApp[] }>()
const { sortState, sortData, toggleSort } = useSortable('potential', 'desc')
const sorted = computed(() => sortData(props.filtered, sortState.key, 'num'))
function arrow(k: string) { return sortState.key !== k ? '' : sortState.dir === 'asc' ? '▲' : '▼' }
</script>

<template>
  <div class="card overflow-hidden !p-0">
    <div class="overflow-x-auto">
      <table class="w-full text-xs border-collapse">
        <thead class="sticky top-0 z-10">
          <tr class="border-b border-slate-700/30 bg-slate-800/30">
            <th @click="toggleSort('rank_category','num')" class="px-3 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">排名 {{ arrow('rank_category') }}</th>
            <th @click="toggleSort('overall_rank','num')" class="px-3 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">总榜 {{ arrow('overall_rank') }}</th>
            <th @click="toggleSort('app_name','str')" class="px-3 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">应用 {{ arrow('app_name') }}</th>
            <th @click="toggleSort('developer_name','str')" class="px-3 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">开发者 {{ arrow('developer_name') }}</th>
            <th @click="toggleSort('rating_count','num')" class="px-3 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300 pr-4">评分数 {{ arrow('rating_count') }}</th>
            <th @click="toggleSort('rating_avg','num')" class="px-3 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300 pl-4">评分 {{ arrow('rating_avg') }}</th>
            <th @click="toggleSort('price_sort','num')" class="px-3 py-2.5 text-[11px] text-left text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">价格 {{ arrow('price_sort') }}</th>
            <th @click="toggleSort('est_downloads','num')" class="px-3 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">预估下载 {{ arrow('est_downloads') }}</th>
            <th @click="toggleSort('est_revenue_high','num')" class="px-3 py-2.5 text-[11px] text-right text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">预估收入 {{ arrow('est_revenue_high') }}</th>
            <th @click="toggleSort('potential','num')" class="px-3 py-2.5 text-[11px] text-center text-slate-500 font-medium uppercase tracking-wider cursor-pointer select-none hover:text-slate-300">潜力 {{ arrow('potential') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/30">
          <tr v-for="row in sorted" :key="row.app_id + '-' + row.category_id" class="hover:bg-slate-800/40 transition-colors bg-danger/[0.03]">
            <td class="px-3 py-2.5">
              <div class="flex flex-col items-start gap-0.5 min-w-[60px]">
                <span class="text-[10px] text-slate-500 leading-none">{{ row.category_name }}</span>
                <span class="text-lg font-bold font-mono text-slate-100 leading-none tabular-nums">#{{ row.rank_category }}</span>
              </div>
            </td>
            <td class="px-3 py-3"><RankBadge :rank="row.overall_rank" type="overall" /></td>
            <td class="px-3 py-3 min-w-[180px]"><AppIcon :icon-url="row.icon_url" :app-name="row.app_name" :app-id="row.app_id" :country="row.country" /></td>
            <td class="px-3 py-3 text-slate-500 max-w-[130px] truncate text-xs">{{ row.developer_name || '-' }}</td>
            <td class="px-3 py-3 text-right text-slate-400 font-mono tabular-nums tracking-tight pr-4">{{ formatCount(row.rating_count) }}</td>
            <td class="px-3 py-3 pl-4"><RatingStars :rating="row.rating_avg" /></td>
            <td class="px-3 py-3"><PriceBadge :price="row.price" /></td>
            <td class="px-3 py-3 text-right text-slate-200 font-mono tabular-nums tracking-tight">{{ formatDownloads(row.est_downloads) }}</td>
            <td class="px-3 py-3 text-right text-slate-200 font-mono tabular-nums tracking-tight">{{ formatRevenue(row.est_revenue_low, row.est_revenue_high) }}</td>
            <td class="px-3 py-3"><PotentialBar :potential="row.potential" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
