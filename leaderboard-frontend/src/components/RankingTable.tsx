import { Box, ScrollArea, Table, Text } from '@mantine/core';
import type { TeamEntry, WrestlerEntry } from '../types/leaderboard';

export interface RankingRow {
  rank: number;
  wrestler: WrestlerEntry;
  team: TeamEntry | undefined;
}

interface RankingTableProps {
  rows: RankingRow[];
  debugMode: boolean;
}

export function RankingTable({ rows, debugMode }: RankingTableProps) {
  if (!rows.length) {
    return (
      <Box py="lg">
        <Text c="dimmed">No wrestlers match the active filters.</Text>
      </Box>
    );
  }

  return (
    <ScrollArea>
      <Table striped highlightOnHover withRowBorders={false} miw={720}>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>#</Table.Th>
            <Table.Th>Wrestler</Table.Th>
            <Table.Th>Team</Table.Th>
            <Table.Th>Division</Table.Th>
            <Table.Th>Section</Table.Th>
            {!debugMode ? null : (
              <>
                <Table.Th ta="right">RD</Table.Th>
                <Table.Th ta="right">Sigma</Table.Th>
              </>
            )}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row) => (
            <Table.Tr key={`${row.wrestler.id}-${row.rank}`}>
              <Table.Td>{row.rank}</Table.Td>
              <Table.Td>
                <Text fw={600}>{row.wrestler.name}</Text>
                <Text size="sm" c="dimmed">
                  Record{' '}
                  <Text component="span" c="green.5" fw={600}>
                    {row.wrestler.wins}
                  </Text>
                  -
                  <Text component="span" c="red.5" fw={600}>
                    {row.wrestler.losses}
                  </Text>
                </Text>
                {debugMode && (
                  <>
                    <Text size="xs" c="dimmed">
                      Rating {row.wrestler.rating.toFixed(1)} · Wrestler ID: {row.wrestler.id}
                    </Text>
                  </>
                )}
              </Table.Td>
              <Table.Td>
                {row.team?.name ?? '—'}
                {debugMode && row.team?.id && (
                  <Text size="xs" c="dimmed">
                    Team ID: {row.team.id}
                  </Text>
                )}
              </Table.Td>
              <Table.Td>{row.team?.division ?? '—'}</Table.Td>
              <Table.Td>{row.team?.section ?? '—'}</Table.Td>
              {!debugMode ? null : (
                <>
                  <Table.Td ta="right">{row.wrestler.rd.toFixed(1)}</Table.Td>
                  <Table.Td ta="right">{row.wrestler.sigma.toFixed(3)}</Table.Td>
                </>
              )}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </ScrollArea>
  );
}
