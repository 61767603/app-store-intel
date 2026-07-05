<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ potential: number | null | undefined }>()

const score = computed(() => props.potential != null ? Math.round(props.potential) : null)

const barColor = computed(() => {
  if (score.value == null) return ''
  if (score.value >= 80) return 'from-amber-400 to-danger'
  if (score.value >= 60) return 'from-warn to-orange-500'
  if (score.value >= 40) return 'from-accent-glow to-accent'
  return 'from-slate-500 to-slate-400'
})

const textColor = computed(() => {
  if (score.value == null) return 'text-slate-500'
  if (score.value >= 80) return 'text-danger'
  if (score.value >= 60) return 'text-orange-400'
  if (score.value >= 40) return 'text-accent-glow'
  return 'text-slate-400'
})
</script>

<template>
  <div v-if="score != null" class="flex items-center gap-2">
    <div class="w-14 h-1.5 bg-slate-800 rounded-full overflow-hidden">
      <div class="h-full rounded-full bg-gradient-to-r transition-all duration-300" :class="barColor" :style="{ width: score + '%' }"></div>
    </div>
    <span class="text-xs font-mono font-bold tabular-nums" :class="textColor">{{ score }}</span>
  </div>
  <span v-else class="text-xs text-slate-500">-</span>
</template>
