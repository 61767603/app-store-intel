<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import { useOverviewStore } from '../../stores/overview'
import { onMounted, ref, onUnmounted } from 'vue'

const overviewStore = useOverviewStore()
onMounted(() => overviewStore.fetch())

const time = ref('')
let timer: ReturnType<typeof setInterval>
onMounted(() => {
  const tick = () => {
    time.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  tick()
  timer = setInterval(tick, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="flex bg-base-900 text-slate-200">
    <Sidebar />
    <main class="flex-1 min-w-0 min-h-screen">
      <header class="h-14 px-6 border-b border-slate-800/60 flex items-center justify-between bg-base-800/60 backdrop-blur sticky top-0 z-40">
        <div v-if="overviewStore.data" class="flex items-center gap-4 text-sm">
          <div class="flex items-center gap-2">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-ok opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-ok"></span>
            </span>
            <span class="text-slate-400">数据日期 <span class="text-slate-200 font-semibold">{{ overviewStore.data.date }}</span></span>
          </div>
          <span class="text-slate-600">·</span>
          <span class="text-slate-400">{{ overviewStore.data.apps }} 个应用</span>
        </div>
        <div v-else class="text-sm text-slate-500">正在连接 ...</div>
        <div class="text-sm text-slate-400 font-mono tabular-nums">{{ time }}</div>
      </header>
      <div class="p-6">
        <slot />
      </div>
    </main>
  </div>
</template>
