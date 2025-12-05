# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  # Leaderboard Frontend

  This is the Vite + React + TypeScript frontend for viewing the wrestling leaderboard produced by the backend (`leaderboard.json`). It uses Mantine for UI components and theming and is optimized for client-side filtering and rendering of ~2,500 wrestlers and ~150 teams.

  ## Quick start

  1. Copy the generated `leaderboard.json` into `public/leaderboard.json`.
  2. Run the dev server:

  ```bash
  npm run dev
  ```

  ## Project structure

  ```
  src/
  ├─ main.tsx                 # app entry, Mantine provider + theme
  ├─ App.tsx                  # main layout + tab navigation
  ├─ theme.ts                 # Mantine theme (dark-first)
  ├─ types/leaderboard.ts     # TS types (LeaderboardPayload)
  ├─ hooks/
  │  ├─ useLeaderboardData.ts # fetch leaderboard.json and memoize maps
  │  └─ usePersistedBoolean.ts# small localStorage-backed boolean hook
  ├─ context/
  │  └─ FilterContext.tsx     # global filters + debug mode, provided to app
  ├─ components/
  │  ├─ AppHeader.tsx         # header, weight selector, search, debug toggle
  │  ├─ DivisionSectionControls.tsx
  │  ├─ RankingTable.tsx      # reusable ranking table
  │  └─ TeamList.tsx          # team roster UI (ignores global weight filter)
  └─ pages/
     ├─ AllStateView.tsx
     ├─ DivisionView.tsx
     ├─ SectionView.tsx
     └─ TeamsView.tsx
  ```

  ## Important behavior

  - Global weight-class filtering: The weight selector in the header is the primary filter for ranking-focused views (All-State, Division, Section). Those views read `data.weights[selectedWeight]` and then apply optional division/section filters and search.
  - Teams view exception: The Teams page intentionally ignores the global weight-class filter and instead shows each team's full roster across all weight classes. The UI shows an explanatory alert when viewing Teams.
  - Dark Mode: The app defaults to Dark Mode via Mantine. Users can toggle between dark and light using the header control.
  - Debug Mode: A prominent header switch toggles Debug Mode (persisted in `localStorage`). When ON, internal IDs and RD/sigma values are visible in tables and team cards; when OFF, those internal details are hidden.

  ## Performance notes

  - The data hook memoizes lookups (wrestlersById, teamsById). Views use `useMemo` to compute filtered lists and sorting to avoid unnecessary recomputation on unrelated state changes.
  - Tables use Mantine's `ScrollArea` to keep large lists performant and responsive.

  If you want, I can now:
  - Add small enhancements like client-side pagination or virtualization for extra-large datasets.
  - Add an exported static HTML snapshot of a selected view.
