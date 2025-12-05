import { useCallback, useState } from 'react';

function readInitial(key: string, fallback: boolean) {
  if (typeof window === 'undefined') return fallback;
  const stored = window.localStorage.getItem(key);
  if (stored === 'true' || stored === 'false') {
    return stored === 'true';
  }
  return fallback;
}

export function usePersistedBoolean(key: string, defaultValue: boolean) {
  const [value, setValue] = useState(() => readInitial(key, defaultValue));

  const update = useCallback(
    (next: boolean) => {
    setValue(next);
    window.localStorage.setItem(key, String(next));
    },
    [key]
  );

  return [value, update] as const;
}
