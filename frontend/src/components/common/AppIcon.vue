<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  iconUrl: string | null | undefined
  appName: string | null | undefined
  appId: string
  country?: string
  size?: 'sm' | 'md'
}>()

const href = computed(() => {
  const cc = props.country || 'us'
  return `https://apps.apple.com/${cc}/app/id${props.appId}`
})
const letter = computed(() => (props.appName || '?')[0].toUpperCase())
const sizeClass = computed(() => props.size === 'sm' ? 'w-6 h-6 text-xs' : 'w-10 h-10 text-lg')
</script>

<template>
  <a :href="href" target="_blank" class="inline-flex items-center gap-2 text-slate-300 hover:text-accent-glow transition-colors shrink-0">
    <img
      v-if="iconUrl"
      :src="iconUrl"
      :alt="appName || ''"
      :class="[sizeClass, 'rounded-lg object-cover']"
      loading="lazy"
      @error="(e: Event) => { (e.target as HTMLImageElement).style.display = 'none'; ((e.target as HTMLElement).nextElementSibling as HTMLElement).style.display = 'flex' }"
    >
    <span
      :class="[sizeClass, 'rounded-lg bg-accent/20 text-accent-glow font-bold items-center justify-center shrink-0', iconUrl ? 'hidden' : 'flex']"
    >{{ letter }}</span>
    <span class="max-w-[160px] truncate text-xs" :title="appName || ''">{{ appName || '未知' }}</span>
  </a>
</template>
