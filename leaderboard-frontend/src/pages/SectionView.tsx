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
  sections: string[];
}

export function SectionView({ data, wrestlersById, teamsById, sections }: Props) {
  const { sectionFilter, weightClass, wrestlerSearch, teamSearch, debugMode } = useFilters();

  const rows = useMemo<RankingRow[]>(() => {
    if (sectionFilter === 'all') return [];
    const ranking = data.weights[weightClass] ?? [];
    const wrestlerQuery = wrestlerSearch.trim().toLowerCase();
    const teamQuery = teamSearch.trim().toLowerCase();

    let rows = ranking
      .map((id, index) => {
        const wrestler = wrestlersById[id];
        if (!wrestler || !wrestler.teamId) return null;
        const team = teamsById[wrestler.teamId];
        if (!team || team.section !== sectionFilter) return null;
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
  }, [data, sectionFilter, weightClass, wrestlersById, teamsById, wrestlerSearch, teamSearch]);

  return (
    <>
      <DivisionSectionControls sections={sections} divisions={[]} showDivision={false} />
      {sectionFilter === 'all' ? (
        <Alert variant="light" color="blue">
          Select a section to view rankings for the active weight class.
        </Alert>
      ) : (
        <RankingTable rows={rows} debugMode={debugMode} />
      )}
    </>
  );
}
