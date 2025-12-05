import { useMemo } from 'react';
import { Alert } from '@mantine/core';
import type { LeaderboardPayload, TeamEntry, WrestlerEntry } from '../types/leaderboard';
import { useFilters } from '../context/FilterContext';
import { RankingTable, type RankingRow } from '../components/RankingTable';
import { DivisionSectionControls } from '../components/DivisionSectionControls';

interface Props {
  data: LeaderboardPayload;
  wrestlersById: Record<string, WrestlerEntry>;
  teamsById: Record<string, TeamEntry>;
  divisions: number[];
}

export function DivisionView({ data, wrestlersById, teamsById, divisions }: Props) {
  const { divisionFilter, weightClass, wrestlerSearch, teamSearch, debugMode } = useFilters();

  const rows = useMemo<RankingRow[]>(() => {
    if (divisionFilter === 'all') return [];
    const ranking = data.weights[weightClass] ?? [];
    const wrestlerQuery = wrestlerSearch.trim().toLowerCase();
    const teamQuery = teamSearch.trim().toLowerCase();

    let rows = ranking
      .map((id, index) => {
        const wrestler = wrestlersById[id];
        if (!wrestler || !wrestler.teamId) return null;
        const team = teamsById[wrestler.teamId];
        if (!team || String(team.division) !== divisionFilter) return null;
        return { rank: index + 1, wrestler, team } satisfies RankingRow;
      })
      .filter(Boolean) as RankingRow[];

    if (wrestlerQuery) {
      rows = rows.filter((row) => row.wrestler.name.toLowerCase().includes(wrestlerQuery));
    }
    if (teamQuery) {
      rows = rows.filter((row) => (row.team?.name ?? '').toLowerCase().includes(teamQuery));
    }

    return rows;
  }, [data, divisionFilter, weightClass, wrestlersById, teamsById, wrestlerSearch, teamSearch]);

  return (
    <>
      <DivisionSectionControls divisions={divisions} sections={[]} showSection={false} />
      {divisionFilter === 'all' ? (
        <Alert variant="light" color="blue">
          Select a division to view rankings for the active weight class.
        </Alert>
      ) : (
        <RankingTable rows={rows} debugMode={debugMode} />
      )}
    </>
  );
}
