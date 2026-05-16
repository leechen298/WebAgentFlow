import { createRouter, createWebHistory } from 'vue-router';
import IndexPage from '../pages/IndexPage.vue';
import LoginPage from '../pages/LoginPage.vue';
import DashboardPage from '../pages/DashboardPage.vue';
import UserDirectoryPage from '../pages/UserDirectoryPage.vue';
import RuntimeObservationIndex from '../pages/runtime-observation/RuntimeObservationIndex.vue';
import BasicBusinessFixtureShell from '../pages/runtime-observation/basic/BasicBusinessFixtureShell.vue';

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
      path: '/runtime-observation/basic/login',
      name: 'basic-login',
      component: BasicBusinessFixtureShell,
      props: { fixtureId: 'basic-login' },
      meta: { title: 'Basic Login — Validation Site' },
    },
    {
      path: '/runtime-observation/basic/register',
      name: 'basic-register',
      component: BasicBusinessFixtureShell,
      props: { fixtureId: 'basic-register' },
      meta: { title: 'Basic Register — Validation Site' },
    },
    {
      path: '/runtime-observation/basic/sms-login',
      name: 'basic-sms-login',
      component: BasicBusinessFixtureShell,
      props: { fixtureId: 'basic-sms-login' },
      meta: { title: 'Basic SMS Login — Validation Site' },
    },
    {
      path: '/runtime-observation/basic/search',
      name: 'basic-search',
      component: BasicBusinessFixtureShell,
      props: { fixtureId: 'basic-search' },
      meta: { title: 'Basic Search — Validation Site' },
    },
    {
      path: '/runtime-observation/basic/detail',
      name: 'basic-detail',
      component: BasicBusinessFixtureShell,
      props: { fixtureId: 'basic-detail' },
      meta: { title: 'Basic Detail — Validation Site' },
    },
    {
      path: '/runtime-observation/basic/settings',
      name: 'basic-settings',
      component: BasicBusinessFixtureShell,
      props: { fixtureId: 'basic-settings' },
      meta: { title: 'Basic Settings — Validation Site' },
    },
    {
      path: '/runtime-observation/basic/confirm',
      name: 'basic-confirm',
      component: BasicBusinessFixtureShell,
      props: { fixtureId: 'basic-confirm' },
      meta: { title: 'Basic Confirm — Validation Site' },
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
