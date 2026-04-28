from knowledge.knowledge_objects import FieldType


FIELD_PRIORITY: dict[FieldType, int] = {
    FieldType.IDENTITY: 100,
    FieldType.LEGAL: 90,
    FieldType.FINANCIAL: 80,
    FieldType.EMPLOYMENT: 70,
    FieldType.ADDRESS: 60,
    FieldType.DOCUMENT: 50,
    FieldType.CONTACT: 40,
    FieldType.OTHER: 10,
}

TAG_PRIORITY: dict[str, int] = {
    "primary": 100,
    "salary": 90,
    "work": 80,
    "personal": 70,
    "secondary": 50,
    "rental": 40,
    "savings": 30,
    "default": 10,
}


class PriorityManager:

    def field_priority(self, field_type: FieldType) -> int:
        return FIELD_PRIORITY.get(field_type, 10)

    def tag_priority(self, tag: str) -> int:
        return TAG_PRIORITY.get(tag, 10)

    def combined(self, field_type: FieldType, tag: str) -> int:
        return self.field_priority(field_type) + self.tag_priority(tag)

    def rank(self, items: list[dict]) -> list[dict]:
        return sorted(
            items,
            key=lambda x: self.combined(
                x.get("field_type", FieldType.OTHER), x.get("tag", "default")
            ),
            reverse=True,
        )


priority_manager = PriorityManager()
