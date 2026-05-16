import { createRouter, createWebHistory } from 'vue-router';
import IndexPage from '../pages/IndexPage.vue';
import LoginPage from '../pages/LoginPage.vue';
import DashboardPage from '../pages/DashboardPage.vue';
import UserDirectoryPage from '../pages/UserDirectoryPage.vue';
import RuntimeObservationIndex from '../pages/runtime-observation/RuntimeObservationIndex.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'index', component: IndexPage, meta: { title: 'WebAgentFlow · Validation Site' } },
    { path: '/login', name: 'login', component: LoginPage, meta: { title: 'Sign in — Validation Site' } },
    { path: '/dashboard', name: 'dashboard', component: DashboardPage, meta: { title: 'Dashboard — Validation Site' } },
    { path: '/users', name: 'users', component: UserDirectoryPage, meta: { title: 'User Directory — Validation Site' } },
    {
      path: '/runtime-observation',
      name: 'runtime-observation',
      component: RuntimeObservationIndex,
      meta: { title: 'Runtime Observation Fixtures — Validation Site' },
    },
    {
      path: '/runtime-observation/:category(basic|medium|complex|mobile)',
      name: 'runtime-observation-category',
      component: RuntimeObservationIndex,
      meta: { title: 'Runtime Observation Fixtures — Validation Site' },
    },
  ],
});

router.afterEach((to) => {
  const title = (to.meta.title as string) || 'Validation Site';
  document.title = title;
});
