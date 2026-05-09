import { useState, useRef, useCallback } from 'react';

/**
 * Плавный прогресс-бар: display-значение медленно ползёт вперёд
 * внутри каждого шага, не обгоняя реальный прогресс больше чем на 85% шага.
 */
export function useSmoothProgress() {
  const [displayProgress, setDisplayProgress] = useState(0);
  const ref = useRef({ target: 0, stepSize: 100, timer: null });

  const start = useCallback((total) => {
    ref.current = { target: 0, stepSize: 100 / Math.max(total, 1), timer: null };

    const tick = () => {
      setDisplayProgress(prev => {
        const { target, stepSize } = ref.current;
        // Можно дойти до 90% следующего шага, но не дальше 99
        const ceiling = Math.min(target + stepSize * 0.9, 99);
        if (prev >= ceiling) return prev;
        return Math.min(prev + 0.5, ceiling);
      });
      ref.current.timer = setTimeout(tick, 80);
    };

    ref.current.timer = setTimeout(tick, 80);
  }, []);

  // Вызывается при каждом реальном обновлении прогресса с бэкенда
  const update = useCallback((realPct) => {
    ref.current.target = realPct;
    if (realPct >= 100) {
      setDisplayProgress(100);
    } else {
      // Не откатываем назад, только вперёд
      setDisplayProgress(prev => Math.max(prev, realPct));
    }
  }, []);

  const reset = useCallback(() => {
    if (ref.current.timer) clearTimeout(ref.current.timer);
    ref.current = { target: 0, stepSize: 100, timer: null };
    setDisplayProgress(0);
  }, []);

  return { displayProgress, start, update, reset };
}
