import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '../pages/LoginPage.vue';
import DashboardPage from '../pages/DashboardPage.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'login', component: LoginPage, meta: { title: 'Sign in — Validation Site' } },
    { path: '/dashboard', name: 'dashboard', component: DashboardPage, meta: { title: 'Dashboard — Validation Site' } },
  ],
});

router.afterEach((to) => {
  const title = (to.meta.title as string) || 'Validation Site';
  document.title = title;
});
