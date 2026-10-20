"""Prior meetings' takeaways as retrievable context, and record= into a MeetingStore (#5, part 2). Offline."""

import asyncio

from hearing.agents import ExtractiveAgent, build_default_agent
from hearing.context import CombinedRetriever, KeywordRetriever, meeting_retriever
from hearing.pipeline import _persist
from hearing.storage import MeetingStore
from hearing.types import TimeSpan, Transcript, TranscriptSegment


def _transcript(text, insight=None):
    t = Transcript([TranscriptSegment(text, TimeSpan(0, 1000))])
    return t.with_meta(insight=insight) if insight else t


def test_takeaways_of_prior_meetings_are_retrievable_and_the_current_one_excluded():
    store = MeetingStore({})
    store.save("0512.wav", _transcript("long talk about databases", "Decision: keep Postgres. Owner: ana."))
    store.save("0519.wav", _transcript("pricing chat", "Decision: raise the price in June."))
    store.save("0526.wav", _transcript("today", "Decision: Postgres again?"))
    memory = meeting_retriever(store, exclude=["0526.wav"])
    hits = asyncio.run(memory.search("postgres decision"))
    assert hits[0].source == "meeting:0512.wav" and "meeting:0526.wav" not in {h.source for h in hits}
    assert hits[0].title == "takeaways 0512.wav"
    full = meeting_retriever(store.store, transcripts=True)  # the raw mapping works too
    assert "transcript 0512.wav" in {h.title for h in asyncio.run(full.search("databases"))}


def test_record_accepts_a_meeting_store_or_a_mapping_and_both_feed_memory():
    store = MeetingStore({})
    _persist(_transcript("hello", "Takeaway: ship Friday."), "/calls/standup.wav", store)
    mapping = {}
    _persist(_transcript("hello", "Takeaway: ship Friday."), "/calls/standup.wav", mapping)
    assert list(store.store) == list(mapping) == ["standup.wav.transcript.json"]
    for meetings in (store, mapping):
        assert asyncio.run(meeting_retriever(meetings).search("ship friday"))


def test_history_joins_the_agents_retriever():
    store = MeetingStore({})
    store.save("m1", _transcript("x", "Decision: Postgres."))
    project = KeywordRetriever({"notes": "Postgres hosting on example.org"})
    agent = build_default_agent(prefer="claude", retriever=project, history=store)
    assert isinstance(agent.retriever, CombinedRetriever)
    titles = {c.title for c in asyncio.run(agent.retriever.search("postgres"))}
    assert titles == {"notes", "takeaways m1"}
    assert isinstance(build_default_agent(prefer="extractive", history=store), ExtractiveAgent)


def test_a_recorded_transcript_keeps_its_insight_and_old_records_still_load():
    import json

    from hearing.storage import transcript_from_json

    mapping = {}
    _persist(_transcript("hello", "Takeaway: ship Friday."), "standup.wav", mapping)
    assert transcript_from_json(mapping["standup.wav.transcript.json"]).meta["insight"] == "Takeaway: ship Friday."
    legacy = json.dumps([{"text": "hi", "start_ms": 0, "end_ms": 5}])
    assert transcript_from_json(legacy).text == "hi"
