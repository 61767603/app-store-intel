import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Platform = 'ios' | 'android'

export const usePlatformStore = defineStore('platform', () => {
  const platform = ref<Platform>('ios')

  function toggle() {
    platform.value = platform.value === 'ios' ? 'android' : 'ios'
  }

  function setPlatform(p: Platform) {
    platform.value = p
  }

  return { platform, toggle, setPlatform }
})
