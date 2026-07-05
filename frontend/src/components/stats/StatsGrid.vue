<script setup lang="ts">
import { computed } from 'vue'
import StatCard from './StatCard.vue'
import type { Overview } from '../../types/api'

const props = defineProps<{
  overview: Overview | null
}>()

const scaleItems = computed(() => {
  const o = props.overview
  if (!o) return []
  return [
    { label: '品类覆盖', value: o.categories ?? '-', color: 'default' as const },
    { label: '唯一应用', value: o.apps ?? '-', color: 'default' as const },
    { label: '详情条数', value: o.details ?? '-', color: 'default' as const },
  ]
})

const gemItems = computed(() => {
  const o = props.overview
  if (!o) return []
  return [
    { label: '闷声型', value: o.quiet_count ?? '-', color: 'accent' as const },
    { label: '草根型', value: o.indie_count ?? '-', color: 'ok' as const },
    { label: '低分高收', value: o.low_rat_count ?? '-', color: 'danger' as const },
  ]
})
</script>

<template>
  <div class="space-y-5 mb-6">
    <div>
      <div class="text-[11px] text-slate-500 uppercase tracking-wider mb-3 px-1">数据规模</div>
      <div class="grid grid-cols-3 gap-4">
        <StatCard v-for="item in scaleItems" :key="item.label" :label="item.label" :value="item.value" :color="item.color" />
      </div>
    </div>
    <div>
      <div class="text-[11px] text-slate-500 uppercase tracking-wider mb-3 px-1">发现机会</div>
      <div class="grid grid-cols-3 gap-4">
        <StatCard v-for="item in gemItems" :key="item.label" :label="item.label" :value="item.value" :color="item.color" />
      </div>
    </div>
  </div>
</template>
