import { createRouter, createWebHistory } from 'vue-router';
import WorkspaceLoginPage from '../pages/WorkspaceLoginPage.vue';
import WorkspaceHomePage from '../pages/WorkspaceHomePage.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/workspace-login',
    },
    {
      path: '/workspace-login',
      name: 'workspace-login',
      component: WorkspaceLoginPage,
    },
    {
      path: '/workspace-home',
      name: 'workspace-home',
      component: WorkspaceHomePage,
    },
  ],
});

export default router;
