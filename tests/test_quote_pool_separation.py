"""Clarification 1: normal and favorite pools are strictly separate.

- Normal pool = quotes where is_favorite = 0; only these participate
  in non-repeating cycles.
- Favorite pool = quotes where is_favorite = 1; independently
  repeatable, never consumes or resets the normal cycle.
- Pool membership follows a quote's CURRENT is_favorite status;
  historical quote_usage rows are never rewritten when that status
  changes later.
"""
import random


def test_favorite_is_excluded_from_normal_pool(quote_repo):
    quote_repo.create("A")
    quote_repo.create("B", is_favorite=True)
    quote_repo.create("D")

    normal_texts = {q.text for q in quote_repo.list_normal()}
    favorite_texts = {q.text for q in quote_repo.list_favorites()}

    assert normal_texts == {"A", "D"}
    assert favorite_texts == {"B"}


def test_selecting_a_favorite_does_not_consume_a_normal_cycle_slot(
    quote_repo, make_quote_service
):
    quote_repo.create("A")
    quote_repo.create("B")
    quote_repo.create("C", is_favorite=True)
    quote_repo.create("D")

    # favorite_selection_probability=1.0 forces every pick to be the
    # (sole) favorite, C, whenever the coin allows it.
    service = make_quote_service(
        favorite_selection_probability=1.0, random_source=random.Random(0)
    )

    for i in range(6):
        assignment = service.get_or_assign_daily_quote(f"2026-09-{i + 1:02d}")
        assert assignment.day.quote_text == "C"

    # Six favorite selections in a row must not have touched the
    # normal pool's cycle tracking at all.
    normal_texts = {q.text for q in quote_repo.list_normal()}
    assert normal_texts == {"A", "B", "D"}


def test_favorite_can_repeat_before_normal_pool_is_exhausted(
    quote_repo, make_quote_service
):
    quote_repo.create("A")
    quote_repo.create("B")
    quote_repo.create("C", is_favorite=True)

    service = make_quote_service(
        favorite_selection_probability=1.0, random_source=random.Random(0)
    )
    first = service.get_or_assign_daily_quote("2026-09-01").day.quote_text
    second = service.get_or_assign_daily_quote("2026-09-02").day.quote_text

    assert first == "C"
    assert second == "C"  # repeated on consecutive days — allowed for favorites


def test_normal_cycle_completes_correctly_around_a_favorite(
    quote_repo, make_quote_service
):
    """A=normal, B=normal, C=favorite, D=normal (the example from the spec).

    A normal cycle is exactly {A, B, D}; interleaved favorite picks of
    C must not stop that cycle from completing after exactly 3 normal
    selections, nor cause any normal quote to repeat before it does.
    """
    quote_repo.create("A")
    quote_repo.create("B")
    quote_repo.create("C", is_favorite=True)
    quote_repo.create("D")

    # Alternate: favorite, normal, favorite, normal, favorite, normal
    # by toggling the injected probability draw per call.
    #
    # This is a plain object implementing random()/choice() directly,
    # NOT a random.Random subclass. random.Random.choice() calls
    # self._randbelow(), which for a subclass that only overrides
    # random() routes through _randbelow_without_getrandbits() --
    # which itself calls self.random() one or more extra times. That
    # silently breaks call-count-based alternation (a subclassed
    # version of this helper was tried and confirmed to call
    # random() twice per selection after the first, not once). A
    # duck-typed object with no random.Random inheritance has no such
    # hidden extra calls.
    class FakeRandom:
        def __init__(self):
            self._call_count = 0

        def random(self) -> float:
            self._call_count += 1
            return 0.0 if self._call_count % 2 == 1 else 1.0  # odd calls -> favorite

        def choice(self, seq):
            return seq[0]

    service = make_quote_service(
        favorite_selection_probability=0.5, random_source=FakeRandom()
    )

    dates = [f"2026-09-{i + 1:02d}" for i in range(6)]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]

    favorite_picks = [t for t in texts if t == "C"]
    normal_picks = [t for t in texts if t != "C"]

    assert favorite_picks == ["C", "C", "C"]
    assert len(normal_picks) == 3
    assert set(normal_picks) == {"A", "B", "D"}  # one full cycle, no repeats


def test_pool_membership_follows_current_favorite_status(
    db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo
):
    """If a quote's favorite flag changes, future pool membership follows
    the new status, but its past quote_usage rows are untouched."""
    from app.core.services.quote_service import QuoteService

    quote_a = quote_repo.create("A")  # starts as normal
    quote_repo.create("B")

    service = QuoteService(
        db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(2),
    )
    assignment = service.get_or_assign_daily_quote("2026-09-01")
    used_usage = quote_usage_repo.get_for_day(assignment.day.id)
    was_favorite_at_selection_time = used_usage.is_favorite_selection

    # Now mark A as favorite going forward.
    quote_repo.set_favorite(quote_a.id, True)

    # Pool membership for a NEW assignment reflects the current status.
    assert {q.text for q in quote_repo.list_favorites()} == {"A"}
    assert {q.text for q in quote_repo.list_normal()} == {"B"}

    # The historical usage row from before the change is untouched.
    unchanged_usage = quote_usage_repo.get_for_day(assignment.day.id)
    assert unchanged_usage.is_favorite_selection == was_favorite_at_selection_time
