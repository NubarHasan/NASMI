from __future__ import annotations

from ui.viewmodels.profile_models import (
    FactSource,
    FactStatus,
    ProfileFact,
    ProfileSnapshot,
)

_MOCK_PROFILE = ProfileSnapshot(
    entity_id="entity-001",
    entity_name="Nubar Hasan",
    confidence=0.91,
    facts=(
        ProfileFact(
            fact_id="fact-001",
            field="full_name",
            value="Nubar Hasan",
            status=FactStatus.CONFIRMED,
            sources=(
                FactSource("doc-001", "passport", "Name: Nubar Hasan", 0.97),
                FactSource(
                    "doc-002", "residence_permit", "Full Name: Nubar Hasan", 0.93
                ),
            ),
        ),
        ProfileFact(
            fact_id="fact-002",
            field="date_of_birth",
            value="1990-03-22",
            status=FactStatus.CONFIRMED,
            sources=(FactSource("doc-001", "passport", "DOB: 1990-03-22", 0.97),),
        ),
        ProfileFact(
            fact_id="fact-003",
            field="employer",
            value="TechCorp GmbH",
            status=FactStatus.UNVERIFIED,
            sources=(
                FactSource(
                    "doc-003", "employment_contract", "Employer: TechCorp GmbH", 0.88
                ),
            ),
        ),
        ProfileFact(
            fact_id="fact-004",
            field="residence_permit_expiry",
            value="2027-11-19",
            status=FactStatus.CONFLICTED,
            sources=(
                FactSource(
                    "doc-002", "residence_permit", "Valid Until: 2027-11-19", 0.93
                ),
                FactSource(
                    "doc-002", "immigration_registry", "Expiry Date: 2027-12-01", 0.85
                ),
            ),
        ),
        ProfileFact(
            fact_id="fact-005",
            field="monthly_income",
            value="4200 EUR",
            status=FactStatus.UNVERIFIED,
            sources=(
                FactSource("doc-005", "payslip", "Net Pay: 4200 EUR", None),
                FactSource("doc-004", "bank_statement", "Credit: 4200.00", 0.81),
            ),
        ),
    ),
)


def _count_conflicts(snapshot: ProfileSnapshot) -> int:
    return sum(1 for f in snapshot.facts if f.status is FactStatus.CONFLICTED)


class ProfileVM:
    def load_profile(self, entity_id: str) -> ProfileSnapshot | None:
        if entity_id == _MOCK_PROFILE.entity_id:
            return _MOCK_PROFILE
        return None

    def refresh_profile(self, entity_id: str) -> ProfileSnapshot | None:
        return self.load_profile(entity_id)

    def count_conflicts(self, snapshot: ProfileSnapshot) -> int:
        return _count_conflicts(snapshot)
