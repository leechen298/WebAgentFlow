import { createRouter, createWebHistory } from 'vue-router';
import IndexPage from '../pages/IndexPage.vue';
import LoginPage from '../pages/LoginPage.vue';
import DashboardPage from '../pages/DashboardPage.vue';
import UserDirectoryPage from '../pages/UserDirectoryPage.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'index', component: IndexPage, meta: { title: 'WebAgentFlow · Validation Site' } },
    { path: '/login', name: 'login', component: LoginPage, meta: { title: 'Sign in — Validation Site' } },
    { path: '/dashboard', name: 'dashboard', component: DashboardPage, meta: { title: 'Dashboard — Validation Site' } },
    { path: '/users', name: 'users', component: UserDirectoryPage, meta: { title: 'User Directory — Validation Site' } },
  ],
});

router.afterEach((to) => {
  const title = (to.meta.title as string) || 'Validation Site';
  document.title = title;
});
