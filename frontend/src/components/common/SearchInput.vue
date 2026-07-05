<script setup lang="ts">
const model = defineModel<string>({ default: '' })
defineProps<{ placeholder?: string }>()
</script>

<template>
  <input
    v-model="model"
    :placeholder="placeholder || '搜索应用名...'"
    class="bg-slate-800/60 border border-slate-700/40 rounded-lg px-4 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-accent/40 transition-colors min-w-[200px]"
  >
</template>
