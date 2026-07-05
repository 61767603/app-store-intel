import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Overview } from '../types/api'
import { useApi } from '../composables/useApi'
import { useCountryStore } from './country'

export const useOverviewStore = defineStore('overview', () => {
  const data = ref<Overview | null>(null)
  const loading = ref(false)

  async function fetch() {
    loading.value = true
    const { api } = useApi()
    try {
      data.value = await api<Overview>('/api/overview')
      const countryStore = useCountryStore()
      if (data.value) {
        countryStore.setAvailableCountries(data.value.countries)
      }
    } finally {
      loading.value = false
    }
  }

  return { data, loading, fetch }
})
