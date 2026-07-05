<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ rating: number | null | undefined }>()

const stars = computed(() => {
  if (props.rating == null) return ''
  const full = Math.floor(props.rating)
  const half = props.rating - full >= 0.25 && props.rating - full < 0.75 ? 1 : 0
  const empty = 5 - full - half
  return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(empty)
})

const starCls = computed(() => {
  if (props.rating == null) return ''
  if (props.rating < 3.0) return 'text-danger'
  if (props.rating < 3.5) return 'text-orange-400'
  if (props.rating < 4.0) return 'text-warn'
  return 'text-ok'
})

const isLow = computed(() => props.rating != null && props.rating < 3.5)
</script>

<template>
  <span v-if="props.rating == null" class="text-xs text-slate-500">N/A</span>
  <span v-else class="text-xs whitespace-nowrap inline-flex items-center gap-1">
    <span :class="starCls" :style="isLow ? 'text-shadow: 0 0 8px currentColor' : ''">{{ stars }}</span>
    <span class="text-slate-400 font-mono tabular-nums">{{ props.rating.toFixed(1) }}</span>
  </span>
</template>
