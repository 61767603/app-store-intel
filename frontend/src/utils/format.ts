export function formatCount(n: number | null | undefined): string {
  if (n == null) return '-'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

export function formatDownloads(d: number | null | undefined): string {
  if (d == null) return '-'
  if (d >= 10_000) return (d / 10_000).toFixed(1) + '万/月'
  if (d >= 1_000) return (d / 1_000).toFixed(1) + '千/月'
  return String(d) + '/月'
}

export function formatRevenue(lo: number | null, hi: number | null): string {
  if (lo == null && hi == null) return '-'

  const fmt = (v: number): string => {
    if (v >= 10_000) return '$' + (v / 10_000).toFixed(1) + '万'
    if (v >= 1_000) return '$' + (v / 1_000).toFixed(1) + '千'
    return '$' + v
  }

  const l = lo ?? 0
  const h = hi ?? 0
  return fmt(l) + '-' + fmt(h) + '/月'
}

export function parsePriceNum(p: string | number | null | undefined): number {
  if (p == null || p === 'Free' || p === 'Get') return 0
  const v = parseFloat(String(p).replace(/[^0-9.]/g, ''))
  return isNaN(v) ? 0 : v
}
