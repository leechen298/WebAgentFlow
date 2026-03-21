import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '@/layouts/MainLayout.vue';
import HomePage from '@/pages/HomePage.vue';
import RecordingsPage from '@/pages/RecordingsPage.vue';
import RecordingDetailPage from '@/pages/RecordingDetailPage.vue';
import RunDetailPage from '@/pages/RunDetailPage.vue';
import RunsPage from '@/pages/RunsPage.vue';
import SkillDetailPage from '@/pages/SkillDetailPage.vue';
import SkillsPage from '@/pages/SkillsPage.vue';

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
          meta: { title: 'Overview', menuKey: '/' },
        },
        {
          path: 'recordings',
          name: 'recordings',
          component: RecordingsPage,
          meta: { title: 'Recordings', menuKey: '/recordings' },
        },
        {
          path: 'recordings/:id',
          name: 'recording-detail',
          component: RecordingDetailPage,
          meta: { title: 'Recording Detail', menuKey: '/recordings' },
        },
        {
          path: 'skills',
          name: 'skills',
          component: SkillsPage,
          meta: { title: 'Skills', menuKey: '/skills' },
        },
        {
          path: 'skills/:id',
          name: 'skill-detail',
          component: SkillDetailPage,
          meta: { title: 'Skill Detail', menuKey: '/skills' },
        },
        {
          path: 'runs',
          name: 'runs',
          component: RunsPage,
          meta: { title: 'Runs', menuKey: '/runs' },
        },
        {
          path: 'runs/:id',
          name: 'run-detail',
          component: RunDetailPage,
          meta: { title: 'Run Detail', menuKey: '/runs' },
        },
      ],
    },
  ],
});

router.afterEach((to) => {
  const title = String(to.meta.title ?? 'WebAgentFlow Console');
  document.title = `${title} | WebAgentFlow`;
});

export default router;
