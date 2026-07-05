<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ quietCount: number; indieCount: number; lowRatCount: number }>()

const option = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(15,23,42,0.95)',
    borderColor: '#6366f1',
    textStyle: { color: '#e2e8f0', fontSize: 12 },
  },
  legend: { bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
  series: [{
    type: 'pie',
    radius: ['45%', '75%'],
    center: ['50%', '46%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 6, borderColor: '#0b1220', borderWidth: 3 },
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold', color: '#e2e8f0' } },
    data: [
      { value: props.quietCount, name: '闷声型', itemStyle: { color: '#6366f1' } },
      { value: props.indieCount, name: '草根型', itemStyle: { color: '#22c55e' } },
      { value: props.lowRatCount, name: '低分高收', itemStyle: { color: '#ef4444' } },
    ],
  }],
}))
</script>

<template>
  <div class="card p-5">
    <h3 class="card-title mb-4">发现类型分布</h3>
    <VChart :option="option" autoresize style="height: 280px" />
  </div>
</template>
