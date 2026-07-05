import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/overview' },
    {
      path: '/overview',
      name: 'overview',
      component: () => import('../views/OverviewPage.vue'),
      meta: { label: '📊 总览' },
    },
    {
      path: '/overall-top',
      name: 'overall-top',
      component: () => import('../views/OverallTopPage.vue'),
      meta: { label: '🏆 总榜' },
    },
    {
      path: '/quiet-gems',
      name: 'quiet-gems',
      component: () => import('../views/QuietGemsPage.vue'),
      meta: { label: '🤫 闷声型' },
    },
    {
      path: '/indie-gems',
      name: 'indie-gems',
      component: () => import('../views/IndieGemsPage.vue'),
      meta: { label: '🌱 草根型' },
    },
    {
      path: '/low-rating',
      name: 'low-rating',
      component: () => import('../views/LowRatingPage.vue'),
      meta: { label: '🔥 低分高收' },
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('../views/CategoriesPage.vue'),
      meta: { label: '📂 品类' },
    },
  ],
})

export default router
