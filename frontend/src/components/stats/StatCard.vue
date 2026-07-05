<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value: string | number
  color?: 'default' | 'accent' | 'ok' | 'danger'
}>()

const bgMap: Record<string, string> = {
  default: 'bg-slate-500/20',
  accent: 'bg-accent/20',
  ok: 'bg-ok/20',
  danger: 'bg-danger/20',
}

const textMap: Record<string, string> = {
  default: 'text-slate-100',
  accent: 'text-accent-glow',
  ok: 'text-ok',
  danger: 'text-danger',
}

const borderMap: Record<string, string> = {
  default: 'border-slate-700/40',
  accent: 'border-accent/20',
  ok: 'border-ok/20',
  danger: 'border-danger/20',
}

const c = computed(() => props.color || 'default')
</script>

<template>
  <div class="card relative overflow-hidden p-5 transition-shadow duration-200 hover:shadow-glow" :class="borderMap[c]">
    <div class="absolute -right-6 -bottom-6 w-24 h-24 rounded-full opacity-15 blur-2xl pointer-events-none" :class="bgMap[c]" />
    <div class="relative">
      <div class="text-xs text-slate-500 mb-2">{{ label }}</div>
      <div class="stat-value" :class="textMap[c]">{{ value }}</div>
    </div>
  </div>
</template>
