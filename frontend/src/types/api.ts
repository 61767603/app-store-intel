export interface Overview {
  date: string
  country: string
  categories: number
  apps: number
  details: number
  quiet_count: number
  indie_count: number
  low_rat_count: number
  countries: string[]
}

export interface OverallApp {
  rank: number
  app_id: string
  app_name: string
  developer_name: string
  rating_count: number | null
  rating_avg: number | null
  price: string | null
  genre: string | null
  icon_url: string | null
  est_downloads: number
  est_revenue_low: number
  est_revenue_high: number
  price_sort?: number
}

export interface GemApp {
  country: string
  category_id: string
  category_name: string
  app_id: string
  app_name: string
  developer_name: string
  rank_category: number
  overall_rank: number | null
  rating_count: number | null
  rating_avg: number | null
  price: string | null
  genre: string | null
  icon_url: string | null
  release_date: string | null
  est_downloads: number
  est_revenue_low: number
  est_revenue_high: number
  potential: number
  price_sort?: number
}

export interface IndieGemApp extends GemApp {
  rev_type: string
}

export interface LowRatingApp {
  country: string
  category_id: string
  category_name: string
  app_id: string
  app_name: string
  developer_name: string
  rank_category: number
  overall_rank: number | null
  rating_count: number | null
  rating_avg: number | null
  price: string | null
  genre: string | null
  icon_url: string | null
  release_date: string | null
  current_version_rating: number | null
  current_version_count: number | null
  est_downloads: number
  est_revenue_low: number
  est_revenue_high: number
  potential: number
  price_sort?: number
}

export interface PaginatedResponse<T> {
  total: number
  page: number
  per_page: number
  data: T[]
}

export interface CategoryInfo {
  id: string
  name: string
  count: number
}

export interface CategoryTopApp {
  rank: number
  app_id: string
  app_name: string
  developer_name: string
  rating_count: number | null
  rating_avg: number | null
  price: string | null
  genre: string | null
  icon_url: string | null
  overall_rank: number | null
  est_downloads: number
  potential: number
  est_revenue_low: number
  est_revenue_high: number
  price_sort?: number
}

export interface GpNewApp {
  app_id: string
  first_seen_date: string
  title: string
  developer: string
  genre: string
  score: number | null
  installs: string
  price: number
  free: boolean
  icon_url: string
  url: string
}
