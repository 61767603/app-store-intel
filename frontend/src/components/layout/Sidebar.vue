<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useCountryStore } from '../../stores/country'

const router = useRouter()
const route = useRoute()
const countryStore = useCountryStore()

const LABELS: Record<string, string> = {
  us: '🇺🇸 美国', jp: '🇯🇵 日本', gb: '🇬🇧 英国', de: '🇩🇪 德国',
  kr: '🇰🇷 韩国', sa: '🇸🇦 沙特', au: '🇦🇺 澳洲', ca: '🇨🇦 加拿大',
  fr: '🇫🇷 法国', br: '🇧🇷 巴西', tr: '🇹🇷 土耳其', id: '🇮🇩 印尼',
}

function label(c: string) { return LABELS[c] || c.toUpperCase() }

const navItems = [
  { path: '/overview', label: '📊  总览' },
  { path: '/overall-top', label: '🏆  畅销总榜' },
  { path: '/quiet-gems', label: '🤫  闷声型' },
  { path: '/indie-gems', label: '🌱  草根型' },
  { path: '/low-rating', label: '🔥  低分高收' },
  { path: '/categories', label: '📂  品类排行' },
]

function isActive(path: string) { return route.path === path }
function navigate(path: string) { router.push(path) }
</script>

<template>
  <aside class="w-60 shrink-0 bg-base-800/60 backdrop-blur border-r border-slate-700/40 flex flex-col min-h-screen">
    <div class="px-5 py-5">
      <div class="flex items-center gap-3">
        <span class="text-2xl">📱</span>
        <div>
          <div class="font-bold text-lg text-slate-100 leading-tight">App Intel</div>
          <div class="text-xs text-slate-500">app.apisyncs.com</div>
        </div>
      </div>
    </div>

    <nav class="flex-1 px-3 space-y-2">
      <button
        v-for="item in navItems"
        :key="item.path"
        @click="navigate(item.path)"
        class="w-full flex items-center gap-3 px-4 py-3.5 rounded-lg text-base transition-colors font-medium"
        :class="isActive(item.path)
          ? 'bg-accent/15 text-accent-glow border-l-[3px] border-accent-glow shadow-sm'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border-l-[3px] border-transparent'"
      >
        {{ item.label }}
      </button>
    </nav>

    <div class="px-3 py-4 border-t border-slate-800/60">
      <label class="block text-xs text-slate-500 mb-2 px-3 uppercase tracking-wider">地区</label>
      <select
        :value="countryStore.country"
        @change="countryStore.setCountry(($event.target as HTMLSelectElement).value)"
        class="w-full bg-base-900/60 border border-slate-700/40 rounded-lg px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-accent/40 cursor-pointer appearance-none"
      >
        <option v-for="c in countryStore.availableCountries" :key="c" :value="c">{{ label(c) }}</option>
      </select>
    </div>

    <div class="px-5 py-3 text-xs text-slate-600 border-t border-slate-800/60">
      v1.0 · MVVM
    </div>
  </aside>
</template>
