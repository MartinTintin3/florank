import { useMemo } from 'react';
import type { LeaderboardPayload, TeamEntry, WrestlerEntry } from '../types/leaderboard';
import { useFilters } from '../context/FilterContext';
import { RankingTable, type RankingRow } from '../components/RankingTable';

interface Props {
  data: LeaderboardPayload;
  wrestlersById: Record<string, WrestlerEntry>;
  teamsById: Record<string, TeamEntry>;
}

export function AllStateView({ data, wrestlersById, teamsById }: Props) {
  const { weightClass, wrestlerSearch, teamSearch, divisionFilter, sectionFilter, debugMode } = useFilters();

  const rows = useMemo<RankingRow[]>(() => {
    const ranking = data.weights[weightClass] ?? [];
    const wrestlerQuery = wrestlerSearch.trim().toLowerCase();
    const teamQuery = teamSearch.trim().toLowerCase();

    let rows = ranking
      .map((id, index) => {
        const wrestler = wrestlersById[id];
        if (!wrestler) return null;
        const team = wrestler.teamId ? teamsById[wrestler.teamId] : undefined;
        return { rank: index + 1, wrestler, team } satisfies RankingRow;
      })
      .filter(Boolean) as RankingRow[];

    if (wrestlerQuery) {
      rows = rows.filter((row) => row.wrestler.name.toLowerCase().includes(wrestlerQuery));
    }
    if (teamQuery) {
      rows = rows.filter((row) => (row.team?.name ?? '').toLowerCase().includes(teamQuery));
    }
    if (divisionFilter !== 'all') {
      rows = rows.filter((row) => String(row.team?.division) === divisionFilter);
    }
    if (sectionFilter !== 'all') {
      rows = rows.filter((row) => row.team?.section === sectionFilter);
    }

    return rows;
  }, [data, weightClass, wrestlersById, teamsById, wrestlerSearch, teamSearch, divisionFilter, sectionFilter]);

  return <RankingTable rows={rows} debugMode={debugMode} />;
}
