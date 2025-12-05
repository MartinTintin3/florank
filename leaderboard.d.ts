type WeightClass = string;
export type WrestlerId = string;
export type TeamId = string;

export interface LeaderboardOverrides {
  /** Per-wrestler weight-class overrides, or null if none applied */
  weights: Record<WrestlerId, WeightClass> | null;
  /** Wrestler IDs excluded from the leaderboard, or null if none */
  exclude: string[] | null;
  /** Grad-year overrides keyed by wrestler, or null if unused */
  gradYears: Record<WrestlerId, number> | null;
  /** Forcing specific team IDs per wrestler, or null if not used */
  teams: Record<WrestlerId, TeamId> | null;
}

export interface SectionDivisionData {
  /** Sections present in this leaderboard payload */
  sections: string[];
  /** Divisions present in this leaderboard payload */
  divisions: number[];
}

export interface WrestlerEntry {
  /** Wrestler unique ID */
  id: WrestlerId;
  /** Display name */
  name: string;
  /** Team association (null if unknown) */
  teamId: TeamId | null;
  /** Graduation year (null if unknown) */
  gradYear: number | null;
  /** Glicko rating (rounded to two decimals) */
  rating: number;
  /** Rating deviation (RD), rounded to two decimals */
  rd: number;
  /** Volatility (sigma), rounded to four decimals */
  sigma: number;
  /** Total wins accumulated in the processed matches */
  wins: number;
  /** Total losses accumulated in the processed matches */
  losses: number;
}

export interface TeamEntry {
  /** Team unique ID */
  id: TeamId;
  /** Team name (null if not available) */
  name: string | null;
  /** Section label (null if unknown) */
  section: string | null;
  /** Division number (null if unknown) */
  division: number | null;
  /** Weight-class map listing wrestler IDs for that team */
  weights: Record<WeightClass, WrestlerId[]>;
}

export type WeightRankings = Record<WeightClass, WrestlerId[]>;

export interface LeaderboardPayload {
  /** Tau value used for the simulation */
  tau: number;
  /** Total matches processed */
  matches: number;
  /** Number of rating periods simulated */
  periods: number;
  /** Optional CLI grad-year filter applied to the run */
  gradYear: number | null;
  /** Overrides captured from input files/flags */
  overrides: LeaderboardOverrides;
  /** Unique sections and divisions represented */
  sectionDivisionData: SectionDivisionData;
  /** Flattened roster of wrestlers with ratings and records */
  wrestlers: WrestlerEntry[];
  /** Teams with metadata plus per-weight wrestler IDs */
  teams: TeamEntry[];
  /** Weight-class rankings listing wrestler IDs in order */
  weights: WeightRankings;
}
