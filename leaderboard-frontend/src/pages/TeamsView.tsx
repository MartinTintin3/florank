import { Alert } from '@mantine/core';
import { useMemo } from 'react';
import type { LeaderboardPayload, WrestlerEntry } from '../types/leaderboard';
import { useFilters } from '../context/FilterContext';
import { DivisionSectionControls } from '../components/DivisionSectionControls';
import { TeamList } from '../components/TeamList';

interface Props {
  data: LeaderboardPayload;
  divisions: number[];
  sections: string[];
  wrestlersById: Record<string, WrestlerEntry>;
}

export function TeamsView({ data, divisions, sections, wrestlersById }: Props) {
  const { divisionFilter, sectionFilter, wrestlerSearch, teamSearch, debugMode } = useFilters();

  const teams = useMemo(() => {
    const wrestlerQuery = wrestlerSearch.trim().toLowerCase();
    const teamQuery = teamSearch.trim().toLowerCase();
    return data.teams.filter((team) => {
      if (divisionFilter !== 'all' && String(team.division) !== divisionFilter) return false;
      if (sectionFilter !== 'all' && team.section !== sectionFilter) return false;
      if (teamQuery && !(team.name ?? '').toLowerCase().includes(teamQuery)) {
        return false;
      }
      if (!wrestlerQuery) {
        return true;
      }
      const rosterMatch = Object.values(team.weights ?? {}).some((ids) =>
        ids.some((id) => {
          const wrestlerName = wrestlersById[id]?.name;
          return wrestlerName ? wrestlerName.toLowerCase().includes(wrestlerQuery) : false;
        })
      );
      return rosterMatch;
    });
  }, [data.teams, divisionFilter, sectionFilter, wrestlerSearch, teamSearch, wrestlersById]);

  return (
    <>
      <Alert variant="light" color="yellow" mb="sm">
        Team rosters intentionally ignore the global weight-class filter so you can scout the full
        lineup. Use the division/section filters here if you need to narrow teams down.
      </Alert>
      <DivisionSectionControls divisions={divisions} sections={sections} />
      <TeamList teams={teams} wrestlersById={wrestlersById} debugMode={debugMode} />
    </>
  );
}
