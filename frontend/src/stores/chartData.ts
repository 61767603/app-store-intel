import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OverallApp, PaginatedResponse, GemApp, IndieGemApp, LowRatingApp, CategoryInfo, CategoryTopApp } from '../types/api'
import { useApi } from '../composables/useApi'
import { parsePriceNum } from '../utils/format'

export const useOverallTopStore = defineStore('overallTop', () => {
  const data = ref<OverallApp[]>([])
  const loading = ref(false)

  async function fetch() {
    loading.value = true
    const { api } = useApi()
    try {
      const list = await api<OverallApp[]>('/api/overall_top')
      list.forEach(a => { a.price_sort = parsePriceNum(a.price) })
      data.value = list
    } finally {
      loading.value = false
    }
  }

  return { data, loading, fetch }
})

export const useQuietGemsStore = defineStore('quietGems', () => {
  const data = ref<GemApp[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetch() {
    loading.value = true
    const { api } = useApi()
    try {
      const res = await api<PaginatedResponse<GemApp>>('/api/quiet_gems', { page: '1', per_page: '200' })
      res.data.forEach(a => { a.price_sort = parsePriceNum(a.price) })
      data.value = res.data
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  return { data, total, loading, fetch }
})

export const useIndieGemsStore = defineStore('indieGems', () => {
  const data = ref<IndieGemApp[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetch() {
    loading.value = true
    const { api } = useApi()
    try {
      const res = await api<PaginatedResponse<IndieGemApp>>('/api/indie_gems', { page: '1', per_page: '200' })
      res.data.forEach(a => { a.price_sort = parsePriceNum(a.price) })
      data.value = res.data
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  return { data, total, loading, fetch }
})

export const useLowRatingStore = defineStore('lowRating', () => {
  const data = ref<LowRatingApp[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetch(categoryId?: string) {
    loading.value = true
    const { api } = useApi()
    const params: Record<string, string> = { page: '1', per_page: '200' }
    if (categoryId) params.category_id = categoryId
    try {
      const res = await api<PaginatedResponse<LowRatingApp>>('/api/low_rating', params)
      res.data.forEach(a => { a.price_sort = parsePriceNum(a.price) })
      data.value = res.data
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  return { data, total, loading, fetch }
})

export const useCategoriesStore = defineStore('categories', () => {
  const categories = ref<CategoryInfo[]>([])
  const topByCategory = ref<Record<string, CategoryTopApp[]>>({})
  const loading = ref(false)

  async function fetchCategories() {
    const { api } = useApi()
    categories.value = await api<CategoryInfo[]>('/api/categories')
  }

  async function fetchCategoryTop() {
    loading.value = true
    const { api } = useApi()
    const catList = categories.value
    const results: Record<string, CategoryTopApp[]> = {}

    const chunks = []
    for (let i = 0; i < catList.length; i += 6) {
      chunks.push(catList.slice(i, i + 6))
    }

    for (const chunk of chunks) {
      const promises = chunk.map(async cat => {
        const data = await api<CategoryTopApp[]>('/api/category_top', { category_id: cat.id })
        data.forEach(a => { a.price_sort = parsePriceNum(a.price) })
        results[cat.id] = data
      })
      await Promise.all(promises)
    }

    topByCategory.value = results
    loading.value = false
  }

  async function fetchAll() {
    await fetchCategories()
    await fetchCategoryTop()
  }

  return { categories, topByCategory, loading, fetchAll }
})
