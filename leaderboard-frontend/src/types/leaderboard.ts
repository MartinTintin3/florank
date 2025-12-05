export type WeightClass = string;
export type WrestlerId = string;
export type TeamId = string;

export interface LeaderboardOverrides {
  weights: Record<WrestlerId, WeightClass> | null;
  exclude: string[] | null;
  gradYears: Record<WrestlerId, number> | null;
  teams: Record<WrestlerId, TeamId> | null;
}

export interface SectionDivisionData {
  sections: string[];
  divisions: number[];
}

export interface WrestlerEntry {
  id: WrestlerId;
  name: string;
  teamId: TeamId | null;
  gradYear: number | null;
  rating: number;
  rd: number;
  sigma: number;
  wins: number;
  losses: number;
}

export interface TeamEntry {
  id: TeamId;
  name: string | null;
  section: string | null;
  division: number | null;
  weights: Record<WeightClass, WrestlerId[]>;
}

export type WeightRankings = Record<WeightClass, WrestlerId[]>;

export interface LeaderboardPayload {
  tau: number;
  matches: number;
  periods: number;
  gradYear: number | null;
  overrides: LeaderboardOverrides;
  sectionDivisionData: SectionDivisionData;
  wrestlers: WrestlerEntry[];
  teams: TeamEntry[];
  weights: WeightRankings;
}
