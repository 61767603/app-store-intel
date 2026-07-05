import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useCountryStore = defineStore('country', () => {
  const country = ref('us')
  const availableCountries = ref<string[]>([])

  function setCountry(c: string) {
    country.value = c
  }

  function setAvailableCountries(list: string[]) {
    availableCountries.value = list
  }

  return { country, availableCountries, setCountry, setAvailableCountries }
})
