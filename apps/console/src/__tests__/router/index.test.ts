import { beforeEach, describe, expect, it } from 'vitest';
import router from '@/router';

describe('router', () => {
  beforeEach(async () => {
    await router.push('/');
    await router.isReady();
  });

  it('registers the expected application routes', () => {
    const names = router.getRoutes().map(route => route.name).filter(Boolean);

    expect(names).toEqual(expect.arrayContaining([
      'home',
      'recordings',
      'recording-detail',
      'skills',
      'skill-detail',
      'runs',
      'run-detail',
      'exploration',
      'learning-debug',
    ]));
  });

  it('updates document.title from route metadata', async () => {
    await router.push('/skills');

    expect(document.title).toContain('WebAgentFlow');
    expect(document.title.length).toBeGreaterThan('WebAgentFlow'.length);
  });
});
