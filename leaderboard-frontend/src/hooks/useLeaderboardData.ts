import { useEffect, useMemo, useState } from 'react';
import type { LeaderboardPayload, TeamEntry, WrestlerEntry } from '../types/leaderboard';

interface LeaderboardState {
  data: LeaderboardPayload | null;
  loading: boolean;
  error: string | null;
  weightClasses: string[];
  divisions: number[];
  sections: string[];
  wrestlersById: Record<string, WrestlerEntry>;
  teamsById: Record<string, TeamEntry>;
}

export function useLeaderboardData(): LeaderboardState {
  const [data, setData] = useState<LeaderboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/leaderboard.json')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load leaderboard.json (${response.status})`);
        }
        return response.json();
      })
      .then((payload: LeaderboardPayload) => {
        setData(payload);
      })
      .catch((err) => {
        setError(err.message);
      });
  }, []);

  const weightClasses = useMemo(() => Object.keys(data?.weights ?? {}), [data]);
  const divisions = useMemo(() => data?.sectionDivisionData.divisions ?? [], [data]);
  const sections = useMemo(() => data?.sectionDivisionData.sections ?? [], [data]);

  const wrestlersById = useMemo(() => {
    if (!data) return {};
    return Object.fromEntries(data.wrestlers.map((wrestler) => [wrestler.id, wrestler]));
  }, [data]);

  const teamsById = useMemo(() => {
    if (!data) return {};
    return Object.fromEntries(data.teams.map((team) => [team.id, team]));
  }, [data]);

  return {
    data,
    loading: !data && !error,
    error,
    weightClasses,
    divisions,
    sections,
    wrestlersById,
    teamsById,
  };
}
