<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCountryStore } from '../../stores/country'
import { usePlatformStore } from '../../stores/platform'

const router = useRouter()
const route = useRoute()
const countryStore = useCountryStore()
const platformStore = usePlatformStore()

const LABELS: Record<string, string> = {
  us: '🇺🇸 美国', jp: '🇯🇵 日本', gb: '🇬🇧 英国', de: '🇩🇪 德国',
  kr: '🇰🇷 韩国', sa: '🇸🇦 沙特', au: '🇦🇺 澳洲', ca: '🇨🇦 加拿大',
  fr: '🇫🇷 法国', br: '🇧🇷 巴西', tr: '🇹🇷 土耳其', id: '🇮🇩 印尼',
}

const iosCountries = ['us', 'jp', 'de', 'gb', 'kr', 'sa', 'au', 'ca', 'fr', 'br', 'tr', 'id']
const androidCountries = ['us', 'jp', 'de', 'br', 'id']

const availableCountries = computed(() =>
  platformStore.platform === 'ios' ? iosCountries : androidCountries
)

const iosNavItems = [
  { path: '/overview', label: '📊  总览' },
  { path: '/overall-top', label: '🏆  畅销总榜' },
  { path: '/quiet-gems', label: '🤫  闷声型' },
  { path: '/indie-gems', label: '🌱  草根型' },
  { path: '/low-rating', label: '🔥  低分高收' },
  { path: '/categories', label: '📂  品类排行' },
]

const androidNavItems = [
  { path: '/gp/new-apps', label: '🆕  新发现' },
  { path: '/gp/top-free', label: '📈  免费榜' },
]

const navItems = computed(() =>
  platformStore.platform === 'ios' ? iosNavItems : androidNavItems
)

function isActive(path: string) { return route.path === path }
function navigate(path: string) { router.push(path) }
function switchTo(p: 'ios' | 'android') {
  platformStore.setPlatform(p)
  if (p === 'android' && !androidCountries.includes(countryStore.country)) {
    countryStore.setCountry('us')
  }
  router.push(p === 'ios' ? '/overview' : '/gp/new-apps')
}
</script>

<template>
  <aside class="w-60 shrink-0 bg-base-800/60 backdrop-blur border-r border-slate-700/40 flex flex-col min-h-screen">
    <div class="px-5 py-5">
      <div class="flex items-center gap-3">
        <span class="text-2xl">{{ platformStore.platform === 'ios' ? '📱' : '🤖' }}</span>
        <div>
          <div class="font-bold text-lg text-slate-100 leading-tight">App Intel</div>
          <div class="text-xs text-slate-500">app.apisyncs.com</div>
        </div>
      </div>
    </div>

    <!-- Platform Toggle -->
    <div class="px-3 mb-2">
      <div class="flex rounded-lg bg-slate-800/60 p-0.5">
        <button
          @click="switchTo('ios')"
          class="flex-1 py-1.5 text-sm rounded-md transition-colors font-medium"
          :class="platformStore.platform === 'ios' ? 'bg-accent text-white shadow' : 'text-slate-400 hover:text-slate-200'"
        >📱 iOS</button>
        <button
          @click="switchTo('android')"
          class="flex-1 py-1.5 text-sm rounded-md transition-colors font-medium"
          :class="platformStore.platform === 'android' ? 'bg-accent text-white shadow' : 'text-slate-400 hover:text-slate-200'"
        >🤖 安卓</button>
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
        <option v-for="c in availableCountries" :key="c" :value="c">{{ LABELS[c] || c.toUpperCase() }}</option>
      </select>
    </div>

    <div class="px-5 py-3 text-xs text-slate-600 border-t border-slate-800/60">
      v1.0 · iOS+GP
    </div>
  </aside>
</template>
