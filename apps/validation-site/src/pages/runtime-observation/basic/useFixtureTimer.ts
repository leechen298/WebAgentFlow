import { onUnmounted } from 'vue';

export function useFixtureTimer() {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let interval: ReturnType<typeof setInterval> | null = null;

  function clearAll() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    if (interval) {
      clearInterval(interval);
      interval = null;
    }
  }

  function setDelay(ms: number, cb: () => void) {
    clearAll();
    timer = setTimeout(() => {
      timer = null;
      cb();
    }, ms);
  }

  function setCountdown(
    seconds: number,
    onTick: (n: number) => void,
    onDone: () => void,
  ) {
    clearAll();
    let remaining = seconds;
    onTick(remaining);
    interval = setInterval(() => {
      remaining -= 1;
      onTick(remaining);
      if (remaining <= 0) {
        if (interval) clearInterval(interval);
        interval = null;
        onDone();
      }
    }, 1000);
  }

  onUnmounted(clearAll);

  return { clearAll, setDelay, setCountdown };
}
