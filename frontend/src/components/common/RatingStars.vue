<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ rating: number | null | undefined }>()

const display = computed(() => {
  if (props.rating == null) return { text: 'N/A', cls: '', tag: false }
  const full = Math.floor(props.rating)
  const half = props.rating - full >= 0.25 && props.rating - full < 0.75 ? 1 : 0
  const empty = 5 - full - half
  const stars = '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(empty)
  let cls = ''
  let tag = false
  if (props.rating < 3.0) { cls = 'text-danger'; tag = true }
  else if (props.rating < 3.5) { cls = 'text-orange-400'; tag = true }
  else if (props.rating < 4.0) cls = 'text-warn'
  else cls = 'text-ok'
  return { text: `${stars} ${props.rating.toFixed(1)}`, cls, tag }
})
</script>

<template>
  <span
    :class="display.cls"
    class="text-xs whitespace-nowrap font-mono"
    :style="display.tag ? 'text-shadow: 0 0 8px currentColor' : ''"
  >{{ display.text }}</span>
</template>
