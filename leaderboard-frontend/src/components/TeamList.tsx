import { Accordion, Badge, Card, Group, Stack, Text, Title } from '@mantine/core';
import type { TeamEntry, WrestlerEntry } from '../types/leaderboard';

interface TeamListProps {
  teams: TeamEntry[];
  wrestlersById: Record<string, WrestlerEntry>;
  debugMode: boolean;
}

export function TeamList({ teams, wrestlersById, debugMode }: TeamListProps) {
  if (!teams.length) {
    return (
      <Text c="dimmed" mt="md">
        No teams match the selected filters.
      </Text>
    );
  }

  return (
    <Accordion multiple chevronPosition="right">
      {teams.map((team) => (
        <Accordion.Item key={team.id} value={team.id}>
          <Accordion.Control>
            <Group justify="space-between" wrap="wrap">
              <div>
                <Title order={4}>{team.name ?? 'Unknown team'}</Title>
                <Text size="sm" c="dimmed">
                  Division {team.division ?? '—'} · {team.section ?? '—'}
                </Text>
                {debugMode && team.id && (
                  <Text size="xs" c="dimmed">
                    Team ID: {team.id}
                  </Text>
                )}
              </div>
              <Badge variant="light">{Object.keys(team.weights ?? {}).length} weights</Badge>
            </Group>
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="sm">
              {Object.entries(team.weights ?? {})
                .sort(([a], [b]) => {
                  const weightA = Number(a);
                  const weightB = Number(b);
                  if (Number.isNaN(weightA) || Number.isNaN(weightB)) {
                    return a.localeCompare(b);
                  }
                  return weightA - weightB;
                })
                .map(([weight, wrestlerIds]) => (
                  <Card key={weight} withBorder>
                    <Group justify="space-between" mb="xs">
                      <Text fw={600}>{weight} lbs</Text>
                      <Badge>{wrestlerIds.length} ranked</Badge>
                    </Group>
                    <Stack gap={4}>
                      {wrestlerIds.map((id) => {
                        const wrestler = wrestlersById[id];
                        if (!wrestler) return null;
                        return (
                          <Group key={id} justify="space-between" wrap="wrap">
                            <div>
                              <Text>{wrestler.name}</Text>
                              <Text size="sm" c="dimmed">
                                Record {wrestler.wins}-{wrestler.losses}
                              </Text>
                              {debugMode && (
                                <Text size="xs" c="dimmed">
                                  Rating {wrestler.rating.toFixed(1)} · Wrestler ID: {wrestler.id} · RD {wrestler.rd.toFixed(1)} · σ {wrestler.sigma.toFixed(3)}
                                </Text>
                              )}
                            </div>
                          </Group>
                        );
                      })}
                    </Stack>
                  </Card>
                ))}
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion>
  );
}
