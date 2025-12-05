import { Group, Select } from '@mantine/core';
import { useFilters } from '../context/FilterContext';

interface Props {
  divisions: number[];
  sections: string[];
  showDivision?: boolean;
  showSection?: boolean;
}

export function DivisionSectionControls({
  divisions,
  sections,
  showDivision = true,
  showSection = true,
}: Props) {
  const { divisionFilter, setDivisionFilter, sectionFilter, setSectionFilter } = useFilters();

  return (
    <Group gap="md" wrap="wrap" my="md">
      {showDivision && (
        <Select
          label="Division"
          placeholder="All divisions"
          data={divisions.map((div) => ({ label: `Division ${div}`, value: String(div) }))}
          value={divisionFilter === 'all' ? null : divisionFilter}
          onChange={(value) => setDivisionFilter(value ?? 'all')}
          clearable
          w={200}
        />
      )}
      {showSection && (
        <Select
          label="Section"
          placeholder="All sections"
          data={sections.map((section) => ({ label: section, value: section }))}
          value={sectionFilter === 'all' ? null : sectionFilter}
          onChange={(value) => setSectionFilter(value ?? 'all')}
          clearable
          w={220}
        />
      )}
    </Group>
  );
}
