import { useEffect, useState } from 'react';

/**
 * Hook that triggers a re-render every second to keep relative times
 * ("2m ago", "12s ago") updated in the UI without causing full state
 * updates of the big dashboardStore.
 */
export function useFreshnessTick() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setTick((t) => t + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return tick;
}
