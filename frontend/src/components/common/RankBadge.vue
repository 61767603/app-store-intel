<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ rank: number | null | undefined; type: 'category' | 'overall' }>()

const display = computed(() => props.rank != null ? `#${props.rank}` : null)

const badgeClass = computed(() => {
  if (props.rank == null) return 'text-slate-500'
  if (props.type === 'category') {
    if (props.rank === 1) return 'bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20'
    if (props.rank === 2) return 'bg-slate-400/15 text-slate-300 ring-1 ring-slate-400/20'
    if (props.rank === 3) return 'bg-orange-700/15 text-orange-400 ring-1 ring-orange-700/20'
    if (props.rank <= 5) return 'bg-ok/10 text-ok ring-1 ring-ok/15'
    if (props.rank <= 20) return 'bg-accent/10 text-accent-glow ring-1 ring-accent/15'
    if (props.rank <= 30) return 'text-slate-300'
    return 'text-slate-500'
  }
  if (props.rank <= 3) return 'bg-danger/10 text-danger ring-1 ring-danger/15 font-bold'
  if (props.rank <= 10) return 'bg-danger/10 text-danger ring-1 ring-danger/10'
  if (props.rank <= 50) return 'bg-orange-500/10 text-orange-400 ring-1 ring-orange-500/10'
  if (props.rank <= 100) return 'bg-accent/10 text-accent-glow ring-1 ring-accent/10'
  if (props.rank <= 200) return 'text-slate-300'
  return 'text-slate-500'
})
</script>

<template>
  <span v-if="display" :class="badgeClass" class="inline-block px-1.5 py-px rounded text-[11px] font-mono font-bold">{{ display }}</span>
  <span v-else class="text-xs text-slate-500">-</span>
</template>
