import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import DashboardView from '@/views/DashboardView.vue'
import ProjectDetailView from '@/views/ProjectDetailView.vue'
import LoginView from '@/views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/', component: DashboardView },
    { path: '/project/:name', component: ProjectDetailView },
    { path: '/health', component: () => import('@/views/HealthView.vue') },
    { path: '/onboard', component: () => import('@/views/OnboardView.vue'), meta: { managerOrAdmin: true } },
    { path: '/users', component: () => import('@/views/UsersView.vue'), meta: { adminOnly: true } },
    { path: '/help', component: () => import('@/views/HelpView.vue') },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.public) return true

  if (!auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.adminOnly && !auth.isAdmin) {
    return { path: '/' }
  }

  if (to.meta.managerOrAdmin && !auth.canOnboard) {
    return { path: '/' }
  }

  return true
})

export default router
