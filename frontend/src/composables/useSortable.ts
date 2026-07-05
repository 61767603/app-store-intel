import { reactive } from 'vue'

export interface SortState {
  key: string
  dir: 'asc' | 'desc'
}

export function useSortable(initialKey = 'rank', initialDir: 'asc' | 'desc' = 'asc') {
  const sortState = reactive<SortState>({ key: initialKey, dir: initialDir })

  function sortData<T>(data: T[], key: string, type: 'num' | 'str' = 'num'): T[] {
    const dir = sortState.dir
    const sorted = [...data].sort((a, b) => {
      const va = (a as Record<string, unknown>)[key]
      const vb = (b as Record<string, unknown>)[key]

      let vaClean: unknown = key === 'overall_rank' ? (va ?? 9999) : (va ?? (type === 'num' ? 99999 : ''))
      let vbClean: unknown = key === 'overall_rank' ? (vb ?? 9999) : (vb ?? (type === 'num' ? 99999 : ''))

      if (type === 'num') {
        const na = Number(vaClean), nb = Number(vbClean)
        return dir === 'asc' ? na - nb : nb - na
      }
      return dir === 'asc' ? String(vaClean).localeCompare(String(vbClean)) : String(vbClean).localeCompare(String(vaClean))
    })
    return sorted
  }

  function toggleSort(key: string, type: 'num' | 'str' = 'num') {
    if (sortState.key === key) {
      sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc'
    } else {
      sortState.key = key
      sortState.dir = type === 'num' ? 'desc' : 'asc'
    }
  }

  return { sortState, sortData, toggleSort }
}
