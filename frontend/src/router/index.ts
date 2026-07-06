import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/overview' },
    {
      path: '/overview',
      name: 'overview',
      component: () => import('../views/OverviewPage.vue'),
    },
    {
      path: '/overall-top',
      name: 'overall-top',
      component: () => import('../views/OverallTopPage.vue'),
    },
    {
      path: '/quiet-gems',
      name: 'quiet-gems',
      component: () => import('../views/QuietGemsPage.vue'),
    },
    {
      path: '/indie-gems',
      name: 'indie-gems',
      component: () => import('../views/IndieGemsPage.vue'),
    },
    {
      path: '/low-rating',
      name: 'low-rating',
      component: () => import('../views/LowRatingPage.vue'),
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('../views/CategoriesPage.vue'),
    },
    // Google Play routes
    {
      path: '/gp/new-apps',
      name: 'gp-new-apps',
      component: () => import('../views/GpNewAppsPage.vue'),
    },
    {
      path: '/gp/top-free',
      name: 'gp-top-free',
      component: () => import('../views/GpTopFreePage.vue'),
    },
  ],
})

export default router
