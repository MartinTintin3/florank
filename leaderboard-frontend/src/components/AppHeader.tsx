import { ActionIcon, Group, Select, Stack, Switch, Text, TextInput, Title, Tooltip, rem } from '@mantine/core';
import { IconMoon, IconSearch, IconSun } from '@tabler/icons-react';
import { useMantineColorScheme } from '@mantine/core';
import { useFilters } from '../context/FilterContext';

interface AppHeaderProps {
  weightClasses: string[];
  activePage: 'rankings' | 'teams';
}

export function AppHeader({ weightClasses, activePage }: AppHeaderProps) {
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  const {
    weightClass,
    setWeightClass,
    wrestlerSearch,
    setWrestlerSearch,
    teamSearch,
    setTeamSearch,
    debugMode,
    setDebugMode,
  } = useFilters();
  const isTeamsPage = activePage === 'teams';
  const wrestlerPlaceholder = isTeamsPage ? 'Search rosters for a wrestler' : 'Enter wrestler name';
  const teamPlaceholder = isTeamsPage ? 'Enter team name' : 'Filter by team name';

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <div>
          <Title order={2}>MA Wrestling Leaderboard</Title>
          <Text size="sm" c="dimmed">
            Interactive statewide rankings powered by precomputed Glicko data.
          </Text>
        </div>
        <Group gap="xs">
          <Tooltip label="Toggle color scheme" withArrow>
            <ActionIcon
              variant="subtle"
              size="lg"
              onClick={() => setColorScheme(colorScheme === 'dark' ? 'light' : 'dark')}
            >
              {colorScheme === 'dark' ? (
                <IconSun style={{ width: rem(18), height: rem(18) }} />
              ) : (
                <IconMoon style={{ width: rem(18), height: rem(18) }} />
              )}
            </ActionIcon>
          </Tooltip>
          <Switch
            label="Debug mode"
            checked={debugMode}
            onChange={(event) => setDebugMode(event.currentTarget.checked)}
          />
        </Group>
      </Group>

      <Group gap="md" wrap="wrap">
        <Select
          label="Weight class"
          placeholder="Select weight"
          data={weightClasses}
          value={weightClass}
          onChange={(value) => value && setWeightClass(value)}
          allowDeselect={false}
          w={200}
        />
        <TextInput
          label="Search wrestlers"
          placeholder={wrestlerPlaceholder}
          leftSection={<IconSearch size={16} />}
          value={wrestlerSearch}
          onChange={(event) => setWrestlerSearch(event.currentTarget.value)}
          w={240}
        />
        <TextInput
          label="Search teams"
          placeholder={teamPlaceholder}
          leftSection={<IconSearch size={16} />}
          value={teamSearch}
          onChange={(event) => setTeamSearch(event.currentTarget.value)}
          w={240}
        />
      </Group>
    </Stack>
  );
}
