<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ price: string | number | null | undefined }>()

const isFree = computed(() => {
  const p = props.price
  if (p == null || p === 'Free' || p === 'Get' || p === '' || p === 0) return true
  if (typeof p === 'number') return p === 0
  const n = parseFloat(p)
  return isNaN(n) || n === 0
})

const display = computed(() => {
  if (isFree.value) return null
  const v = typeof props.price === 'number' ? props.price : parseFloat(String(props.price).replace(/[^0-9.]/g, ''))
  return isNaN(v) ? null : '$' + v.toFixed(2)
})
</script>

<template>
  <span v-if="isFree" class="text-slate-500 text-xs">Free</span>
  <span v-else-if="display" class="text-accent-glow text-xs font-medium font-mono bg-accent/10 px-1.5 py-px rounded">{{ display }}</span>
  <span v-else class="text-slate-500 text-xs">-</span>
</template>
