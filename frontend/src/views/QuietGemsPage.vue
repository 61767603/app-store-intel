<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuietGemsStore } from '../stores/chartData'
import { useCountryStore } from '../stores/country'
import QuietGemTable from '../components/tables/QuietGemTable.vue'
import SearchInput from '../components/common/SearchInput.vue'

const store = useQuietGemsStore()
const countryStore = useCountryStore()
const search = ref('')
const catFilter = ref('')

const filtered = computed(() => {
  let list = store.data
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(g => (g.app_name || '').toLowerCase().includes(q) || (g.developer_name || '').toLowerCase().includes(q))
  }
  if (catFilter.value) {
    list = list.filter(g => g.category_id === catFilter.value)
  }
  return list
})

const uniqueCats = computed(() => {
  const ids = [...new Set(store.data.map(g => g.category_id))]
  return ids.map(id => ({ id, name: store.data.find(g => g.category_id === id)?.category_name || id }))
})

onMounted(() => store.fetch())
watch(() => countryStore.country, () => store.fetch())
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-5">
      <h2 class="text-base font-semibold text-slate-300">闷声型发现</h2>
      <span class="text-sm text-slate-500">分类 Top50 · 评价 &lt;5,000</span>
      <span class="text-sm px-3 py-1 rounded-lg bg-accent/15 text-accent-glow font-medium">{{ store.total }} 个</span>
    </div>

    <div class="flex gap-4 mb-5 flex-wrap items-center">
      <select v-model="catFilter" class="bg-slate-800/60 border border-slate-700/40 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:border-accent/40">
        <option value="">全部分类</option>
        <option v-for="c in uniqueCats" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <SearchInput v-model="search" placeholder="搜索应用名或开发者..." />
    </div>

    <QuietGemTable :filtered="filtered" />
  </div>
</template>
