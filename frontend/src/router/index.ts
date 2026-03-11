import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'
import ProjectDetailView from '@/views/ProjectDetailView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/project/:name', component: ProjectDetailView },
    { path: '/health', component: () => import('@/views/HealthView.vue') },
  ]
})

export default router
