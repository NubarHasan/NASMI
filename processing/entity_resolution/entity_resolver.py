from __future__ import annotations

from dataclasses import dataclass, field

from core.guards import require
from core.identifiers import generate_entity_id
from core.types import CandidateFactId, EntityId
from processing.extraction.candidate_fact import CandidateFact
from processing.entity_resolution.entity_match import (
    EntityMatch,
    EntityMatchBundle,
    MatchSignal,
    MatchStrategy,
)
from processing.entity_resolution.entity_resolution_result import EntityResolutionResult

_WEIGHT: dict[str, float] = {
    "ssn": 1.00,
    "tax_id": 1.00,
    "iban": 0.95,
    "birth_date": 0.80,
    "full_name": 0.70,
}

_DEFAULT_WEIGHT: float = 0.50
_FUZZY_THRESHOLD: float = 0.60
_MERGE_THRESHOLD: float = 0.65

_HARD_CONFLICT_STRATEGIES: frozenset[MatchStrategy] = frozenset(
    {
        MatchStrategy.IDENTIFIER,
        MatchStrategy.DATE,
    }
)


def _fuzzy_ratio(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i, ca in enumerate(a, 1):
        for j, cb in enumerate(b, 1):
            dp[i][j] = (
                dp[i - 1][j - 1] + 1 if ca == cb else max(dp[i - 1][j], dp[i][j - 1])
            )
    lcs = dp[len(a)][len(b)]
    return (2 * lcs) / (len(a) + len(b))


def _strategy_for(fact_type: str) -> MatchStrategy:
    if fact_type in {"ssn", "tax_id", "iban", "passport_number", "national_id"}:
        return MatchStrategy.IDENTIFIER
    if fact_type in {"birth_date", "issue_date", "expiry_date"}:
        return MatchStrategy.DATE
    return MatchStrategy.FUZZY


def _weight_for(fact_type: str) -> float:
    return _WEIGHT.get(fact_type, _DEFAULT_WEIGHT)


def _confidence_for(
    val_a: str,
    val_b: str,
    strategy: MatchStrategy,
) -> float:
    if strategy in _HARD_CONFLICT_STRATEGIES:
        return 1.0 if val_a == val_b else 0.0
    ratio = _fuzzy_ratio(val_a, val_b)
    return ratio if ratio >= _FUZZY_THRESHOLD else ratio * 0.5


def _signal_for(
    val_a: str,
    val_b: str,
    strategy: MatchStrategy,
    confidence: float,
) -> MatchSignal:
    if strategy in _HARD_CONFLICT_STRATEGIES:
        return MatchSignal.STRONG if val_a == val_b else MatchSignal.CONFLICT
    return MatchSignal.from_confidence(confidence)


def _has_hard_conflict(matches: list[EntityMatch]) -> bool:
    return any(
        m.signal is MatchSignal.CONFLICT and m.strategy in _HARD_CONFLICT_STRATEGIES
        for m in matches
    )


def _extract_conflict_fact_types(matches: list[EntityMatch]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m.signal is MatchSignal.CONFLICT and m.fact_type not in seen:
            seen.add(m.fact_type)
            result.append(m.fact_type)
    return tuple(result)


def _overall_score(matches: list[EntityMatch]) -> float:
    if not matches:
        return 0.0
    total_weight: float = sum((_weight_for(m.fact_type) for m in matches), 0.0)
    if total_weight == 0.0:
        return 0.0
    weighted_sum: float = sum(
        (m.confidence * _weight_for(m.fact_type) for m in matches), 0.0
    )
    return weighted_sum / total_weight


@dataclass
class _EntityCluster:
    entity_id: EntityId
    facts: list[CandidateFact] = field(default_factory=list)

    def facts_for(self, fact_type: str) -> list[CandidateFact]:
        return [f for f in self.facts if f.fact_type == fact_type]

    def best_fact_for(self, fact_type: str) -> CandidateFact | None:
        candidates = self.facts_for(fact_type)
        if not candidates:
            return None
        return max(candidates, key=lambda f: f.confidence)

    def all_fact_types(self) -> set[str]:
        return {f.fact_type for f in self.facts}

    def shared_fact_types(self, other: _EntityCluster) -> set[str]:
        return self.all_fact_types() & other.all_fact_types()

    def total_confidence(self) -> float:
        return sum((f.confidence for f in self.facts), 0.0)


def _build_match(
    cluster_a: _EntityCluster,
    cluster_b: _EntityCluster,
    fact_type: str,
) -> EntityMatch | None:
    fact_a = cluster_a.best_fact_for(fact_type)
    fact_b = cluster_b.best_fact_for(fact_type)
    if fact_a is None or fact_b is None:
        return None

    val_a = fact_a.normalized_value
    val_b = fact_b.normalized_value
    strategy = _strategy_for(fact_type)
    conf = _confidence_for(val_a, val_b, strategy)
    signal = _signal_for(val_a, val_b, strategy, conf)

    return EntityMatch.create(
        fact_type=fact_type,
        value_a=val_a,
        value_b=val_b,
        fact_id_a=fact_a.candidate_fact_id,
        fact_id_b=fact_b.candidate_fact_id,
        strategy=strategy,
        confidence=conf,
        signal=signal,
        span_ids_a=tuple(fact_a.span_ids),
        span_ids_b=tuple(fact_b.span_ids),
    )


def _build_matches(
    cluster_a: _EntityCluster,
    cluster_b: _EntityCluster,
) -> list[EntityMatch]:
    matches: list[EntityMatch] = []
    for fact_type in cluster_a.shared_fact_types(cluster_b):
        match = _build_match(cluster_a, cluster_b, fact_type)
        if match is not None:
            matches.append(match)
    return matches


def _select_canonical(clusters: list[_EntityCluster]) -> dict[str, str]:
    best: dict[str, tuple[str, float]] = {}
    for cluster in clusters:
        for fact_type in cluster.all_fact_types():
            fact = cluster.best_fact_for(fact_type)
            if fact is None:
                continue
            current_conf = best.get(fact_type, ("", -1.0))[1]
            if fact.confidence > current_conf:
                best[fact_type] = (fact.normalized_value, fact.confidence)
    return {ft: val for ft, (val, _) in best.items()}


def _collect_fact_ids(clusters: list[_EntityCluster]) -> tuple[CandidateFactId, ...]:
    seen: set[CandidateFactId] = set()
    result: list[CandidateFactId] = []
    for cluster in clusters:
        for fact in cluster.facts:
            if fact.candidate_fact_id not in seen:
                seen.add(fact.candidate_fact_id)
                result.append(fact.candidate_fact_id)
    return tuple(result)


class EntityResolver:

    def resolve(
        self,
        facts: list[CandidateFact],
        entity_id: EntityId | None = None,
    ) -> EntityResolutionResult:
        require(len(facts) > 0, "facts must not be empty")

        clusters = self._group_into_clusters(facts)

        if len(clusters) == 1:
            return self._resolve_single_cluster(clusters[0], entity_id)

        return self._resolve_multi_cluster(clusters, entity_id)

    def _group_into_clusters(
        self,
        facts: list[CandidateFact],
    ) -> list[_EntityCluster]:
        index: dict[EntityId, _EntityCluster] = {}
        for fact in facts:
            if fact.entity_id not in index:
                index[fact.entity_id] = _EntityCluster(entity_id=fact.entity_id)
            index[fact.entity_id].facts.append(fact)
        return list(index.values())

    def _resolve_single_cluster(
        self,
        cluster: _EntityCluster,
        entity_id: EntityId | None,
    ) -> EntityResolutionResult:
        resolved_id = entity_id or cluster.entity_id
        canonical = _select_canonical([cluster])
        fact_ids = _collect_fact_ids([cluster])

        bundle = EntityMatchBundle(
            matches=(),
            overall_score=1.0,
        )

        return EntityResolutionResult.create(
            resolved_entity_id=resolved_id,
            candidate_fact_ids=fact_ids,
            bundle=bundle,
            canonical_values=canonical,
            conflict_fact_types=(),
            resolution_confidence=1.0,
        )

    def _resolve_multi_cluster(
        self,
        clusters: list[_EntityCluster],
        entity_id: EntityId | None,
    ) -> EntityResolutionResult:
        all_matches: list[EntityMatch] = []

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                all_matches.extend(_build_matches(clusters[i], clusters[j]))

        if _has_hard_conflict(all_matches):
            primary = max(clusters, key=lambda c: c.total_confidence())
            conflict_types = _extract_conflict_fact_types(all_matches)
            return self._resolve_with_conflict(
                primary, all_matches, conflict_types, entity_id
            )

        overall = _overall_score(all_matches)

        if overall < _MERGE_THRESHOLD:
            primary = max(clusters, key=lambda c: c.total_confidence())
            return self._resolve_single_cluster(primary, entity_id)

        resolved_id = entity_id or generate_entity_id()
        canonical = _select_canonical(clusters)
        fact_ids = _collect_fact_ids(clusters)

        bundle = EntityMatchBundle(
            matches=tuple(all_matches),
            overall_score=overall,
        )

        return EntityResolutionResult.create(
            resolved_entity_id=resolved_id,
            candidate_fact_ids=fact_ids,
            bundle=bundle,
            canonical_values=canonical,
            conflict_fact_types=(),
            resolution_confidence=overall,
        )

    def _resolve_with_conflict(
        self,
        primary: _EntityCluster,
        all_matches: list[EntityMatch],
        conflict_types: tuple[str, ...],
        entity_id: EntityId | None,
    ) -> EntityResolutionResult:
        resolved_id = entity_id or primary.entity_id
        canonical = _select_canonical([primary])
        fact_ids = _collect_fact_ids([primary])
        overall = _overall_score(all_matches)

        bundle = EntityMatchBundle(
            matches=tuple(all_matches),
            overall_score=overall,
        )

        return EntityResolutionResult.create(
            resolved_entity_id=resolved_id,
            candidate_fact_ids=fact_ids,
            bundle=bundle,
            canonical_values=canonical,
            conflict_fact_types=conflict_types,
            resolution_confidence=overall,
        )

