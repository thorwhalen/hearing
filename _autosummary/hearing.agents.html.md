# hearing.agents

The agent / “copilot” layer — the actual point of the hearing project.

An agent consumes a (speaker-labelled) transcript and produces feedback. The
*same* [`AgentConsumer`](hearing.interfaces.html.md#hearing.interfaces.AgentConsumer) interface serves both modes;
only *when* and *what granularity* it consumes differs:

* **batch** — `on_window(whole_transcript)` -> summary, action items,
  decisions, open questions, follow-up research (post-meeting).
* **live** — `on_segment(finalized_segment)` -> running notes, suggested
  questions, surfaced docs, fact-checks (as the meeting unfolds).

Agents are meant to be *context-connected*: bound to a meeting/project and able
to draw on accumulated knowledge (prior takeaways, the codebase, research
reports) and live web search. The `context` field is that hook.

The default backend is Claude (latest/most capable) but stays pluggable — see
the `claude-api` skill for model ids, pricing, tool use, and structured
output, and the `hearing-agents` skill for the queue-consumer pattern, RAG,
and the batch≡live unification.

### Module Attributes

| [`DEFAULT_CLAUDE_MODEL`](#hearing.agents.DEFAULT_CLAUDE_MODEL)   | A sensible, current default Claude model for meeting analysis.   |
|-------------------------------------------------------------------------|------------------------------------------------------------------|

### Functions

| [`build_default_agent`](#hearing.agents.build_default_agent)(\*[, context, model, ...])     | Pick the best available agent.                                           |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`summarize_transcript`](#hearing.agents.summarize_transcript)(transcript, \*[, agent, ...]) | Synchronous facade: run a (batch) agent over a transcript, return notes. |

### Classes

| [`ClaudeAgent`](#hearing.agents.ClaudeAgent)([model, context, system_prompt, ...])   | Context-connected meeting agent backed by Claude (the default).     |
|------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`ExtractiveAgent`](#hearing.agents.ExtractiveAgent)([max_key_points, action_cues])      | Deterministic, dependency-free fallback agent (no API, no network). |

### *class* hearing.agents.ClaudeAgent(model='claude-sonnet-4-6', context=None, system_prompt='You are a meeting assistant. Given a (speaker-labelled) transcript, produce a concise, well-structured analysis with these sections, omitting any that don\\'t apply:\\n\\n## Summary\\n2-4 sentences capturing what the meeting was about and its outcome.\\n\\n## Decisions\\nBullet points of decisions that were made.\\n\\n## Action items\\nBullet points as "- [owner] action" when an owner is identifiable, else "- action".\\n\\n## Open questions / follow-ups\\nBullet points of unresolved questions or things worth researching afterwards.\\n\\nBe faithful to the transcript; do not invent facts. Speakers labelled "me" are the local user; "them"/"spk_\*" are remote participants.', max_tokens=1024, api_key=None, retriever=None, web_search=None, retrieve_k=4, web_k=3)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Context-connected meeting agent backed by Claude (the default).

* **Parameters:**
  * **model** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Claude model id (see the `claude-api` skill).
  * **context** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – optional context to connect the agent to a meeting/project —
    prior takeaways, project notes, etc. Prepended to the prompt.
  * **system_prompt** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – override the default meeting-assistant instructions.
  * **max_tokens** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – output cap.

#### *async* on_segment(segment)

Live per-segment hook (milestone 2). No-op in the batch milestone.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### *async* on_window(window)

Analyze a whole transcript (batch) and return structured notes.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### hearing.agents.DEFAULT_CLAUDE_MODEL *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'claude-sonnet-4-6'*

A sensible, current default Claude model for meeting analysis. Override via
`model=` (e.g. “claude-opus-4-8” for max capability). See claude-api skill.

### *class* hearing.agents.ExtractiveAgent(max_key_points=5, action_cues=("let's", 'we should', "i'll", "we'll", 'need to', 'action', 'todo', 'to do', 'follow up', 'next step', 'assign', 'by friday', 'by monday', 'deadline'))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Deterministic, dependency-free fallback agent (no API, no network).

Produces a usable summary by extraction/heuristics so the app always does
*something* offline and tests stay deterministic. Detects naive action
items (imperative / commitment cues) and open questions (`?`).

#### action_cues *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ("let's", 'we should', "i'll", "we'll", 'need to', 'action', 'todo', 'to do', 'follow up', 'next step', 'assign', 'by friday', 'by monday', 'deadline')*

cues that hint a segment is an action item / commitment

#### *async* on_segment(segment)

Live per-segment hook: surface questions and action-item cues.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### *async* on_window(window)

Return a deterministic extractive summary of the window.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### hearing.agents.build_default_agent(, context=None, model=None, prefer='auto', retriever=None, web_search=None)

Pick the best available agent.

`prefer="claude"` forces Claude; `"extractive"` forces the offline
fallback; `"auto"` (default) uses Claude when the anthropic SDK and an API
key are available, otherwise the dependency-free [`ExtractiveAgent`](#hearing.agents.ExtractiveAgent).
A `retriever`/`web_search` make the Claude agent context-connected.

### hearing.agents.summarize_transcript(transcript, , agent=None, context=None, model=None, retriever=None, web_search=None)

Synchronous facade: run a (batch) agent over a transcript, return notes.

Builds the default agent when none is injected (context-connected when a
`retriever`/`web_search` is supplied). Usable on a transcript with no
audio at all.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
