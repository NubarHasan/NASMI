from __future__ import annotations

import re
from datetime import UTC, date, datetime

from core.guards import require
from core.types import CandidateFactId, EntityId
from knowledge.conflict import Conflict
from knowledge.evidence import Evidence
from knowledge.fact import Fact
from knowledge.fact_evidence import FactEvidence, FactEvidenceRole
from knowledge.provenance import Provenance, ProvenanceActor, ProvenanceStep
from processing.entity_resolution.entity_resolution_result import EntityResolutionResult
from processing.extraction.candidate_fact import CandidateFact
from processing.knowledge_build.knowledge_build_result import KnowledgeBuildResult

_EVIDENCE_ONLY_TYPES: frozenset[str] = frozenset(
    {
        "document_label",
        "document_date",
        "letter_date",
        "date",
        "date_value",
        "legal_reference_date",
        "legal_reference",
        "organization_name",
        "authority_name",
        "office_name",
        "contact_email",
        "contact_phone",
        "contact_person",
        "organization_iban",
        "organization_address",
        "organization_reference",
        "bank_name",
        "bic",
        "employer",
        "employee",
        "tax_office",
        "insurance_provider",
        "case_worker",
        "document_reference",
        "page_number",
        "footer",
        "header",
        "form_label",
        "form_instruction",
        "form_section",
        "form_checkbox",
        "form_option",
        "form_help_text",
        "form_footer",
        "form_header",
        "instruction_text",
        "public_authority_reference",
        "authority_reference",
        "tax_reference",
        "tax_office_reference",
        "health_reference",
        "health_provider",
        "insurance_reference",
        "business_reference",
        "employment_reference",
        "bank_reference",
        "payment_reference",
        "invoice_reference",
        "legal_reference_number",
        "case_reference",
        "department_name",
        "service_center",
        "customer_center",
        "branch_name",
        "recipient_name",
        "sender_name",
        "company_name",
        "unknown_non_person",
        "fax",
        "tel",
        "telephone",
        "phone",
        "hotline",
        "service_phone",
        "authority_phone",
        "organization_phone",
        "public_phone",
        "support_phone",
        "customer_service_phone",
        "form_value",
        "form_noise",
        "ocr_fragment",
        "reference_noise",
    }
)

_REVIEW_ONLY_TYPES: frozenset[str] = frozenset(
    {
        "review_candidate",
    }
)

_DATE_TYPES: frozenset[str] = frozenset(
    {
        "date",
        "date_value",
        "birth_date",
        "date_of_birth",
        "issue_date",
        "issued_date",
        "date_of_issue",
        "expiry_date",
        "expiration_date",
        "valid_until",
        "due_date",
        "payment_due_date",
        "enrollment_date",
        "document_date",
        "letter_date",
        "legal_reference_date",
        "appointment_date",
        "coverage_start_date",
        "coverage_end_date",
        "employment_start_date",
        "employment_end_date",
        "contract_start_date",
        "contract_end_date",
        "tax_year_date",
        "invoice_date",
        "service_period_start",
        "service_period_end",
        "decision_date",
        "approval_date",
        "application_date",
        "submission_date",
        "processing_date",
        "period_start_date",
        "period_end_date",
        "valid_from",
        "valid_to",
    }
)

_DATE_OF_BIRTH_HINTS: tuple[str, ...] = (
    "date of birth",
    "birth date",
    "geburtsdatum",
    "geboren",
    "geboren am",
    "born",
    "born on",
    "dob",
    "date naissance",
    "date de naissance",
    "تاريخ الميلاد",
)

_ISSUE_DATE_HINTS: tuple[str, ...] = (
    "issue date",
    "date of issue",
    "issued",
    "issued on",
    "ausstellungsdatum",
    "ausgestellt",
    "ausgestellt am",
    "date delivrance",
    "date de délivrance",
    "تاريخ الإصدار",
)

_EXPIRY_DATE_HINTS: tuple[str, ...] = (
    "expiry date",
    "expiration date",
    "expires",
    "expires on",
    "valid until",
    "gültig bis",
    "gueltig bis",
    "ablaufdatum",
    "ablauf am",
    "date expiration",
    "date d'expiration",
    "تاريخ الانتهاء",
)

_ENROLLMENT_DATE_HINTS: tuple[str, ...] = (
    "enrollment date",
    "registration date",
    "start date",
    "course start",
    "beginn",
    "anmeldung",
    "einschreibung",
    "immatrikulation",
    "تاريخ التسجيل",
)

_PAYMENT_DUE_DATE_HINTS: tuple[str, ...] = (
    "payment due",
    "payment due date",
    "due date",
    "due by",
    "pay until",
    "pay by",
    "payable until",
    "payment deadline",
    "deadline for payment",
    "zahlung bis",
    "zahlbar bis",
    "zahlbar am",
    "fällig am",
    "fällig bis",
    "faellig am",
    "faellig bis",
    "bis spätestens",
    "bis spaetestens",
    "rechnung fällig",
    "rechnung faellig",
    "invoice due",
    "mahnung",
    "zahlungserinnerung",
    "mahnbetrag",
    "überweisen bis",
    "ueberweisen bis",
    "آخر موعد للدفع",
    "تاريخ الاستحقاق",
    "ادفع حتى",
    "الدفع حتى",
)

_DOCUMENT_DATE_HINTS: tuple[str, ...] = (
    "document date",
    "letter date",
    "letter dated",
    "date of letter",
    "schreiben vom",
    "brief vom",
    "bescheid vom",
    "datum",
    "erstellt am",
    "created on",
    "ausfertigung",
    "bearbeitet am",
    "eingegangen am",
    "posteingang",
    "eingangsdatum",
    "druckdatum",
    "تاريخ الوثيقة",
    "تاريخ الخطاب",
)

_LEGAL_REFERENCE_DATE_HINTS: tuple[str, ...] = (
    "gesetz",
    "gesetzes",
    "gesetz vom",
    "verordnung",
    "verordnung vom",
    "rechtsgrundlage",
    "rechtsgrundlagen",
    "paragraph",
    "artikel",
    "abs.",
    "absatz",
    "sgb",
    "s gb",
    "bgb",
    "aufenthg",
    "asylg",
    "estg",
    "ao",
    "ustg",
    "§",
    "in kraft",
    "inkrafttreten",
    "law dated",
    "regulation dated",
    "legal basis",
    "legal reference",
    "قانون",
    "لائحة",
    "الأساس القانوني",
)

_APPOINTMENT_DATE_HINTS: tuple[str, ...] = (
    "appointment",
    "termin",
    "vorsprache",
    "einladung",
    "meeting",
    "interview",
    "anhörung",
    "anhoerung",
    "ladung",
    "vorsprechen am",
    "erscheinen am",
    "موعد",
    "مقابلة",
)

_COVERAGE_START_HINTS: tuple[str, ...] = (
    "versichert ab",
    "gültig ab",
    "gueltig ab",
    "valid from",
    "coverage from",
    "insurance from",
    "beginn der versicherung",
    "mitglied ab",
    "بداية التأمين",
)

_COVERAGE_END_HINTS: tuple[str, ...] = (
    "versichert bis",
    "gültig bis",
    "gueltig bis",
    "valid until",
    "coverage until",
    "insurance until",
    "ende der versicherung",
    "mitglied bis",
    "نهاية التأمين",
)

_EMPLOYMENT_START_HINTS: tuple[str, ...] = (
    "employment start",
    "begin of employment",
    "beschäftigt seit",
    "beschaeftigt seit",
    "eintritt",
    "arbeitsbeginn",
    "tätig seit",
    "taetig seit",
    "beginn der beschäftigung",
    "beginn der beschaeftigung",
    "بداية العمل",
)

_EMPLOYMENT_END_HINTS: tuple[str, ...] = (
    "employment end",
    "end of employment",
    "austritt",
    "arbeitsende",
    "beschäftigt bis",
    "beschaeftigt bis",
    "ende der beschäftigung",
    "ende der beschaeftigung",
    "نهاية العمل",
)

_CONTRACT_START_HINTS: tuple[str, ...] = (
    "contract start",
    "vertragsbeginn",
    "mietbeginn",
    "lease start",
    "starts on",
    "beginnt am",
    "beginn des vertrags",
    "بداية العقد",
)

_CONTRACT_END_HINTS: tuple[str, ...] = (
    "contract end",
    "vertragsende",
    "mietende",
    "lease end",
    "ends on",
    "endet am",
    "ende des vertrags",
    "نهاية العقد",
)

_INVOICE_DATE_HINTS: tuple[str, ...] = (
    "invoice date",
    "rechnungsdatum",
    "rechnung vom",
    "datum der rechnung",
    "belegdatum",
    "تاريخ الفاتورة",
)

_DECISION_DATE_HINTS: tuple[str, ...] = (
    "decision date",
    "bescheid vom",
    "entscheidung vom",
    "beschluss vom",
    "bewilligung vom",
    "ablehnung vom",
    "تاريخ القرار",
)

_TAX_CONTEXT_HINTS: tuple[str, ...] = (
    "steuerbescheid",
    "finanzamt",
    "steuer",
    "tax assessment",
    "tax office",
    "einkommensteuer",
    "lohnsteuer",
    "steuerjahr",
    "steuernummer",
    "steuer-id",
    "steueridentifikationsnummer",
    "identifikationsnummer",
    "ust-id",
    "umsatzsteuer",
    "lohnsteuerbescheinigung",
    "elster",
    "abgabenordnung",
    "freibetrag",
    "solidaritätszuschlag",
    "solidaritaetszuschlag",
    "kirchensteuer",
    "ضريبة",
)

_HEALTH_CONTEXT_HINTS: tuple[str, ...] = (
    "aok",
    "aok plus",
    "tk",
    "techniker krankenkasse",
    "barmer",
    "dak",
    "ikk",
    "kkh",
    "hkk",
    "krankenkasse",
    "pflegekasse",
    "gesundheitskasse",
    "versicherung",
    "krankenversicherung",
    "pflegeversicherung",
    "versichert",
    "versichertennummer",
    "mitgliedsnummer",
    "egk",
    "gesundheitskarte",
    "elektronische gesundheitskarte",
    "health insurance",
    "insurance provider",
    "coverage",
    "patient",
    "beitrag",
    "beitragssatz",
    "sozialversicherung",
)

_BUSINESS_CONTEXT_HINTS: tuple[str, ...] = (
    "arbeitgeber",
    "arbeitnehmer",
    "employee",
    "employer",
    "employment",
    "beschäftigung",
    "beschaeftigung",
    "beschäftigungsbetrieb",
    "beschaftigungsbetrieb",
    "beschäftigungsort",
    "beschaftigungsort",
    "firma",
    "company",
    "unternehmen",
    "betrieb",
    "lohn",
    "gehalt",
    "payroll",
    "salary",
    "wage",
    "contribution",
    "employee contribution",
    "employer contribution",
    "personalabteilung",
    "hr",
    "abteilung",
    "beruf",
    "tätigkeit",
    "taetigkeit",
)

_BANK_CONTEXT_HINTS: tuple[str, ...] = (
    "iban",
    "bic",
    "bank",
    "sparkasse",
    "volksbank",
    "deutsche bank",
    "commerzbank",
    "postbank",
    "bankverbindung",
    "zahlungsempfänger",
    "zahlungsempfaenger",
    "kontoinhaber",
    "konto",
    "kontonummer",
    "gläubiger",
    "glaeubiger",
    "mandatsreferenz",
    "sepa",
    "lastschrift",
    "überweisung",
    "ueberweisung",
    "zahlungsverkehr",
    "recipient bank",
    "creditor",
)

_AUTHORITY_CONTEXT_HINTS: tuple[str, ...] = (
    "jobcenter",
    "landratsamt",
    "wartburgkreis",
    "ausländerbehörde",
    "auslaenderbehoerde",
    "stadtverwaltung",
    "gemeinde",
    "amt",
    "behörde",
    "behoerde",
    "finanzamt",
    "bundesagentur",
    "agentur für arbeit",
    "agentur fuer arbeit",
    "sozialamt",
    "rathaus",
    "bürgeramt",
    "buergeramt",
    "einwohnermeldeamt",
    "familienkasse",
    "jugendamt",
    "wohngeldstelle",
    "ordnungsamt",
    "department",
    "authority",
    "public office",
)

_FORM_CONTEXT_HINTS: tuple[str, ...] = (
    "formular",
    "vordruck",
    "seite",
    "page",
    "anlage",
    "abschnitt",
    "bitte",
    "ankreuzen",
    "zutreffendes",
    "ausfüllen",
    "ausfuellen",
    "eintragen",
    "unterschrift",
    "signature",
    "zurück",
    "zurdck",
    "zurueck",
    "weiter",
    "hinweis",
    "hinweise",
    "erklärung",
    "erklaerung",
    "datenschutzhinweis",
    "pflichtfeld",
    "optional",
)

_ADDRESS_JUNK_HINTS: tuple[str, ...] = (
    "zurück",
    "zurdck",
    "zurueck",
    "beschäftigungsbetrieb",
    "beschaftigungsbetrieb",
    "beschäftigungsort",
    "beschaftigungsort",
    "ändert",
    "andert",
    "formular",
    "vordruck",
    "seite",
    "page",
    "anlage",
    "bitte",
    "ankreuzen",
    "ausfüllen",
    "ausfuellen",
    "unterschrift",
    "signature",
    "hinweis",
    "kundencenter",
    "servicecenter",
    "postfach",
    "telefon",
    "fax",
    "email",
    "e-mail",
    "www.",
    "http",
)

_NON_PERSON_CONTEXT_HINTS: tuple[str, ...] = (
    (
        "aok",
        "aok plus",
        "jobcenter",
        "landratsamt",
        "wartburgkreis",
        "ausländerbehörde",
        "auslaenderbehoerde",
        "stadtverwaltung",
        "gemeinde",
        "amt",
        "behörde",
        "behoerde",
        "finanzamt",
        "krankenkasse",
        "versicherung",
        "bundesagentur",
        "agentur für arbeit",
        "agentur fuer arbeit",
        "sozialamt",
        "rathaus",
        "telefon",
        "fax",
        "e-mail",
        "email",
        "www.",
        "http",
        "straße",
        "strasse",
        "postfach",
        "bankverbindung",
        "iban",
        "bic",
        "sparkasse",
        "volksbank",
        "deutsche bank",
        "commerzbank",
        "zahlungsverkehr",
        "servicecenter",
        "kundencenter",
    )
    + _TAX_CONTEXT_HINTS
    + _HEALTH_CONTEXT_HINTS
    + _BUSINESS_CONTEXT_HINTS
    + _BANK_CONTEXT_HINTS
    + _AUTHORITY_CONTEXT_HINTS
    + _FORM_CONTEXT_HINTS
)

_ORGANIZATION_VALUE_HINTS: tuple[str, ...] = (
    "aok",
    "plus",
    "gmbh",
    "ag",
    "kg",
    "ug",
    "ohg",
    "ev",
    "e.v.",
    "amt",
    "behörde",
    "behoerde",
    "jobcenter",
    "landratsamt",
    "kreis",
    "stadt",
    "gemeinde",
    "versicherung",
    "krankenkasse",
    "bank",
    "sparkasse",
    "finanzamt",
    "bundesagentur",
    "agentur",
    "sozialamt",
    "rathaus",
    "verwaltung",
    "center",
    "zentrum",
    "service",
    "kundencenter",
    "servicecenter",
    "abteilung",
    "department",
    "office",
    "authority",
)

_PERSON_NAME_FIELDS: frozenset[str] = frozenset(
    {
        "surname",
        "given_names",
        "full_name",
        "first_name",
        "last_name",
    }
)

_WEAK_PERSON_FIELDS: frozenset[str] = frozenset(
    {
        "employer",
        "employee",
        "occupation",
        "job_title",
    }
)

_ADDRESS_FIELDS: frozenset[str] = frozenset(
    {
        "address",
        "street",
        "postal_address",
        "residence",
        "residential_address",
        "home_address",
    }
)

_PHONE_FIELDS: frozenset[str] = frozenset(
    {
        "phone_number",
        "phone",
        "telephone",
        "mobile",
        "contact_phone",
        "fax",
        "tel",
        "telefon",
    }
)

_REFERENCE_FIELDS: frozenset[str] = frozenset(
    {
        "reference",
        "reference_number",
        "case_number",
        "number",
        "customer_number",
        "insurance_number",
        "member_number",
        "tax_number",
        "file_number",
        "document_number",
    }
)

_PROTECTED_PERSON_FIELDS: frozenset[str] = frozenset(
    {
        "surname",
        "given_names",
        "full_name",
        "first_name",
        "last_name",
        "date_of_birth",
        "place_of_birth",
        "nationality",
        "sex",
        "gender",
        "tax_id",
        "iban",
        "phone_number",
        "phone",
        "telephone",
        "mobile",
        "email",
        "address",
        "street",
        "postal_address",
        "residence",
        "residential_address",
        "home_address",
    }
)

_PHONE_CONTEXT_NOISE_HINTS: tuple[str, ...] = (
    "fax",
    "telefon",
    "tel.",
    "tel:",
    "phone",
    "hotline",
    "service",
    "kundencenter",
    "servicecenter",
    "zentrale",
    "durchwahl",
    "extension",
    "kontakt",
    "contact",
    "sprechzeiten",
    "öffnungszeiten",
    "oeffnungszeiten",
    "homepage",
    "webseite",
    "website",
    "www.",
    "http",
    "behörde",
    "behoerde",
    "amt",
    "jobcenter",
    "landratsamt",
    "finanzamt",
    "krankenkasse",
    "versicherung",
    "agentur für arbeit",
    "agentur fuer arbeit",
    "stadtverwaltung",
    "gemeinde",
    "rathaus",
    "postfach",
    "service-hotline",
    "kundenservice",
    "support",
    "zentrale rufnummer",
    "telefonnummer der dienststelle",
)

_PHONE_VALUE_NOISE_PREFIXES: tuple[str, ...] = (
    "004-",
    "004 ",
    "00 4",
    "000",
)

_FORM_VALUE_NOISE_HINTS: tuple[str, ...] = (
    "zurdck",
    "zurück",
    "zurueck",
    "weiter",
    "bitte",
    "seite",
    "page",
    "formular",
    "anlage",
    "abschnitt",
    "hinweis",
    "unterschrift",
    "signature",
    "ankreuzen",
    "ausfüllen",
    "ausfuellen",
    "eintragen",
)

_REFERENCE_NOISE_HINTS: tuple[str, ...] = (
    "kundencenter",
    "servicecenter",
    "jobcenter",
    "landratsamt",
    "finanzamt",
    "krankenkasse",
    "versicherung",
    "agentur",
    "bank",
    "sparkasse",
    "postfach",
    "telefon",
    "fax",
    "email",
    "www.",
    "http",
)
_NAME_CONTEXT_NOISE_HINTS: tuple[str, ...] = (
    "betreuenden fachkraft",
    "fachkraft",
    "maßnahmeteilnehmenden",
    "massnahmeteilnehmenden",
    "ma&nahmeteilnehmenden",
    "teilnehmenden",
    "teilnehmer",
    "ansprechpartner",
    "sachbearbeiter",
    "bearbeiter",
    "kontaktperson",
    "berater",
    "betreuer",
    "dozent",
    "lehrer",
    "mitarbeiter",
    "zuständig",
    "zustaendig",
    "zuständige",
    "zustaendige",
    "unterschrift",
    "signature",
)

_NAME_VALUE_NOISE_PREFIXES: tuple[str, ...] = (
    "herr ",
    "frau ",
    "mr ",
    "mrs ",
    "ms ",
    "dr ",
    "prof ",
)

_NAME_FIELDS: frozenset[str] = frozenset(
    {
        "surname",
        "given_names",
        "full_name",
        "first_name",
        "last_name",
    }
)


class KnowledgeBuilder:

    def build(
        self,
        entity_resolution_result: EntityResolutionResult,
        candidate_facts: tuple[CandidateFact, ...],
    ) -> KnowledgeBuildResult:
        require(
            isinstance(entity_resolution_result, EntityResolutionResult),
            "entity_resolution_result must be an EntityResolutionResult",
        )
        require(
            isinstance(candidate_facts, tuple) and len(candidate_facts) >= 1,
            "candidate_facts must be a non-empty tuple",
        )

        entity_id: EntityId = entity_resolution_result.resolved_entity_id

        fact_by_candidate: dict[CandidateFactId, Fact] = {}
        evidence_by_candidate: dict[CandidateFactId, Evidence] = {}

        for cf in candidate_facts:
            evidence_by_candidate[cf.candidate_fact_id] = _build_evidence(entity_id, cf)

            if _should_build_fact(cf):
                fact_by_candidate[cf.candidate_fact_id] = _build_fact(entity_id, cf)

        fact_evidence_links = _build_fact_evidence_links(
            fact_by_candidate,
            evidence_by_candidate,
            candidate_facts,
        )

        provenance_records = _build_provenance_records(
            entity_id,
            fact_by_candidate,
            evidence_by_candidate,
            candidate_facts,
        )

        conflicts = _build_conflicts(
            entity_id,
            entity_resolution_result,
            fact_by_candidate,
        )

        return KnowledgeBuildResult.create(
            entity_id=entity_id,
            facts=tuple(fact_by_candidate.values()),
            evidence=tuple(evidence_by_candidate.values()),
            fact_evidence_links=fact_evidence_links,
            provenance_records=provenance_records,
            conflicts=conflicts,
        )


def _should_build_fact(cf: CandidateFact) -> bool:
    resolved_field_name = _resolve_field_name(cf)

    if cf.fact_type in _EVIDENCE_ONLY_TYPES:
        return False

    if resolved_field_name in _EVIDENCE_ONLY_TYPES:
        return False

    if cf.fact_type in _REVIEW_ONLY_TYPES:
        return False

    if cf.metadata.get("role") == "document_label":
        return False

    if cf.metadata.get("is_person_fact") is False:
        return False

    if cf.metadata.get("store_as_knowledge_evidence") is True:
        return False

    if _looks_like_label_value(cf.normalized_value):
        return False

    if _is_junk_value(cf, resolved_field_name):
        return False

    if _is_non_person_contact(cf, resolved_field_name):
        return False

    if _is_likely_organization_name(cf, resolved_field_name):
        return False

    if _is_non_person_iban(cf, resolved_field_name):
        return False

    if _is_weak_person_field_noise(cf, resolved_field_name):
        return False

    if _is_address_noise(cf, resolved_field_name):
        return False

    if _is_phone_noise(cf, resolved_field_name):
        return False

    if _is_reference_noise(cf, resolved_field_name):
        return False

    if _is_form_value_noise(cf, resolved_field_name):
        return False

    if _is_name_noise(cf, resolved_field_name):
        return False

    return not _is_domain_specific_noise(cf, resolved_field_name)


def _build_fact(entity_id: EntityId, cf: CandidateFact) -> Fact:
    field_name = _resolve_field_name(cf)

    return Fact.create(
        entity_id=entity_id,
        field_name=field_name,
        canonical_value=cf.normalized_value,
        display_value=cf.normalized_value,
        source_stage=cf.source_stage,
        confidence=cf.confidence,
    )


def _build_evidence(entity_id: EntityId, cf: CandidateFact) -> Evidence:
    metadata = dict(cf.metadata)
    resolved_field_name = _resolve_field_name(cf)

    metadata["document_id"] = str(cf.document_id)
    metadata["candidate_fact_id"] = str(cf.candidate_fact_id)
    metadata["fact_type"] = cf.fact_type
    metadata["resolved_field_name"] = resolved_field_name

    return Evidence.create(
        source_id=cf.source_id,
        entity_id=entity_id,
        field_name=resolved_field_name,
        raw_value=cf.raw_value,
        extraction_method=cf.source_stage,
        confidence=cf.confidence,
        location={"span_ids": [str(s) for s in cf.span_ids]},
        metadata=metadata,
    )


def _resolve_field_name(cf: CandidateFact) -> str:
    target_field = cf.metadata.get("target_field")
    field_name = str(target_field) if target_field else str(cf.fact_type)
    field_name = field_name.strip().lower()
    context = _candidate_context_text(cf)

    if _is_date_candidate(cf, field_name):
        return _classify_date_field(cf, field_name)

    if field_name == "phone_number" and _looks_like_date(cf.normalized_value):
        return "date_of_birth"

    if field_name == "email" and _is_non_person_contact(cf, field_name):
        return "contact_email"

    if field_name in _PHONE_FIELDS and _is_non_person_contact(cf, field_name):
        return "contact_phone"

    if field_name in _PHONE_FIELDS and _is_phone_noise(cf, field_name):
        return "contact_phone"

    if field_name in _PERSON_NAME_FIELDS and _is_likely_organization_name(
        cf, field_name
    ):
        return "organization_name"

    if field_name == "iban" and _is_non_person_iban(cf, field_name):
        return "organization_iban"

    if field_name in _ADDRESS_FIELDS and _is_organization_context(cf):
        return "organization_address"

    if field_name in _REFERENCE_FIELDS and _is_organization_context(cf):
        return "organization_reference"

    if field_name in _REFERENCE_FIELDS and _is_reference_noise(cf, field_name):
        return "reference_noise"

    if (
        _contains_any(context, _HEALTH_CONTEXT_HINTS)
        and field_name not in _PROTECTED_PERSON_FIELDS
    ):
        return "health_reference"

    if (
        _contains_any(context, _TAX_CONTEXT_HINTS)
        and field_name not in _PROTECTED_PERSON_FIELDS
    ):
        return "tax_reference"

    if (
        _contains_any(context, _BUSINESS_CONTEXT_HINTS)
        and field_name not in _PROTECTED_PERSON_FIELDS
    ):
        return "business_reference"

    if _contains_any(context, _BANK_CONTEXT_HINTS) and field_name not in {
        "iban",
        "organization_iban",
    }:
        return "bank_reference"

    if (
        _contains_any(context, _AUTHORITY_CONTEXT_HINTS)
        and field_name not in _PROTECTED_PERSON_FIELDS
    ):
        return "public_authority_reference"

    if (
        _contains_any(context, _FORM_CONTEXT_HINTS)
        and field_name not in _PROTECTED_PERSON_FIELDS
    ):
        return "form_instruction"

    return field_name


def _is_date_candidate(cf: CandidateFact, field_name: str) -> bool:
    lowered_field = field_name.strip().lower()
    lowered_type = str(cf.fact_type).strip().lower()

    return (
        lowered_field in _DATE_TYPES
        or lowered_type in _DATE_TYPES
        or bool(_looks_like_date(cf.normalized_value))
    )


def _classify_date_field(cf: CandidateFact, fallback: str) -> str:
    context = _candidate_context_text(cf)
    fallback_value = fallback.strip().lower()
    target_field = str(cf.metadata.get("target_field") or "").strip().lower()

    if _contains_any(context, _LEGAL_REFERENCE_DATE_HINTS):
        return "legal_reference_date"

    if _contains_any(context, _PAYMENT_DUE_DATE_HINTS):
        return "payment_due_date"

    if _contains_any(context, _DATE_OF_BIRTH_HINTS):
        return "date_of_birth"

    if _contains_any(context, _ISSUE_DATE_HINTS):
        return "issue_date"

    if _contains_any(context, _EXPIRY_DATE_HINTS):
        return "expiry_date"

    if _contains_any(context, _ENROLLMENT_DATE_HINTS):
        return "enrollment_date"

    if _contains_any(context, _APPOINTMENT_DATE_HINTS):
        return "appointment_date"

    if _contains_any(context, _COVERAGE_START_HINTS):
        return "coverage_start_date"

    if _contains_any(context, _COVERAGE_END_HINTS):
        return "coverage_end_date"

    if _contains_any(context, _EMPLOYMENT_START_HINTS):
        return "employment_start_date"

    if _contains_any(context, _EMPLOYMENT_END_HINTS):
        return "employment_end_date"

    if _contains_any(context, _CONTRACT_START_HINTS):
        return "contract_start_date"

    if _contains_any(context, _CONTRACT_END_HINTS):
        return "contract_end_date"

    if _contains_any(context, _INVOICE_DATE_HINTS):
        return "invoice_date"

    if _contains_any(context, _DECISION_DATE_HINTS):
        return "decision_date"

    if _contains_any(context, _TAX_CONTEXT_HINTS):
        return "document_date"

    if _contains_any(context, _DOCUMENT_DATE_HINTS):
        return "document_date"

    if target_field in _DATE_TYPES:
        if target_field in {"date", "date_value"}:
            return "date"
        return target_field

    if fallback_value in {"birth_date", "date_of_birth"}:
        return "date_of_birth"

    if fallback_value in {"expiration_date", "expiry_date", "valid_until", "valid_to"}:
        return "expiry_date"

    if fallback_value in {"issue_date", "date_of_issue", "issued_date"}:
        return "issue_date"

    if fallback_value in {"payment_due_date", "due_date"}:
        return "payment_due_date"

    if fallback_value in {"enrollment_date", "registration_date", "start_date"}:
        return "enrollment_date"

    if fallback_value in {"document_date", "letter_date"}:
        return "document_date"

    if fallback_value == "legal_reference_date":
        return "legal_reference_date"

    parsed_date = _parse_date_value(cf.normalized_value)
    if parsed_date is None:
        parsed_date = _parse_date_value(cf.raw_value)

    if parsed_date is None:
        return "date"

    today = datetime.now(UTC).date()
    age_years = _year_distance(parsed_date, today)

    if parsed_date > today:
        if parsed_date.year >= today.year + 2:
            return "expiry_date"
        return "document_date"

    if 16 <= age_years <= 120:
        if _is_probably_birth_date_context(context):
            return "date_of_birth"
        return "date"

    if today.year - 5 <= parsed_date.year <= today.year:
        return "document_date"

    return "date"


def _parse_date_value(value: str) -> date | None:
    text = str(value).strip()
    patterns = (
        r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$",
        r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$",
    )

    match = re.match(patterns[0], text)
    if match:
        day, month, year = match.groups()
        return _safe_date(year, month, day)

    match = re.match(patterns[1], text)
    if match:
        year, month, day = match.groups()
        return _safe_date(year, month, day)

    digits = re.sub(r"\D", "", text)

    if len(digits) == 8:
        if 1900 <= int(digits[:4]) <= 2100:
            return _safe_date(digits[:4], digits[4:6], digits[6:8])
        return _safe_date(digits[4:8], digits[2:4], digits[0:2])

    if len(digits) == 6:
        year = digits[4:6]
        full_year = "19" + year if int(year) > 30 else "20" + year
        return _safe_date(full_year, digits[2:4], digits[0:2])

    return None


def _safe_date(year: str, month: str, day: str) -> date | None:
    try:
        year_value = int(year)
        if year_value < 100:
            year_value = 1900 + year_value if year_value > 30 else 2000 + year_value

        return date(
            year_value,
            int(month),
            int(day),
        )
    except ValueError:
        return None


def _year_distance(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return years


def _candidate_context_text(cf: CandidateFact) -> str:
    parts: list[str] = [
        str(cf.fact_type),
        str(cf.raw_value),
        str(cf.normalized_value),
        str(cf.source_stage),
    ]

    for key in (
        "target_field",
        "label",
        "nearby_label",
        "context",
        "line_text",
        "block_text",
        "page_text",
        "left_text",
        "right_text",
        "previous_text",
        "next_text",
        "source_label",
        "document_type",
        "sender",
        "recipient",
        "section",
        "table_header",
        "column_header",
        "row_header",
        "document_title",
        "document_category",
        "issuer",
        "authority",
        "organization",
        "page_header",
        "page_footer",
    ):
        value = cf.metadata.get(key)
        if value is not None:
            parts.append(str(value))

    return " ".join(parts).strip().lower()


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in hints)


def _looks_like_date(value: str) -> bool:
    text = str(value).strip()
    patterns = (
        r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$",
        r"^\d{4}[./-]\d{1,2}[./-]\d{1,2}$",
        r"^\d{6}$",
        r"^\d{8}$",
    )
    return any(re.match(pattern, text) for pattern in patterns)


def _looks_like_label_value(value: str) -> bool:
    text = " ".join(str(value).strip().lower().split())

    if not text:
        return True

    labels = {
        "surname",
        "given names",
        "name",
        "date of birth",
        "birth date",
        "place of birth",
        "nationality",
        "sex",
        "address",
        "residence",
        "phone",
        "telephone",
        "telefon",
        "email",
        "e-mail",
        "fax",
        "iban",
        "bic",
        "betrag",
        "amount",
        "datum",
        "date",
        "nr",
        "nummer",
        "number",
        "kundennummer",
        "versichertennummer",
        "steuer-id",
        "identifikationsnummer",
        "prénoms",
        "/ prénoms",
        "religious name or pseudonym",
        "/ religious name or pseudonym /",
        "residence./ do",
        "arbeitgeber",
        "arbeitnehmer",
        "employee",
        "employer",
        "beschäftigungsbetrieb",
        "beschaftigungsbetrieb",
        "beschäftigungsort",
        "beschaftigungsort",
        "steuer",
        "finanzamt",
        "krankenkasse",
        "versicherung",
        "formular",
        "hinweis",
        "seite",
        "page",
    }

    if text in labels:
        return True

    return bool(len(text) <= 2 and not text.isdigit())


def _is_junk_value(cf: CandidateFact, field_name: str) -> bool:
    value = " ".join(str(cf.normalized_value).strip().split())
    lowered = value.lower()

    if not value:
        return True

    if len(value) <= 2:
        return True

    if lowered in {
        "-nr",
        "nr",
        "no",
        "n/a",
        "na",
        "none",
        "null",
        "and by",
        "by",
        "and",
        "or",
        "of",
        "the",
        "for",
        "from",
        "to",
        "contribution @",
        "contribution",
        "employee contribution",
        "employer contribution",
        "@",
        "-",
        "/",
        ".",
        ":",
        ";",
        ",",
        "zurdck",
        "zurück",
        "zurueck",
        "weiter",
        "bitte",
        "seite",
        "page",
        "formular",
        "tel",
        "telefon",
        "phone",
        "fax",
        "hotline",
        "kontakt",
        "contact",
        "service",
        "support",
        "zentrale",
        "durchwahl",
    }:
        return True

    if re.fullmatch(r"[\W_]+", value):
        return True

    if re.fullmatch(r"[-–—]*[a-zA-Z]{1,3}[-–—]*", value) and field_name not in {
        "sex",
        "gender",
    }:
        return True

    if (
        field_name in _WEAK_PERSON_FIELDS
        and len(value.split()) <= 2
        and lowered
        in {
            "and by",
            "-nr",
            "contribution @",
            "contribution",
            "employee",
            "employer",
            "monthly",
            "annual",
            "gross",
            "net",
        }
    ):
        return True

    if "@" in value and field_name not in {"email", "contact_email"}:
        return True

    if field_name in {"surname", "given_names", "first_name", "last_name"} and any(
        char.isdigit() for char in value
    ):
        return True

    if _contains_any(lowered, _FORM_VALUE_NOISE_HINTS):
        return True

    return bool(_is_probably_ocr_fragment(value))


def _is_non_person_contact(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    context = _candidate_context_text(cf)
    value = str(cf.normalized_value).strip().lower()

    if field not in {
        "email",
        "phone_number",
        "phone",
        "telephone",
        "mobile",
        "fax",
        "tel",
        "telefon",
        "contact_email",
        "contact_phone",
    }:
        return False

    if _contains_any(context, _NON_PERSON_CONTEXT_HINTS):
        return True

    if field in _PHONE_FIELDS:
        return _contains_any(context, _PHONE_CONTEXT_NOISE_HINTS)

    if field in {"email", "contact_email"}:
        organization_tokens = (
            "info@",
            "kontakt@",
            "service@",
            "post@",
            "mail@",
            "support@",
            "team@",
            "office@",
            "verwaltung@",
            "kundenservice@",
            "datenschutz@",
            "bewerbung@",
            "rechnung@",
            "buchhaltung@",
            "personal@",
            "hr@",
            "noreply@",
            "no-reply@",
            "donotreply@",
        )

        if any(token in value for token in organization_tokens):
            return True

        return _contains_any(value, _ORGANIZATION_VALUE_HINTS)

    return False


def _is_likely_organization_name(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    value = " ".join(str(cf.normalized_value).strip().lower().split())
    context = _candidate_context_text(cf)

    if field not in _PERSON_NAME_FIELDS:
        return False

    if _contains_any(value, _ORGANIZATION_VALUE_HINTS):
        return True

    if _contains_any(context, _NON_PERSON_CONTEXT_HINTS) and len(value.split()) >= 2:
        return True

    if re.search(r"\b[a-zäöüß]+straße\b", value):
        return True

    if re.search(r"\b[a-zäöüß]+str\.\b", value):
        return True

    return bool(re.search(r"\b\d{5}\b", value))


def _is_non_person_iban(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    context = _candidate_context_text(cf)

    if field not in {"iban", "organization_iban"}:
        return False

    return _contains_any(context, _NON_PERSON_CONTEXT_HINTS) or _contains_any(
        context,
        (
            "zahlungsempfänger",
            "zahlungsempfaenger",
            "kontoinhaber",
            "bankverbindung",
            "empfänger",
            "empfaenger",
            "gläubiger",
            "glaeubiger",
            "creditor",
            "recipient bank",
        ),
    )


def _is_organization_context(cf: CandidateFact) -> bool:
    context = _candidate_context_text(cf)
    value = str(cf.normalized_value).strip().lower()

    return _contains_any(context, _NON_PERSON_CONTEXT_HINTS) or _contains_any(
        value,
        _ORGANIZATION_VALUE_HINTS,
    )


def _is_weak_person_field_noise(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    value = " ".join(str(cf.normalized_value).strip().split())
    lowered = value.lower()

    if field not in _WEAK_PERSON_FIELDS:
        return False

    if len(value) < 4:
        return True

    if len(value.split()) <= 2 and lowered in {
        "and by",
        "-nr",
        "contribution",
        "contribution @",
        "employee",
        "employer",
        "monthly",
        "annual",
        "gross",
        "net",
    }:
        return True

    return bool(re.search(r"[@:/\\]", value))


def _is_address_noise(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    value = " ".join(str(cf.normalized_value).strip().split()).lower()
    context = _candidate_context_text(cf)

    if field not in _ADDRESS_FIELDS:
        return False

    if len(value) < 8:
        return True

    if _contains_any(value, _ADDRESS_JUNK_HINTS):
        return True

    if _contains_any(context, _FORM_CONTEXT_HINTS) and not _looks_like_real_address(
        value
    ):
        return True

    if _contains_any(context, _BUSINESS_CONTEXT_HINTS) and not _looks_like_real_address(
        value
    ):
        return True

    if _contains_any(
        context, _AUTHORITY_CONTEXT_HINTS
    ) and not _looks_like_real_address(value):
        return True

    return not _looks_like_real_address(value)


def _looks_like_real_address(value: str) -> bool:
    text = " ".join(str(value).strip().lower().split())

    street_hints = (
        "straße",
        "strasse",
        "str.",
        "weg",
        "platz",
        "allee",
        "ring",
        "gasse",
        "ufer",
        "chaussee",
        "damm",
        "steig",
        "pfad",
        "markt",
        "street",
        "road",
        "avenue",
        "ave",
        "lane",
        "drive",
        "blvd",
    )

    has_street_hint = _contains_any(text, street_hints)
    has_postal_code = bool(re.search(r"\b\d{5}\b", text))
    has_house_number = bool(re.search(r"\b\d+[a-z]?\b", text))
    has_city_like_tail = bool(
        re.search(r"\b\d{5}\s+[a-zäöüß][a-zäöüß\-\s]{2,}\b", text)
    )

    return (
        has_city_like_tail
        or (has_street_hint and has_house_number)
        or (has_postal_code and len(text.split()) >= 2)
    )


def _is_phone_noise(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    value = " ".join(str(cf.normalized_value).strip().split())
    lowered = value.lower()
    context = _candidate_context_text(cf)
    digits = re.sub(r"\D", "", value)

    if field not in _PHONE_FIELDS:
        return False

    if not digits:
        return True

    if len(digits) < 10:
        return True

    if len(digits) > 16:
        return True

    if lowered.startswith(_PHONE_VALUE_NOISE_PREFIXES):
        return True

    if field == "fax":
        return True

    if _contains_any(context, _NON_PERSON_CONTEXT_HINTS):
        return True

    if _contains_any(context, _PHONE_CONTEXT_NOISE_HINTS):
        return True

    if re.search(r"\bfax\b", context):
        return True

    if re.search(r"\btel\.?\b", context) and _contains_any(
        context,
        _AUTHORITY_CONTEXT_HINTS,
    ):
        return True

    if lowered.startswith(("0800", "0180", "0137", "0900")):
        return True

    if re.search(r"\b\d{3,5}\s*/\s*\d{3,8}\b", value):
        return True

    if re.search(r"\b\d{3,5}\s*-\s*\d{3,8}\s*-\s*\d{1,5}\b", value):
        return True

    if re.fullmatch(r"0\d{2,5}[-\s]\d{3,8}(?:[-\s]\d{1,5})?", value):
        return True

    if re.search(
        r"\b\d{2,5}[-\s]\d{3,8}(?:[-\s]\d{1,5})?\b",
        value,
    ) and not lowered.startswith(("+49", "0049", "01")):
        return True

    if re.fullmatch(r"\+49\s?\d{2,5}\s?\d{3,8}(?:\s?\d{1,5})?", value):
        return _contains_any(context, _NON_PERSON_CONTEXT_HINTS)

    return False


def _is_reference_noise(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    value = " ".join(str(cf.normalized_value).strip().lower().split())
    context = _candidate_context_text(cf)

    if field not in _REFERENCE_FIELDS:
        return False

    if len(value) <= 3:
        return True

    if _contains_any(value, _REFERENCE_NOISE_HINTS):
        return True

    if _contains_any(context, _FORM_CONTEXT_HINTS):
        return True

    if _contains_any(context, _AUTHORITY_CONTEXT_HINTS):
        return True

    if _contains_any(context, _HEALTH_CONTEXT_HINTS):
        return True

    if _contains_any(context, _TAX_CONTEXT_HINTS):
        return True

    if _contains_any(context, _BANK_CONTEXT_HINTS):
        return True

    if re.fullmatch(r"[\W_]+", value):
        return True

    return bool(
        re.fullmatch(r"[a-zäöüß\s\-]{4,}", value)
        and not any(char.isdigit() for char in value)
    )


def _is_form_value_noise(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    value = " ".join(str(cf.normalized_value).strip().lower().split())
    context = _candidate_context_text(cf)

    if field in _PROTECTED_PERSON_FIELDS and _has_strong_person_signal(cf, field):
        return False

    if _contains_any(value, _FORM_VALUE_NOISE_HINTS):
        return True

    if (
        _contains_any(context, _FORM_CONTEXT_HINTS)
        and field not in _PROTECTED_PERSON_FIELDS
    ):
        return True

    if len(value.split()) >= 7 and not _looks_like_real_address(value):
        return True

    return bool(
        re.search(r"\bbitte\b|\bankreuzen\b|\bausfüllen\b|\bausfuellen\b", value)
    )


def _is_name_noise(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    value = " ".join(str(cf.normalized_value).strip().split())
    lowered = value.lower()
    context = _candidate_context_text(cf)

    if field not in _NAME_FIELDS:
        return False

    if not value:
        return True

    if _contains_any(lowered, _NAME_CONTEXT_NOISE_HINTS):
        return True

    if _contains_any(context, _NAME_CONTEXT_NOISE_HINTS):
        return True

    if value.endswith(("-", "–", "—")):
        return True

    if any(char.isdigit() for char in value):
        return True

    if re.search(r"[&@:/\\|{}<>]", value):
        return True

    if len(value.split()) >= 4:
        return True

    if lowered.startswith(_NAME_VALUE_NOISE_PREFIXES):
        return True

    if lowered in {
        "herr",
        "frau",
        "mr",
        "mrs",
        "ms",
        "dr",
        "prof",
    }:
        return True

    if _contains_any(context, _AUTHORITY_CONTEXT_HINTS):
        return True

    return bool(
        _contains_any(context, _BUSINESS_CONTEXT_HINTS)
        and field in {"surname", "given_names", "first_name", "last_name"}
    )


def _is_domain_specific_noise(cf: CandidateFact, field_name: str) -> bool:
    field = field_name.strip().lower()
    context = _candidate_context_text(cf)
    value = " ".join(str(cf.normalized_value).strip().lower().split())

    if field in _PROTECTED_PERSON_FIELDS and _has_strong_person_signal(cf, field):
        return False

    if (
        _contains_any(context, _FORM_CONTEXT_HINTS)
        and field not in _PROTECTED_PERSON_FIELDS
    ):
        return True

    if _contains_any(context, _HEALTH_CONTEXT_HINTS) and field in {
        "name",
        "address",
        "reference",
        "number",
        "case_number",
        "organization",
    }:
        return True

    if _contains_any(context, _TAX_CONTEXT_HINTS) and field in {
        "name",
        "address",
        "date",
        "document_date",
        "reference",
        "number",
        "case_number",
    }:
        return True

    if _contains_any(context, _BUSINESS_CONTEXT_HINTS) and field in {
        "address",
        "employer",
        "employee",
        "occupation",
        "job_title",
        "reference",
        "number",
    }:
        return True

    if _contains_any(context, _BANK_CONTEXT_HINTS) and field in {
        "name",
        "address",
        "reference",
        "number",
        "case_number",
    }:
        return True

    if _contains_any(context, _AUTHORITY_CONTEXT_HINTS) and field in {
        "name",
        "address",
        "reference",
        "number",
        "case_number",
    }:
        return True

    if field in _PHONE_FIELDS and _contains_any(context, _PHONE_CONTEXT_NOISE_HINTS):
        return True

    if field in _PHONE_FIELDS and _contains_any(context, _AUTHORITY_CONTEXT_HINTS):
        return True

    if field in _PHONE_FIELDS and _contains_any(context, _HEALTH_CONTEXT_HINTS):
        return True

    if field in _PHONE_FIELDS and _contains_any(context, _TAX_CONTEXT_HINTS):
        return True

    if field in _PHONE_FIELDS and _contains_any(context, _BUSINESS_CONTEXT_HINTS):
        return True

    if field in _REFERENCE_FIELDS and _contains_any(context, _NON_PERSON_CONTEXT_HINTS):
        return True

    return bool(
        field in {"address", "name", "reference", "number"}
        and _contains_any(value, _NON_PERSON_CONTEXT_HINTS)
    )


def _has_strong_person_signal(cf: CandidateFact, field_name: str) -> bool:
    context = _candidate_context_text(cf)
    value = " ".join(str(cf.normalized_value).strip().split())

    if field_name in {"surname", "given_names", "first_name", "last_name", "full_name"}:
        if _contains_any(context, _DATE_OF_BIRTH_HINTS):
            return True
        if re.fullmatch(r"[A-ZÄÖÜ][a-zäöüß]+(?:[-\s][A-ZÄÖÜ][a-zäöüß]+){0,3}", value):
            return True

    if field_name == "date_of_birth":
        return _looks_like_date(value)

    if field_name in _ADDRESS_FIELDS:
        return _looks_like_real_address(value)

    return False


def _is_probably_ocr_fragment(value: str) -> bool:
    text = " ".join(str(value).strip().split())
    lowered = text.lower()

    if len(text) < 5:
        return False

    if len(text.split()) >= 8 and not any(char.isdigit() for char in text):
        return True

    if lowered.count("(") != lowered.count(")"):
        return True

    if re.search(r"[|{}<>]", text):
        return True

    return bool(re.search(r"\b[a-z]{1,2}\s+[a-z]{1,2}\s+[a-z]{1,2}\b", lowered))


def _is_probably_birth_date_context(context: str) -> bool:
    return _contains_any(context, _DATE_OF_BIRTH_HINTS) or _contains_any(
        context,
        (
            "passport",
            "reisepass",
            "personalausweis",
            "identity card",
            "id card",
            "aufenthaltstitel",
            "residence permit",
            "nationality",
            "staatsangehörigkeit",
            "staatsangehoerigkeit",
        ),
    )


def _build_fact_evidence_links(
    fact_by_candidate: dict[CandidateFactId, Fact],
    evidence_by_candidate: dict[CandidateFactId, Evidence],
    candidate_facts: tuple[CandidateFact, ...],
) -> tuple[FactEvidence, ...]:
    links: list[FactEvidence] = []

    for cf in candidate_facts:
        fact = fact_by_candidate.get(cf.candidate_fact_id)
        evidence = evidence_by_candidate.get(cf.candidate_fact_id)
        if fact is None or evidence is None:
            continue

        links.append(
            FactEvidence.create(
                fact_id=fact.fact_id,
                evidence_id=evidence.evidence_id,
                role=FactEvidenceRole.PRIMARY,
            )
        )

    return tuple(links)


def _build_provenance_records(
    entity_id: EntityId,
    fact_by_candidate: dict[CandidateFactId, Fact],
    evidence_by_candidate: dict[CandidateFactId, Evidence],
    candidate_facts: tuple[CandidateFact, ...],
) -> tuple[Provenance, ...]:
    records: list[Provenance] = []

    for cf in candidate_facts:
        fact = fact_by_candidate.get(cf.candidate_fact_id)
        evidence = evidence_by_candidate.get(cf.candidate_fact_id)

        if fact is None:
            continue

        records.append(
            Provenance.create(
                fact_id=fact.fact_id,
                entity_id=entity_id,
                decision_chain=[
                    ProvenanceStep(
                        step_order=0,
                        action="extracted",
                        actor=_resolve_actor(cf.source_stage),
                        occurred_at=fact.created_at,
                        evidence_id=evidence.evidence_id if evidence else None,
                        note=f"raw_value={cf.raw_value!r} confidence={cf.confidence}",
                    ),
                ],
                summary=(
                    f"Fact '{fact.field_name}' extracted from source "
                    f"'{cf.source_id}' with confidence {cf.confidence}"
                ),
            )
        )

    return tuple(records)


def _build_conflicts(
    entity_id: EntityId,
    resolution: EntityResolutionResult,
    fact_by_candidate: dict[CandidateFactId, Fact],
) -> tuple[Conflict, ...]:
    if not resolution.has_conflicts:
        return ()

    conflicts: list[Conflict] = []

    for field_name, competing_ids in resolution.conflict_details.items():
        fact_ids: list[str] = []

        for cid in competing_ids:
            fact = fact_by_candidate.get(cid)
            if fact is None:
                continue
            fact_ids.append(fact.fact_id)

        if len(fact_ids) < 2:
            continue

        conflicts.append(
            Conflict.create(
                entity_id=entity_id,
                field_name=field_name,
                fact_ids=fact_ids,
            )
        )

    return tuple(conflicts)


def _resolve_actor(source_stage: str) -> str:
    lowered = source_stage.lower()
    if "ocr" in lowered:
        return ProvenanceActor.OCR
    if "mrz" in lowered:
        return ProvenanceActor.SYSTEM
    if "regex" in lowered:
        return ProvenanceActor.SYSTEM
    if "manual" in lowered:
        return ProvenanceActor.USER
    return ProvenanceActor.SYSTEM
