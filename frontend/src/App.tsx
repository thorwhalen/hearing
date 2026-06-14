// The app shell: upload an audio file, transcribe it via the Python API, and
// render the diarized transcript (me/them lanes) plus optional AI notes.
//
// State is deliberately minimal and local (useState) — for a frontend novice,
// that's the simplest correct tool. The transcript shape comes straight from the
// shared Zod schema, so there's no hand-mapping of API fields to UI fields.
import { useEffect, useRef, useState } from 'react';
import { getHealth, transcribeFile, transcribeStream, type TranscribeResponse } from './api';
import { type Feedback } from './schema';
import { FeedbackPanel } from './components/FeedbackPanel';
import { SummaryPanel } from './components/SummaryPanel';
import { TranscriptView } from './components/TranscriptView';

export function App() {
  const [result, setResult] = useState<TranscribeResponse | null>(null);
  const [liveFeedback, setLiveFeedback] = useState<Feedback[]>([]);
  const [query, setQuery] = useState('');
  const [summarize, setSummarize] = useState(true);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getHealth()
      .then((h) => setVersion(h.version))
      .catch(() => setVersion(null)); // backend not running yet — that's fine
  }, []);

  async function onUpload(file: File) {
    setLoading(true);
    setError(null);
    try {
      if (live) {
        // Live mode: start with an empty meeting and append segments as they stream in.
        setLiveFeedback([]);
        setResult({
          meeting: { id: '', title: file.name, startedAt: '', durationMs: 0, participants: [], segmentCount: 0 },
          segments: [],
        });
        await transcribeStream(
          file,
          {
            onMeeting: (m) =>
              setResult((prev) => (prev ? { ...prev, meeting: { ...prev.meeting, ...m } } : prev)),
            onFeedback: (f) => setLiveFeedback((prev) => [...prev, f]),
            onSegment: (s) =>
              setResult((prev) => {
                if (!prev) return prev;
                const segments = [...prev.segments, s];
                return {
                  ...prev,
                  segments,
                  meeting: {
                    ...prev.meeting,
                    segmentCount: segments.length,
                    durationMs: Math.max(prev.meeting.durationMs, s.endMs),
                    participants: Array.from(new Set(segments.map((x) => x.speaker))),
                  },
                };
              }),
          },
          { title: file.name },
        );
      } else {
        setResult(await transcribeFile(file, { summarize }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>hearing</h1>
        <span className="tagline">
          meeting transcript {version ? `· API v${version}` : '· start `hearing serve`'}
        </span>
      </header>

      <section className="controls">
        <input
          ref={fileRef}
          type="file"
          accept="audio/*,.wav,.aiff,.flac"
          onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
          disabled={loading}
        />
        <label className="check">
          <input
            type="checkbox"
            checked={summarize}
            disabled={live}
            onChange={(e) => setSummarize(e.target.checked)}
          />
          AI notes
        </label>
        <label className="check">
          <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />
          Live stream
        </label>
        <input
          className="search"
          type="search"
          placeholder="Search transcript…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={!result}
        />
      </section>

      {loading && <p className="status">Transcribing… (first run downloads the model)</p>}
      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <div className="meeting-meta">
            <strong>{result.meeting.title}</strong> · {result.meeting.segmentCount} segments ·{' '}
            {result.meeting.participants.join(', ')}
          </div>
          <div className="layout">
            <TranscriptView segments={result.segments} query={query} />
            {live ? <FeedbackPanel items={liveFeedback} /> : <SummaryPanel summary={result.summary} />}
          </div>
        </>
      )}
    </div>
  );
}
