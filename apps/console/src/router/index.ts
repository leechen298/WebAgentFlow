import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '@/layouts/MainLayout.vue';
import HomePage from '@/pages/HomePage.vue';
import RecordingsPage from '@/pages/RecordingsPage.vue';
import RecordingDetailPage from '@/pages/RecordingDetailPage.vue';
import RunDetailPage from '@/pages/RunDetailPage.vue';
import RunsPage from '@/pages/RunsPage.vue';
import SkillDetailPage from '@/pages/SkillDetailPage.vue';
import SkillsPage from '@/pages/SkillsPage.vue';
import ExplorationWorkbenchPage from '@/pages/ExplorationWorkbenchPage.vue';
import AutonomousWorkbenchPage from '@/pages/AutonomousWorkbenchPage.vue';
import LearningDebugPage from '@/pages/LearningDebugPage.vue';
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
          path: 'recordings',
          name: 'recordings',
          component: RecordingsPage,
          meta: { titleKey: 'nav.recordings', menuKey: '/recordings' },
        },
        {
          path: 'recordings/:id',
          name: 'recording-detail',
          component: RecordingDetailPage,
          meta: { titleKey: 'nav.recordingDetail', menuKey: '/recordings' },
        },
        {
          path: 'skills',
          name: 'skills',
          component: SkillsPage,
          meta: { titleKey: 'nav.skills', menuKey: '/skills' },
        },
        {
          path: 'skills/:id',
          name: 'skill-detail',
          component: SkillDetailPage,
          meta: { titleKey: 'nav.skillDetail', menuKey: '/skills' },
        },
        {
          path: 'runs',
          name: 'runs',
          component: RunsPage,
          meta: { titleKey: 'nav.runs', menuKey: '/runs' },
        },
        {
          path: 'runs/:id',
          name: 'run-detail',
          component: RunDetailPage,
          meta: { titleKey: 'nav.runDetail', menuKey: '/runs' },
        },
        {
          path: 'exploration',
          name: 'exploration',
          component: ExplorationWorkbenchPage,
          meta: { titleKey: 'nav.exploration', menuKey: '/exploration' },
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
          path: 'learning/debug',
          name: 'learning-debug',
          component: LearningDebugPage,
          meta: { titleKey: 'nav.learningDebug', menuKey: '/learning/debug' },
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
