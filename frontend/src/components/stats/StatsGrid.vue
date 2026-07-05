<script setup lang="ts">
import { computed } from 'vue'
import StatCard from './StatCard.vue'
import type { Overview } from '../../types/api'

const props = defineProps<{
  overview: Overview | null
}>()

const items = computed(() => {
  const o = props.overview
  if (!o) return []
  return [
    { label: '品类覆盖', value: o.categories ?? '-', color: 'default' as const },
    { label: '唯一应用', value: o.apps ?? '-', color: 'default' as const },
    { label: '详情条数', value: o.details ?? '-', color: 'default' as const },
    { label: '闷声型', value: o.quiet_count ?? '-', color: 'accent' as const },
    { label: '草根型', value: o.indie_count ?? '-', color: 'ok' as const },
    { label: '低分高收', value: o.low_rat_count ?? '-', color: 'danger' as const },
  ]
})
</script>

<template>
  <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
    <StatCard v-for="item in items" :key="item.label" :label="item.label" :value="item.value" :color="item.color" />
  </div>
</template>
