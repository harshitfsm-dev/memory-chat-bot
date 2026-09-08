from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_EXTRACTED_MEMORIES = 12

MemoryKey = Literal[
    # Identity.
    "user_name",
    "user_location",
    "user_timezone",
    # Life context.
    "occupation",
    "hobby",
    "current_goal",
    "dietary_preference",
    # How the assistant should talk to them.
    "preferred_response_style",
    "preferred_explanation_level",
    "preferred_language",
    "preferred_measurement_system",
    "communication_preference",
]
"""The complete, fixed set of long-term profile fields.

This is the whole fact tier now: a small, closed list of stable things worth
knowing about a person and pinning into every prompt. It is closed so the tier
stays bounded — one row per key per user — and predictable, not to constrain the
*value*. Each key holds the user's own free text (see the note on `value` in
``ExtractedMemory``); the list of keys is fixed, the values are not.

Anything that is not one of these is not a fact. It belongs in a note, which is
the open, free-text tier for everything the profile cannot express.
"""

# Facts are pinned into every prompt verbatim, so their value is bounded tightly:
# a name, a place, an occupation, a preference is short, and anything long is a
# sign the extractor captured a sentence rather than a value.
MAX_FACT_VALUE_CHARS = 120

# The sentence stored for each fact key. `{value}` is the user's own short value,
# substituted in by the service after cleaning. Keeping this beside `MemoryKey`
# keeps the two in sync: every key must have a template.
FACT_TEMPLATES: dict[str, str] = {
    "user_name": "The user's name is {value}.",
    "user_location": "The user is located in {value}.",
    "user_timezone": "The user's timezone is {value}.",
    "occupation": "The user works in {value}.",
    "hobby": "The user is interested in {value}.",
    "current_goal": "The user's current goal is {value}.",
    "dietary_preference": "The user's dietary preference is {value}.",
    "preferred_response_style": "The user prefers {value} responses.",
    "preferred_explanation_level": "The user prefers {value} explanations.",
    "preferred_language": "The user prefers to communicate in {value}.",
    "preferred_measurement_system": "The user prefers {value}.",
    "communication_preference": "The user's communication preference: {value}.",
}
FACT_KEYS: frozenset[str] = frozenset(FACT_TEMPLATES)

MemoryCategory = Literal[
    "goal",
    "plan",
    "event",
    "project",
    "constraint",
    "interest",
    "other",
]
"""Closed routing dimension for notes.

Small on purpose: this is the one judgement a small extraction model has to make
consistently across turns. It decides a note's expiry horizon and how it is
displayed. `other` is the escape hatch that stops an unclassifiable-but-important
detail from being dropped.
"""

# The real policy limit on a note, applied by the service after whitespace is
# normalized. Bounds both prompt cost and the amount of user-authored text that
# can be replayed into a later prompt.
MAX_NOTE_CONTENT_CHARS = 200
MAX_NOTE_SUBJECT_CHARS = 80

# The schema limit is deliberately looser than the policy limit. Pydantic
# validates the whole batch at once, so a hard cap here would let one long note
# discard every other memory from the same turn. Over-long items are rejected
# individually by the service instead.
SCHEMA_NOTE_CONTENT_CHARS = 600


class ExtractedMemory(BaseModel):
    """One bounded memory candidate produced from a completed chat turn.

    Two shapes share this model:

    - Facts are one of the fixed profile keys with the user's own short value.
      The value is free text, so it is sanitized before it is pinned.
    - Notes are a category, a short subject, and a free-text sentence. They are
      also sanitized, and additionally expiry-checked and never pinned.

    Both tiers carry user-authored text, so both are cleaned and filtered by the
    service before storage. The old closed-vocabulary fact/episode machinery is
    gone: there is no generated-from-a-vocabulary tier any more.
    """

    memory_type: Literal["fact", "note"]
    memory_key: MemoryKey | None = Field(
        default=None,
        description="Profile fact key; null for notes",
    )
    value: str = Field(
        default="",
        # Loose here on purpose: the schema keeps the whole batch alive and the
        # service applies the real cap, so one over-long value cannot discard the
        # rest of the turn.
        max_length=SCHEMA_NOTE_CONTENT_CHARS,
        description=(
            "Facts only: the user's own value for this key, e.g. 'Alex', 'Berlin', "
            "'concise', 'vegetarian'. Keep it short — just the value, not a "
            "sentence. Leave empty for notes."
        ),
    )
    category: MemoryCategory | None = Field(
        default=None,
        description="Required for notes; null for facts",
    )
    subject: str = Field(
        default="",
        max_length=MAX_NOTE_SUBJECT_CHARS,
        description="Notes only: a few words naming what this is about",
    )
    content: str = Field(
        default="",
        max_length=SCHEMA_NOTE_CONTENT_CHARS,
        description=(
            "Notes only: one short third-person sentence stating what to remember. "
            "Leave empty for facts."
        ),
    )
    confidence: float = Field(default=0.8, ge=0, le=1)
    importance: float = Field(default=0.5, ge=0, le=1)
    is_correction: bool = Field(
        default=False,
        description=(
            "True only when the user explicitly corrects or replaces an older "
            "value for the same fact"
        ),
    )

    @model_validator(mode="after")
    def fields_match_memory_type(self) -> "ExtractedMemory":
        """Strip fields that do not belong to this shape, without rejecting.

        Deliberately coercive rather than strict. Pydantic validates the whole
        batch, so raising here would throw away every memory from a turn because
        one candidate was malformed. Anything still unusable after this (a fact
        with no key or no value, a note with no category or no content) is dropped
        individually by the service, which can log it and keep the rest.
        """
        if self.memory_type == "fact":
            self.category = None
            self.subject = ""
            self.content = ""
        else:
            self.memory_key = None
            self.value = ""
            self.is_correction = False
        return self


class MemoryExtraction(BaseModel):
    """Structured result returned by the post-turn memory extractor."""

    memories: list[ExtractedMemory] = Field(
        max_length=MAX_EXTRACTED_MEMORIES,
        description="Durable memories from this turn; empty when nothing qualifies",
    )


class MemoryItemResponse(BaseModel):
    """User-visible memory fields; embeddings and provenance stay private."""

    id: UUID
    memory_key: MemoryKey | None
    category: MemoryCategory | None
    subject: str | None
    content: str
    event_at: datetime | None
    valid_until: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserMemoriesResponse(BaseModel):
    """All active long-term memories, grouped by tier.

    Two groups now: the fixed profile facts, and the open-ended notes. Both are
    shown so someone can read back everything the system holds about them and
    delete anything that should not have been kept — which makes this listing part
    of the privacy story, not just a convenience.
    """

    facts: list[MemoryItemResponse]
    notes: list[MemoryItemResponse]
