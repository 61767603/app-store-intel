<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { GemApp } from '../../types/api'

use([ScatterChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ gems: GemApp[] }>()

const option = computed(() => {
  const points = props.gems
    .filter(g => g.est_downloads > 0 && g.rating_avg != null)
    .map(g => ({
      name: g.app_name || '',
      dev: g.developer_name || '',
      rank: g.rank_category,
      downloads: g.est_downloads,
      revenue: g.est_revenue_high || g.est_downloads * 0.1,
      rating: g.rating_avg as number,
    }))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: '#6366f1',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      formatter: (params: { dataIndex: number }) => {
        const d = points[params.dataIndex]
        if (!d) return ''
        return `${d.name}<br/>${d.dev}<br/>下载: ${Math.round(d.downloads).toLocaleString()}/月<br/>收入: $${Math.round(d.revenue).toLocaleString()}/月<br/>评分: ${d.rating.toFixed(1)}<br/>排名: #${d.rank}`
      },
    },
    grid: { left: '8%', right: '5%', top: 24, bottom: '10%' },
    xAxis: {
      type: 'log',
      name: '月下载量',
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLabel: { color: '#94a3b8', fontSize: 10, formatter: (v: number) => v >= 10000 ? (v / 10000).toFixed(0) + '万' : String(v) },
      splitLine: { lineStyle: { color: '#1e293b', type: 'dashed' } },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: {
      type: 'log',
      name: '月收入 ($)',
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLabel: { color: '#94a3b8', fontSize: 10, formatter: (v: number) => v >= 1000 ? '$' + (v / 1000).toFixed(0) + 'K' : '$' + v },
      splitLine: { lineStyle: { color: '#1e293b', type: 'dashed' } },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    series: [{
      type: 'scatter',
      data: points.map(d => [d.downloads, d.revenue, d.rating, d.rank]),
      symbolSize: (val: number[]) => 8 + (val[3] <= 10 ? 10 : val[3] <= 30 ? 5 : 2),
      itemStyle: {
        color: (params: { value: number[] }) => {
          const r = params.value[2]
          if (r < 3.0) return '#ef4444'
          if (r < 4.0) return '#eab308'
          return '#22c55e'
        },
        opacity: 0.8,
        borderColor: 'rgba(15,23,42,0.5)',
        borderWidth: 1,
      },
    }],
  }
})
</script>

<template>
  <div class="card p-5">
    <h3 class="card-title mb-4">下载量 × 收入 · 散点分析</h3>
    <VChart :option="option" autoresize style="height: 380px" />
  </div>
</template>
