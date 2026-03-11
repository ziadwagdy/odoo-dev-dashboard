import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'
import ProjectDetailView from '@/views/ProjectDetailView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/project/:name', component: ProjectDetailView },
    { path: '/health', component: () => import('@/views/HealthView.vue') },
    { path: '/onboard', component: () => import('@/views/OnboardView.vue') },
    { path: '/help', component: () => import('@/views/HelpView.vue') },
  ]
})

export default router
