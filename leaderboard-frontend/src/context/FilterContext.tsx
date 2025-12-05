import { createContext, useContext, useMemo, useState } from 'react';
import { usePersistedBoolean } from '../hooks/usePersistedBoolean';

interface FilterState {
  weightClass: string;
  setWeightClass: (value: string) => void;
  wrestlerSearch: string;
  setWrestlerSearch: (value: string) => void;
  teamSearch: string;
  setTeamSearch: (value: string) => void;
  divisionFilter: string;
  setDivisionFilter: (value: string) => void;
  sectionFilter: string;
  setSectionFilter: (value: string) => void;
  debugMode: boolean;
  setDebugMode: (value: boolean) => void;
}

const FilterContext = createContext<FilterState | null>(null);

export function FilterProvider({
  weightClasses,
  children,
}: {
  weightClasses: string[];
  children: React.ReactNode;
}) {
  const [weightClass, setWeightClass] = useState(weightClasses[0] ?? '');
  const [wrestlerSearch, setWrestlerSearch] = useState('');
  const [teamSearch, setTeamSearch] = useState('');
  const [divisionFilter, setDivisionFilter] = useState('all');
  const [sectionFilter, setSectionFilter] = useState('all');
  const [debugMode, setDebugMode] = usePersistedBoolean('leaderboard-debug', false);

  const value = useMemo(
    () => ({
      weightClass,
      setWeightClass,
      wrestlerSearch,
      setWrestlerSearch,
      teamSearch,
      setTeamSearch,
      divisionFilter,
      setDivisionFilter,
      sectionFilter,
      setSectionFilter,
      debugMode,
      setDebugMode,
    }),
    [
      weightClass,
      wrestlerSearch,
      teamSearch,
      divisionFilter,
      sectionFilter,
      debugMode,
      setWeightClass,
      setWrestlerSearch,
      setTeamSearch,
      setDivisionFilter,
      setSectionFilter,
      setDebugMode,
    ]
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFilters() {
  const ctx = useContext(FilterContext);
  if (!ctx) {
    throw new Error('useFilters must be used inside FilterProvider');
  }
  return ctx;
}
