"""Glicko-2 ratings and leaderboards for active wrestlers."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import cmp_to_key
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import utils


SCALE = 173.7178
DEFAULT_RATING = 1500.0
DEFAULT_RD = 350.0
DEFAULT_SIGMA = 0.06
MAX_RD = 350.0
MIN_RD = 30.0
SEASON_RD_FLOOR = 150.0
RECENT_WEIGHT_MATCHES = 5

DEFAULT_WEIGHT_CLASSES = [
	"106",
	"113",
	"120",
	"126",
	"132",
	"138",
	"144",
	"150",
	"157",
	"165",
	"175",
	"190",
	"215",
	"285",
]

WIN_TYPE_WEIGHTS: Mapping[str, float] = {
	"F": 1.0,
	"TF": 0.9,
	"MD": 0.8,
	"DEC": 0.7,
}
DEFAULT_OTHER_WEIGHT = 0.65
DEFAULT_TAU_CANDIDATES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7]


@dataclass
class RatingPeriod:
	start: datetime
	end: datetime
	season: str


@dataclass
class MatchResult:
	id: str
	date: datetime
	top_id: str
	bottom_id: str
	winner_id: str | None
	win_type: str | None
	weight_class: str | None


@dataclass
class Glicko2State:
	rating: float = DEFAULT_RATING
	rd: float = DEFAULT_RD
	sigma: float = DEFAULT_SIGMA


@dataclass
class RatingRunResult:
	ratings: dict[str, Glicko2State]
	head_to_head: dict[tuple[str, str], int]
	weight_counts: dict[str, Counter[str]]
	predictions: list[tuple[float, float]]


class Glicko2:
	def __init__(
		self,
		tau: float,
		win_type_weights: Mapping[str, float] | None = None,
		min_rd: float = MIN_RD,
		max_rd: float = MAX_RD,
		season_rd_floor: float = SEASON_RD_FLOOR,
		weight_history_limit: int = RECENT_WEIGHT_MATCHES,
	):
		self.tau = tau
		self.win_type_weights = win_type_weights or WIN_TYPE_WEIGHTS
		self.min_rd = min_rd
		self.max_rd = max_rd
		self.season_rd_floor = season_rd_floor
		self.weight_history_limit = max(1, weight_history_limit)
		self.states: dict[str, Glicko2State] = {}
		self.weight_history: defaultdict[str, list[str]] = defaultdict(list)

	def ensure_player(self, wrestler_id: str) -> None:
		if wrestler_id not in self.states:
			self.states[wrestler_id] = Glicko2State()

	def _g(self, phi: float) -> float:
		return 1 / math.sqrt(1 + 3 * (phi ** 2) / (math.pi ** 2))

	def _expected(self, mu: float, mu_j: float, phi_j: float) -> float:
		return 1 / (1 + math.exp(-self._g(phi_j) * (mu - mu_j)))

	def win_probability(self, player: Glicko2State, opponent: Glicko2State) -> float:
		mu = (player.rating - DEFAULT_RATING) / SCALE
		mu_j = (opponent.rating - DEFAULT_RATING) / SCALE
		phi_j = opponent.rd / SCALE
		return self._expected(mu, mu_j, phi_j)

	def _win_weight(self, win_type: str | None) -> float:
		key = (win_type or "").upper()
		return self.win_type_weights.get(key, DEFAULT_OTHER_WEIGHT)

	def inflate_for_gap(self, months: float) -> None:
		if months <= 0:
			return
		for state in self.states.values():
			phi = state.rd / SCALE
			phi = math.sqrt(phi * phi + months * state.sigma * state.sigma)
			state.rd = min(self.max_rd, max(self.min_rd, phi * SCALE))

	def reset_rd_for_season(self) -> None:
		"""Increase RD to ensure more volatility heading into a new season."""
		floor = max(self.min_rd, min(self.max_rd, self.season_rd_floor))
		for state in self.states.values():
			state.rd = min(self.max_rd, max(state.rd, floor))

	def _record_weight_class(
		self,
		wrestler_id: str,
		weight_class: str | None,
		weight_counts: defaultdict[str, Counter[str]],
	) -> None:
		if not weight_class:
			return
		history = self.weight_history[wrestler_id]
		history.append(weight_class)
		weight_counts[wrestler_id][weight_class] += 1
		if len(history) > self.weight_history_limit:
			removed = history.pop(0)
			weight_counts[wrestler_id][removed] -= 1
			if weight_counts[wrestler_id][removed] <= 0:
				del weight_counts[wrestler_id][removed]

	def _update_player(
		self,
		player: Glicko2State,
		results: Sequence[tuple[Glicko2State, float, float]],
	) -> Glicko2State:
		mu = (player.rating - DEFAULT_RATING) / SCALE
		phi = player.rd / SCALE
		phi_star = math.sqrt(phi * phi + player.sigma * player.sigma)

		if not results:
			return Glicko2State(
				rating=player.rating,
				rd=min(self.max_rd, max(self.min_rd, phi_star * SCALE)),
				sigma=player.sigma,
			)

		v_inv = 0.0
		delta_sum = 0.0

		for opponent, score, weight in results:
			mu_j = (opponent.rating - DEFAULT_RATING) / SCALE
			phi_j = opponent.rd / SCALE
			g_phi = self._g(phi_j)
			E = self._expected(mu, mu_j, phi_j)
			v_inv += weight * (g_phi ** 2) * E * (1 - E)
			delta_sum += weight * g_phi * (score - E)

		if v_inv == 0:
			return Glicko2State(
				rating=player.rating,
				rd=min(self.max_rd, max(self.min_rd, phi_star * SCALE)),
				sigma=player.sigma,
			)

		v = 1.0 / v_inv
		delta = v * delta_sum

		a = math.log(player.sigma ** 2)

		def f(x: float) -> float:
			exp_x = math.exp(x)
			num = exp_x * (delta ** 2 - phi_star ** 2 - v - exp_x)
			denom = 2 * (phi_star ** 2 + v + exp_x) ** 2
			return (num / denom) - ((x - a) / (self.tau ** 2))

		A = a
		if delta ** 2 > phi_star ** 2 + v:
			B = math.log(delta ** 2 - phi_star ** 2 - v)
		else:
			k = 1
			while f(a - k * self.tau) < 0:
				k += 1
			B = a - k * self.tau

		fA = f(A)
		fB = f(B)

		while abs(B - A) > 1e-6:
			C = A + (A - B) * fA / (fB - fA)
			fC = f(C)
			if fC * fB < 0:
				A = B
				fA = fB
			else:
				fA = fA / 2
			B = C
			fB = fC

		sigma_prime = math.exp(A / 2)
		phi_prime = 1 / math.sqrt(1 / (phi_star ** 2 + sigma_prime ** 2) + 1 / v)
		mu_prime = mu + (phi_prime ** 2) * delta_sum

		return Glicko2State(
			rating=DEFAULT_RATING + mu_prime * SCALE,
			rd=min(self.max_rd, max(self.min_rd, phi_prime * SCALE)),
			sigma=sigma_prime,
		)

	def process_period(
		self,
		matches: Sequence[MatchResult],
		head_to_head: defaultdict[tuple[str, str], int],
		weight_counts: defaultdict[str, Counter[str]],
	) -> list[tuple[float, float]]:
		results_by_player: dict[str, list[tuple[Glicko2State, float, float]]] = defaultdict(list)
		predictions: list[tuple[float, float]] = []

		for match in matches:
			if match.winner_id not in (match.top_id, match.bottom_id):
				continue

			self.ensure_player(match.top_id)
			self.ensure_player(match.bottom_id)

			self._record_weight_class(match.top_id, match.weight_class, weight_counts)
			self._record_weight_class(match.bottom_id, match.weight_class, weight_counts)

			top_state = self.states[match.top_id]
			bottom_state = self.states[match.bottom_id]
			prob_top = self.win_probability(top_state, bottom_state)
			actual_top = 1.0 if match.winner_id == match.top_id else 0.0
			predictions.append((prob_top, actual_top))

			weight = self._win_weight(match.win_type)
			results_by_player[match.top_id].append((bottom_state, actual_top, weight))
			results_by_player[match.bottom_id].append((top_state, 1.0 - actual_top, weight))

			loser = match.bottom_id if match.winner_id == match.top_id else match.top_id
			head_to_head[(match.winner_id, loser)] += 1

		new_states: dict[str, Glicko2State] = {}
		for wrestler_id, state in self.states.items():
			new_states[wrestler_id] = self._update_player(
				state,
				results_by_player.get(wrestler_id, []),
			)

		self.states = new_states
		return predictions


def months_between(first: datetime, second: datetime) -> float:
	"""Approximate month gap between two datetimes."""
	if second <= first:
		return 0.0
	days = (second - first).total_seconds() / 86400.0
	return days / 30.0


def build_periods(
	seasons: Sequence[Mapping],
	season_filter: set[str] | None,
	start_override: datetime | None,
	end_override: datetime | None,
) -> list[RatingPeriod]:
	periods: list[RatingPeriod] = []
	now = datetime.now(timezone.utc)

	for season in seasons:
		season_name = season.get("name", "unknown")
		if season_filter and season_name not in season_filter:
			continue

		regular = season.get("regular", {})
		post = season.get("post", {})
		start_raw = regular.get("start_date")
		end_raw = post.get("end_date")
		if not start_raw or not end_raw:
			continue

		season_start = utils.parse_date(start_raw).astimezone(timezone.utc)
		season_end = utils.parse_date(end_raw).astimezone(timezone.utc) + timedelta(days=1)

		if start_override:
			season_start = max(season_start, start_override)
		if end_override:
			season_end = min(season_end, end_override)

		season_end = min(season_end, now)

		if season_start >= season_end:
			continue

		for start, end in utils.month_periods(season_start, season_end):
			periods.append(RatingPeriod(start=start, end=end, season=season_name))

	return periods


def bucket_matches(periods: Sequence[RatingPeriod], matches: Sequence[MatchResult]) -> list[list[MatchResult]]:
	buckets: list[list[MatchResult]] = [[] for _ in periods]
	if not periods:
		return buckets

	period_idx = 0
	for match in matches:
		while period_idx < len(periods) and match.date >= periods[period_idx].end:
			period_idx += 1
		if period_idx >= len(periods):
			break
		if match.date >= periods[period_idx].start:
			buckets[period_idx].append(match)

	return buckets


def run_simulation(
	periods: Sequence[RatingPeriod],
	matches_by_period: Sequence[Sequence[MatchResult]],
	wrestlers: Iterable[str],
	tau: float,
	season_rd_floor: float | None = SEASON_RD_FLOOR,
) -> RatingRunResult:
	engine = Glicko2(tau=tau, season_rd_floor=season_rd_floor or SEASON_RD_FLOOR)
	for wrestler_id in wrestlers:
		engine.ensure_player(wrestler_id)

	head_to_head: defaultdict[tuple[str, str], int] = defaultdict(int)
	weight_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
	predictions: list[tuple[float, float]] = []

	prev_end: datetime | None = None
	prev_season: str | None = None
	for period, period_matches in zip(periods, matches_by_period):
		if prev_end is not None:
			engine.inflate_for_gap(months_between(prev_end, period.start))
		if season_rd_floor is not None and period.season != prev_season:
			engine.reset_rd_for_season()
			prev_season = period.season
		predictions.extend(engine.process_period(period_matches, head_to_head, weight_counts))
		prev_end = period.end

	return RatingRunResult(
		ratings=engine.states,
		head_to_head=dict(head_to_head),
		weight_counts=dict(weight_counts),
		predictions=predictions,
	)


def evaluate_predictions(predictions: Sequence[tuple[float, float]]) -> tuple[float, float]:
	if not predictions:
		return 0.0, 0.0
	brier = sum((p - actual) ** 2 for p, actual in predictions) / len(predictions)
	accuracy = sum((p >= 0.5 and actual == 1.0) or (p < 0.5 and actual == 0.0) for p, actual in predictions) / len(predictions)
	return brier, accuracy


def tune_tau(
	periods: Sequence[RatingPeriod],
	matches_by_period: Sequence[Sequence[MatchResult]],
	wrestlers: Iterable[str],
	candidates: Sequence[float],
) -> tuple[float, tuple[float, float]]:
	best_tau = candidates[0]
	best_metric = (float("inf"), 0.0)  # (brier, accuracy)

	for tau in candidates:
		result = run_simulation(periods, matches_by_period, wrestlers, tau)
		metrics = evaluate_predictions(result.predictions)
		if metrics[0] < best_metric[0]:
			best_tau = tau
			best_metric = metrics

	return best_tau, best_metric


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Run Glicko-2 ratings and build leaderboards.")
	parser.add_argument(
		"--season",
		action="append",
		help="Season name to include (e.g. 2022-2023). Repeat for multiple.",
	)
	parser.add_argument(
		"--start-date",
		help="Override start date (YYYY-MM-DD). Defaults to season start.",
	)
	parser.add_argument(
		"--end-date",
		help="Override end date (YYYY-MM-DD). Defaults to season cutoff or today.",
	)
	parser.add_argument(
		"--weights",
		nargs="+",
		help="Weight classes to include. Use 'all' for every class seen in the data.",
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=None,
		help="How many wrestlers to show per weight class. Default is all.",
	)
	parser.add_argument(
		"--min-wins",
		type=int,
		default=1,
		help="Minimum wins when selecting active wrestlers.",
	)
	parser.add_argument(
		"--tau",
		type=float,
		help="Explicit tau value. If omitted, the best candidate is back-tested.",
	)
	parser.add_argument(
		"--tau-candidates",
		help="Comma-separated tau candidates to back-test.",
	)
	parser.add_argument(
		"--grad-year",
		type=int,
		help="Only include wrestlers with this graduation year (still filtered to non-graduated).",
	)
	parser.add_argument(
		"--json-out",
		type=Path,
		help="Optional path to write leaderboard JSON payload.",
	)
	parser.add_argument(
		"--overrides",
		type=Path,
		help="Path to JSON mapping wrestler_id to settings (weight, gradYear, exclude).",
	)
	return parser.parse_args()


def parse_user_date(value: str | None) -> datetime | None:
	if value is None:
		return None
	return utils.parse_date(value).astimezone(timezone.utc)


def load_overrides(path: Path | None) -> dict[str, Any]:
	"""Load overrides supporting weight, exclusion, gradYear, and team forcing."""
	if path is None:
		return {"weights": {}, "exclude": set(), "grad_years": {}, "teams": {}}
	if not path.exists():
		print(f"Overrides file not found: {path}")
		return {"weights": {}, "exclude": set(), "grad_years": {}, "teams": {}}
	with path.open("r", encoding="utf-8") as fh:
		data = json.load(fh)
	if not isinstance(data, dict):
		print(f"Overrides file {path} must be a JSON object keyed by wrestler_id.")
		return {"weights": {}, "exclude": set(), "grad_years": {}, "teams": {}}

	weights: dict[str, str] = {}
	exclude: set[str] = set()
	grad_years: dict[str, int] = {}
	teams: dict[str, str] = {}

	for wrestler_id, value in data.items():
		if not isinstance(wrestler_id, str):
			continue
		if isinstance(value, str):
			weights[wrestler_id] = value
			continue
		if isinstance(value, dict):
			weight = value.get("weight")
			if isinstance(weight, str):
				weights[wrestler_id] = weight
			if value.get("exclude"):
				exclude.add(wrestler_id)
			grad = value.get("gradYear")
			if isinstance(grad, int):
				grad_years[wrestler_id] = grad
			team_id = value.get("teamId")
			if isinstance(team_id, str):
				teams[wrestler_id] = team_id
	return {"weights": weights, "exclude": exclude, "grad_years": grad_years, "teams": teams}


def build_matches(
	start: datetime,
	end: datetime,
	wrestlers: Iterable[str],
	weight_classes: set[str] | None,
) -> list[MatchResult]:
	raw_matches = utils.get_matches_between(start, end, wrestlers, weight_classes)
	results: list[MatchResult] = []

	for match in raw_matches:
		results.append(
			MatchResult(
				id=match["id"],
				date=match["date"],
				top_id=match["topId"],
				bottom_id=match["bottomId"],
				winner_id=match["winnerId"],
				win_type=match.get("winType"),
				weight_class=match.get("weightClass"),
			)
		)

	return results


def tally_records(matches: Sequence[MatchResult]) -> tuple[Counter[str], Counter[str]]:
	wins: Counter[str] = Counter()
	losses: Counter[str] = Counter()
	for match in matches:
		winner = match.winner_id
		if winner not in (match.top_id, match.bottom_id):
			continue
		loser = match.bottom_id if winner == match.top_id else match.top_id
		if loser is None:
			continue
		wins[winner] += 1
		losses[loser] += 1
	return wins, losses


def primary_weight_class(
	weight_counts: Mapping[str, Counter[str]],
	wrestler_id: str,
	overrides: Mapping[str, str] | None = None,
) -> str | None:
	if overrides and wrestler_id in overrides:
		return overrides[wrestler_id]
	counter = weight_counts.get(wrestler_id)
	if not counter:
		return None
	[(weight, _)] = counter.most_common(1)
	return weight


def build_leaderboard(
	result: RatingRunResult,
	weight_classes: Sequence[str],
	limit: int | None,
	names: Mapping[str, str],
	allowed_ids: set[str],
	weight_overrides: Mapping[str, str] | None = None,
	teams: Mapping[str, str | None] | None = None,
	grad_years: Mapping[str, int | None] | None = None,
	wins: Mapping[str, int] | None = None,
	losses: Mapping[str, int] | None = None,
) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]]]:
	weight_rankings: dict[str, list[str]] = {}
	wrestlers: dict[str, dict[str, Any]] = {}
	team_mapping = teams or {}
	wins = wins or {}
	losses = losses or {}

	def cmp(a: str, b: str) -> int:
		ra = result.ratings[a].rating
		rb = result.ratings[b].rating
		if abs(ra - rb) > 1e-6:
			return -1 if ra > rb else 1
		h2h = result.head_to_head.get((a, b), 0) - result.head_to_head.get((b, a), 0)
		if h2h != 0:
			return -1 if h2h > 0 else 1
		return 0

	for weight in weight_classes:
		candidates = [
			wrestler_id
			for wrestler_id in result.ratings.keys()
			if wrestler_id in allowed_ids
			if primary_weight_class(result.weight_counts, wrestler_id, weight_overrides) == weight
		]
		candidates.sort(key=cmp_to_key(cmp))

		ranking: list[str] = []
		for wrestler_id in candidates if limit is None else candidates[:limit]:
			if wrestler_id not in wrestlers:
				state = result.ratings[wrestler_id]
				wrestlers[wrestler_id] = {
					"id": wrestler_id,
					"name": names.get(wrestler_id, wrestler_id),
					"teamId": team_mapping.get(wrestler_id),
					"gradYear": (grad_years or {}).get(wrestler_id),
					"rating": round(state.rating, 2),
					"rd": round(state.rd, 2),
					"sigma": round(state.sigma, 4),
					"wins": int(wins.get(wrestler_id, 0)),
					"losses": int(losses.get(wrestler_id, 0)),
				}
			ranking.append(wrestler_id)
		weight_rankings[weight] = ranking

	return weight_rankings, wrestlers


def build_team_rosters(
	weight_rankings: Mapping[str, Sequence[str]],
	weight_classes: Sequence[str],
	wrestlers: Mapping[str, Mapping[str, Any]],
	team_metadata: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
	teams: dict[str, dict[str, Any]] = {}
	for weight in weight_classes:
		ranking = weight_rankings.get(weight, [])
		for wrestler_id in ranking:
			wrestler = wrestlers.get(wrestler_id)
			if not wrestler:
				continue
			team_id = wrestler.get("teamId")
			if not team_id:
				continue
			meta = team_metadata.get(team_id, {})
			team_info = teams.setdefault(
				team_id,
				{
					"id": team_id,
					"name": meta.get("name"),
					"division": meta.get("division"),
					"section": meta.get("section"),
					"weights": defaultdict(list),
				},
			)
			if not team_info.get("name") and meta.get("name"):
				team_info["name"] = meta.get("name")
			if team_info.get("division") is None and meta.get("division") is not None:
				team_info["division"] = meta.get("division")
			if not team_info.get("section") and meta.get("section"):
				team_info["section"] = meta.get("section")
			team_info["weights"][weight].append(wrestler_id)

	ordered: list[dict[str, Any]] = []
	for team in sorted(teams.values(), key=lambda t: ((t.get("name") or "").lower(), t["id"])):
		weights = team["weights"]
		ordered_weights = {
			weight: weights[weight]
			for weight in weight_classes
			if weight in weights
		}
		ordered.append(
			{
				"id": team["id"],
				"name": team.get("name"),
				"division": team.get("division"),
				"section": team.get("section"),
				"weights": ordered_weights,
			}
		)
	return ordered


def main() -> None:
	args = parse_args()

	seasons = utils.load_seasons()
	if not seasons:
		print("No seasons.json data found.")
		return

	season_filter = set(args.season) if args.season else None
	start_override = parse_user_date(args.start_date)
	end_override = parse_user_date(args.end_date)
	if end_override:
		end_override += timedelta(days=1)  # make end exclusive

	periods = build_periods(seasons, season_filter, start_override, end_override)
	if not periods:
		print("No rating periods to process with the provided filters.")
		return

	active_wrestlers = set(utils.get_active_wrestlers(min_wins=args.min_wins))
	if not active_wrestlers:
		print("No active wrestlers found. Try lowering min_wins.")
		return

	overrides = load_overrides(args.overrides)
	weight_overrides: dict[str, str] = overrides.get("weights", {})
	excluded_ids: set[str] = overrides.get("exclude", set())
	grad_overrides: dict[str, int] = overrides.get("grad_years", {})
	team_overrides: dict[str, str] = overrides.get("teams", {})
	team_override_meta = utils.get_team_metadata(team_overrides.values())
	manual_override_ids = set(weight_overrides.keys()) | set(grad_overrides.keys()) | set(team_overrides.keys())
	active_wrestlers.update(manual_override_ids - excluded_ids)

	weight_filter: set[str] | None = None
	if args.weights:
		if len(args.weights) == 1 and args.weights[0].lower() == "all":
			target_weight_classes = DEFAULT_WEIGHT_CLASSES
			weight_filter = None
		else:
			target_weight_classes = args.weights
			weight_filter = set(args.weights)
	else:
		target_weight_classes = DEFAULT_WEIGHT_CLASSES

	overall_start = periods[0].start
	overall_end = periods[-1].end

	all_matches = build_matches(overall_start, overall_end, active_wrestlers, weight_filter)
	if not all_matches:
		print("No matches found for the selected filters.")
		return
	win_counts, loss_counts = tally_records(all_matches)

	matches_by_period = bucket_matches(periods, all_matches)
	candidates = DEFAULT_TAU_CANDIDATES
	if args.tau_candidates:
		parsed = [float(x) for x in args.tau_candidates.split(",") if x.strip()]
		if parsed:
			candidates = parsed

	chosen_tau = args.tau
	metrics = (0.0, 0.0)
	if chosen_tau is None:
		chosen_tau, metrics = tune_tau(periods, matches_by_period, active_wrestlers, candidates)
		print(f"Tuned tau to {chosen_tau:.3f} (Brier={metrics[0]:.4f}, accuracy={metrics[1]:.2%})")
	else:
		print(f"Using provided tau={chosen_tau:.3f}")

	final_result = run_simulation(periods, matches_by_period, active_wrestlers, chosen_tau)

	info = utils.get_wrestler_info(final_result.ratings.keys())
	grad_years: dict[str, int | None] = {wrestler_id: meta.get("gradYear") for wrestler_id, meta in info.items()}
	for wrestler_id, override_year in grad_overrides.items():
		grad_years[wrestler_id] = override_year
	current_school_year = utils.get_school_year(datetime.now(timezone.utc))
	allowed_ids = set()
	for wrestler_id in info.keys():
		grad_year = grad_years.get(wrestler_id)
		if wrestler_id in excluded_ids:
			continue
		if args.grad_year is not None:
			if grad_year is not None and grad_year == args.grad_year and grad_year > current_school_year:
				allowed_ids.add(wrestler_id)
		else:
			if grad_year is None or grad_year > current_school_year:
				allowed_ids.add(wrestler_id)
	if args.grad_year is None:
		for wrestler_id in final_result.ratings.keys():
			if wrestler_id in excluded_ids:
				continue
			if wrestler_id not in info:
				grad_year = grad_years.get(wrestler_id)
				if grad_year is not None and grad_year <= current_school_year:
					continue
				allowed_ids.add(wrestler_id)

	if not allowed_ids:
		print("All wrestlers filtered out by graduation year; no leaderboard to display.")
		return

	names = {wrestler_id: meta.get("name", wrestler_id) for wrestler_id, meta in info.items()}
	teams = {wrestler_id: meta.get("teamId") for wrestler_id, meta in info.items()}
	for wrestler_id, team_id in team_overrides.items():
		teams[wrestler_id] = team_id
	team_names = {wrestler_id: meta.get("teamName") for wrestler_id, meta in info.items()}
	sections = {wrestler_id: meta.get("section") for wrestler_id, meta in info.items()}
	divisions = {wrestler_id: meta.get("division") for wrestler_id, meta in info.items()}
	# Apply team override metadata
	for wrestler_id, team_id in team_overrides.items():
		team_meta = team_override_meta.get(team_id, {})
		team_names[wrestler_id] = team_meta.get("name", teams.get(wrestler_id))
		sections[wrestler_id] = team_meta.get("section", sections.get(wrestler_id))
		divisions[wrestler_id] = team_meta.get("division", divisions.get(wrestler_id))
	team_metadata: dict[str, dict[str, Any]] = {
		team_id: {
			"name": meta.get("name"),
			"section": meta.get("section"),
			"division": meta.get("division"),
		}
		for team_id, meta in team_override_meta.items()
	}
	for wrestler_id in allowed_ids:
		team_id = teams.get(wrestler_id)
		if not team_id:
			continue
		team_info = team_metadata.setdefault(team_id, {"name": None, "section": None, "division": None})
		if not team_info.get("name") and team_names.get(wrestler_id):
			team_info["name"] = team_names[wrestler_id]
		if not team_info.get("section") and sections.get(wrestler_id):
			team_info["section"] = sections[wrestler_id]
		if team_info.get("division") is None and divisions.get(wrestler_id) is not None:
			team_info["division"] = divisions[wrestler_id]

	section_division_data = {
		"sections": sorted({value for value in sections.values() if value}),
		"divisions": sorted({value for value in divisions.values() if value is not None}),
	}
	weight_rankings, wrestler_map = build_leaderboard(
		final_result,
		target_weight_classes,
		args.limit,
		names,
		allowed_ids,
		weight_overrides,
		teams,
		grad_years,
		win_counts,
		loss_counts,
	)
	wrestlers_payload = sorted(
		wrestler_map.values(),
		key=lambda w: (-w["rating"], w["name"], w["id"]),
	)
	teams_payload = build_team_rosters(weight_rankings, target_weight_classes, wrestler_map, team_metadata)

	if args.json_out:
		payload = {
			"tau": chosen_tau,
			"matches": len(all_matches),
			"periods": len(periods),
			"gradYear": args.grad_year,
			"overrides": {
				"weights": weight_overrides or None,
				"exclude": sorted(excluded_ids) or None,
				"gradYears": grad_overrides or None,
				"teams": team_overrides or None,
			},
			"sectionDivisionData": section_division_data,
			"teams": teams_payload,
			"weights": weight_rankings,
			"wrestlers": wrestlers_payload,
		}
		args.json_out.parent.mkdir(parents=True, exist_ok=True)
		args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
		print(f"Wrote leaderboard JSON to {args.json_out}")
		return

	print(f"Processed {len(all_matches)} matches across {len(periods)} monthly periods.")
	for weight in target_weight_classes:
		ranking = weight_rankings.get(weight, [])
		if not ranking:
			continue
		print(f"\nWeight {weight}")
		for idx, wrestler_id in enumerate(ranking, start=1):
			entry = wrestler_map.get(wrestler_id)
			if not entry:
				continue
			print(f"{idx:>2}. {entry['name']} ({entry['id']}) — R: {entry['rating']} RD: {entry['rd']} σ: {entry['sigma']}")


if __name__ == "__main__":
	main()
