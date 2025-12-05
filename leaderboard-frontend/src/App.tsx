import { useState } from 'react';
import { AppShell, Container, Loader, Tabs, Text } from '@mantine/core';
import { AppHeader } from './components/AppHeader';
import { useLeaderboardData } from './hooks/useLeaderboardData';
import { FilterProvider } from './context/FilterContext';
import { AllStateView } from './pages/AllStateView';
import { DivisionView } from './pages/DivisionView';
import { SectionView } from './pages/SectionView';
import { TeamsView } from './pages/TeamsView';

function App() {
  const {
    data,
    loading,
    error,
    weightClasses,
    divisions,
    sections,
    wrestlersById,
    teamsById,
  } = useLeaderboardData();
  const [activePage, setActivePage] = useState<'rankings' | 'teams'>('rankings');
  const [rankingsTab, setRankingsTab] = useState<'all-state' | 'division' | 'section'>('all-state');

  const handlePageChange = (value: string | null) => {
    if (value === 'teams') {
      setActivePage('teams');
      return;
    }
    setActivePage('rankings');
  };

  const handleRankingsTabChange = (value: string | null) => {
    if (value === 'division' || value === 'section') {
      setRankingsTab(value);
      return;
    }
    setRankingsTab('all-state');
  };

  if (loading) {
    return (
      <Container py="xl">
        <Loader />
      </Container>
    );
  }

  if (error || !data) {
    return (
      <Container py="xl">
        <Text c="red">{error ?? 'Unable to load leaderboard data.'}</Text>
      </Container>
    );
  }

  if (!weightClasses.length) {
    return (
      <Container py="xl">
        <Text>No weight classes were found in leaderboard.json.</Text>
      </Container>
    );
  }

  return (
    <FilterProvider weightClasses={weightClasses}>
      <AppShell padding="md">
        <AppShell.Main>
          <Container py="sm">
            <AppHeader weightClasses={weightClasses} activePage={activePage} />
          </Container>
          <Container py="md">
            <Tabs value={activePage} onChange={handlePageChange} keepMounted={false}>
              <Tabs.List mb="md">
                <Tabs.Tab value="rankings">Rankings</Tabs.Tab>
                <Tabs.Tab value="teams">Teams</Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="rankings" pt="sm">
                <Tabs value={rankingsTab} onChange={handleRankingsTabChange} keepMounted={false}>
                  <Tabs.List mb="md">
                    <Tabs.Tab value="all-state">All-State</Tabs.Tab>
                    <Tabs.Tab value="division">Divisions</Tabs.Tab>
                    <Tabs.Tab value="section">Sections</Tabs.Tab>
                  </Tabs.List>

                  <Tabs.Panel value="all-state" pt="sm">
                    <AllStateView data={data} wrestlersById={wrestlersById} teamsById={teamsById} />
                  </Tabs.Panel>

                  <Tabs.Panel value="division" pt="sm">
                    <DivisionView
                      data={data}
                      wrestlersById={wrestlersById}
                      teamsById={teamsById}
                      divisions={divisions}
                    />

                  </Tabs.Panel>

                  <Tabs.Panel value="section" pt="sm">
                    <SectionView
                      data={data}
                      wrestlersById={wrestlersById}
                      teamsById={teamsById}
                      sections={sections}
                    />
                  </Tabs.Panel>
                </Tabs>
              </Tabs.Panel>

              <Tabs.Panel value="teams" pt="sm">
                <TeamsView
                  data={data}
                  divisions={divisions}
                  sections={sections}
                  wrestlersById={wrestlersById}
                />
              </Tabs.Panel>
            </Tabs>
          </Container>
        </AppShell.Main>
      </AppShell>
    </FilterProvider>
  );
}

export default App;
