<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { GemApp, LowRatingApp } from '../../types/api'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  quietGems: GemApp[]
  indieGems: GemApp[]
  lowRating: LowRatingApp[]
}>()

const option = computed(() => {
  const catMap = new Map<string, { quiet: number; indie: number; lowRat: number }>()
  props.quietGems.forEach(g => {
    const cat = g.category_name || g.category_id
    if (!catMap.has(cat)) catMap.set(cat, { quiet: 0, indie: 0, lowRat: 0 })
    catMap.get(cat)!.quiet++
  })
  props.indieGems.forEach(g => {
    const cat = g.category_name || g.category_id
    if (!catMap.has(cat)) catMap.set(cat, { quiet: 0, indie: 0, lowRat: 0 })
    catMap.get(cat)!.indie++
  })
  props.lowRating.forEach(g => {
    const cat = g.category_name || g.category_id
    if (!catMap.has(cat)) catMap.set(cat, { quiet: 0, indie: 0, lowRat: 0 })
    catMap.get(cat)!.lowRat++
  })

  const entries = [...catMap.entries()]
    .sort((a, b) => (b[1].quiet + b[1].indie + b[1].lowRat) - (a[1].quiet + a[1].indie + a[1].lowRat))
    .slice(0, 10)

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: '#6366f1',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
    },
    legend: {
      data: ['闷声型', '草根型', '低分高收'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: 36, containLabel: true },
    xAxis: { type: 'category', data: entries.map(e => e[0]), axisLabel: { color: '#94a3b8', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10 }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [
      { name: '闷声型', type: 'bar', data: entries.map(e => e[1].quiet), itemStyle: { color: '#6366f1', borderRadius: [3, 3, 0, 0] }, barMaxWidth: 24 },
      { name: '草根型', type: 'bar', data: entries.map(e => e[1].indie), itemStyle: { color: '#22c55e', borderRadius: [3, 3, 0, 0] }, barMaxWidth: 24 },
      { name: '低分高收', type: 'bar', data: entries.map(e => e[1].lowRat), itemStyle: { color: '#ef4444', borderRadius: [3, 3, 0, 0] }, barMaxWidth: 24 },
    ],
  }
})
</script>

<template>
  <div class="card p-5">
    <h3 class="card-title mb-4">各品类机会分布（Top 10）</h3>
    <VChart :option="option" autoresize style="height: 320px" />
  </div>
</template>
