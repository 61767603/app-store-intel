<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useLowRatingStore } from '../stores/chartData'
import { useCountryStore } from '../stores/country'
import LowRatingTable from '../components/tables/LowRatingTable.vue'

const store = useLowRatingStore()
const countryStore = useCountryStore()
const catFilter = ref('')

const filtered = computed(() => {
  let list = store.data
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
      <h2 class="text-base font-semibold text-slate-300">低分高收型</h2>
      <span class="text-sm text-slate-500">评分 &lt;4.0 · 排名 ≤200</span>
      <span class="text-sm px-3 py-1 rounded-lg bg-danger/15 text-danger font-medium">{{ store.total }} 个</span>
    </div>

    <div class="flex gap-4 mb-5 flex-wrap items-center">
      <select v-model="catFilter" class="bg-slate-800/60 border border-slate-700/40 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:border-accent/40">
        <option value="">全部分类</option>
        <option v-for="c in uniqueCats" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>

    <LowRatingTable :filtered="filtered" />

    <div class="flex items-center gap-4 mt-3 text-[11px] text-slate-500">
      <span class="text-slate-600">潜力图例：</span>
      <span class="flex items-center gap-1"><span class="inline-block w-3 h-1 rounded-full bg-gradient-to-r from-amber-400 to-danger"></span> 80+</span>
      <span class="flex items-center gap-1"><span class="inline-block w-3 h-1 rounded-full bg-gradient-to-r from-warn to-orange-500"></span> 60+</span>
      <span class="flex items-center gap-1"><span class="inline-block w-3 h-1 rounded-full bg-gradient-to-r from-accent-glow to-accent"></span> 40+</span>
      <span class="flex items-center gap-1"><span class="inline-block w-3 h-1 rounded-full bg-gradient-to-r from-slate-500 to-slate-400"></span> &lt;40</span>
    </div>
  </div>
</template>
