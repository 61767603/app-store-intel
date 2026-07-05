import { useCountryStore } from '../stores/country'

export function useApi() {
  const countryStore = useCountryStore()

  async function api<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(path, window.location.origin)
    url.searchParams.set('country', countryStore.country)
    if (params) {
      Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
    }
    const res = await fetch(url.toString())
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
  }

  return { api }
}
