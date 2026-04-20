import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '@/layouts/MainLayout.vue';
import HomePage from '@/pages/HomePage.vue';
import AutonomousWorkbenchPage from '@/pages/AutonomousWorkbenchPage.vue';
import AutonomousRunHistoryPage from '@/pages/AutonomousRunHistoryPage.vue';
import AutonomousRunDetailPage from '@/pages/AutonomousRunDetailPage.vue';
import i18n from '@/i18n';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: HomePage,
          meta: { titleKey: 'nav.overview', menuKey: '/' },
        },
        {
          path: 'exploration/autonomous',
          name: 'exploration-autonomous',
          component: AutonomousWorkbenchPage,
          meta: {
            titleKey: 'nav.autonomousExploration',
            menuKey: '/exploration/autonomous',
          },
        },
        {
          path: 'exploration/autonomous/history',
          name: 'exploration-autonomous-history',
          component: AutonomousRunHistoryPage,
          meta: {
            titleKey: 'nav.autonomousHistory',
            menuKey: '/exploration/autonomous/history',
          },
        },
        {
          path: 'exploration/autonomous/history/:run_id',
          name: 'exploration-autonomous-run-detail',
          component: AutonomousRunDetailPage,
          meta: {
            titleKey: 'nav.autonomousHistory',
            // Keep the history link highlighted when viewing a run.
            menuKey: '/exploration/autonomous/history',
          },
        },
      ],
    },
  ],
});

router.afterEach((to) => {
  const t = i18n.global.t;
  const titleKey = String(to.meta.titleKey ?? '');
  const title = titleKey ? t(titleKey) : 'WebAgentFlow Console';
  document.title = `${title} | WebAgentFlow`;
});

export default router;
