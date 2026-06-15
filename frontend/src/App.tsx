// The app shell: record your mic or drop a file, transcribe via the backend,
// and render the diarized transcript plus AI notes (batch) or a live copilot.
//
// Settings (engine, model, AI notes, live, API base URL) persist in the browser
// and default to the cheapest options. The manual (Help) explains everything.
import { useEffect, useMemo, useRef, useState } from 'react';
// The manual markdown is the single source of truth (repo: misc/docs/MANUAL.md),
// imported raw at build time and rendered in-app.
import manualMarkdown from '../../misc/docs/MANUAL.md?raw';
import { getHealth, resolveApiBase, transcribeFile, transcribeStream, type TranscribeResponse } from './api';
import { buildCommands, type CommandContext } from './commands';
import { type Feedback } from './schema';
import { DEFAULT_SETTINGS, loadSettings, saveSettings, type Settings } from './settings';
import { useRecorder } from './useRecorder';
import { BackendBanner } from './components/BackendBanner';
import { CommandPalette } from './components/CommandPalette';
import { FeedbackPanel } from './components/FeedbackPanel';
import { ManualView } from './components/ManualView';
import { SettingsPanel } from './components/SettingsPanel';
import { SummaryPanel } from './components/SummaryPanel';
import { TranscriptView } from './components/TranscriptView';

export function App() {
  const [settings, setSettings] = useState<Settings>(() => loadSettings() ?? DEFAULT_SETTINGS);
  const [result, setResult] = useState<TranscribeResponse | null>(null);
  const [liveFeedback, setLiveFeedback] = useState<Feedback[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null); // null = checking
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const { recording, error: recError, start, stop } = useRecorder();

  const backendUrl = resolveApiBase(settings.apiBase) || (typeof location !== 'undefined' ? location.origin : '');

  // Probe the backend. Returns true if reachable; updates the banner state.
  async function probeBackend(): Promise<boolean> {
    try {
      const h = await getHealth(settings.apiBase);
      setVersion(h.version);
      setBackendOk(true);
      return true;
    } catch {
      setVersion(null);
      setBackendOk(false);
      return false;
    }
  }

  // Check on landing (and whenever the target backend changes), so the user is
  // told immediately if it's missing — not after a wasted recording.
  useEffect(() => {
    setBackendOk(null);
    probeBackend();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.apiBase]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const commands = useMemo(() => buildCommands(), []);
  const commandCtx: CommandContext = {
    result,
    focusSearch: () => searchRef.current?.focus(),
    clear: () => {
      setResult(null);
      setLiveFeedback([]);
    },
  };

  function patch(p: Partial<Settings>) {
    const next = { ...settings, ...p };
    setSettings(next);
    saveSettings(next);
  }

  async function runTranscription(file: File) {
    setLoading(true);
    setError(null);
    const common = { engine: settings.engine, model: settings.model, apiBase: settings.apiBase, title: file.name };
    try {
      if (settings.live) {
        setLiveFeedback([]);
        setResult({
          meeting: { id: '', title: file.name, startedAt: '', durationMs: 0, participants: [], segmentCount: 0 },
          segments: [],
        });
        await transcribeStream(
          file,
          {
            onMeeting: (m) => setResult((p) => (p ? { ...p, meeting: { ...p.meeting, ...m } } : p)),
            onFeedback: (f) => setLiveFeedback((p) => [...p, f]),
            onSegment: (s) =>
              setResult((p) => {
                if (!p) return p;
                const segments = [...p.segments, s];
                return {
                  ...p,
                  segments,
                  meeting: {
                    ...p.meeting,
                    segmentCount: segments.length,
                    durationMs: Math.max(p.meeting.durationMs, s.endMs),
                    participants: Array.from(new Set(segments.map((x) => x.speaker))),
                  },
                };
              }),
          },
          common,
        );
      } else {
        setResult(await transcribeFile(file, { ...common, summarize: settings.aiNotes }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onRecordToggle() {
    if (recording) {
      const file = await stop();
      if (file) await runTranscription(file);
      return;
    }
    // About to record — confirm the backend is up FIRST, so we never record into
    // the void and only find out on Stop.
    if (!(await probeBackend())) {
      setError(
        `Can't reach the hearing backend at ${backendUrl}. Start it first: run ` +
          '`hearing serve` in a terminal, then click Record again. (Nothing was recorded.)',
      );
      return;
    }
    setError(null);
    await start();
  }

  return (
    <div className="app">
      <header>
        <h1>hearing</h1>
        <span className="tagline">
          meeting transcript {version ? `· API v${version}` : '· start `hearing serve`'}
        </span>
        <button className="link-btn" onClick={() => setManualOpen(true)}>Help</button>
        <button className="link-btn" onClick={() => setSettingsOpen(true)}>⚙ Settings</button>
      </header>

      {backendOk === false && (
        <BackendBanner url={backendUrl} onRecheck={probeBackend} onHelp={() => setManualOpen(true)} />
      )}

      <section className="controls">
        <button className={`record-btn${recording ? ' on' : ''}`} onClick={onRecordToggle} disabled={loading}>
          {recording ? '■ Stop' : '● Record'}
        </button>
        <input
          type="file"
          accept="audio/*,.wav,.aiff,.flac,.mp3,.m4a,.webm"
          onChange={(e) => e.target.files?.[0] && runTranscription(e.target.files[0])}
          disabled={loading || recording}
        />
        <label className="check">
          <input type="checkbox" checked={settings.aiNotes} disabled={settings.live} onChange={(e) => patch({ aiNotes: e.target.checked })} />
          AI notes
        </label>
        <label className="check">
          <input type="checkbox" checked={settings.live} onChange={(e) => patch({ live: e.target.checked })} />
          Live
        </label>
        <input
          ref={searchRef}
          className="search"
          type="search"
          placeholder="Search transcript…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={!result}
        />
        <button className="kbd-hint" onClick={() => setPaletteOpen(true)} title="Command palette">⌘K</button>
      </section>

      {recording && (
        <p className="status recording">
          ● recording your microphone… press <b>■ Stop</b> to transcribe ·
          {' '}engine: {settings.engine}{settings.aiNotes ? ' · AI notes' : ''}{settings.live ? ' · live' : ''}
        </p>
      )}
      {loading && <p className="status">Transcribing… (first local run downloads the model)</p>}
      {(error || recError) && <p className="error">{error || recError}</p>}

      {result && (
        <>
          <div className="meeting-meta">
            <strong>{result.meeting.title}</strong> · {result.meeting.segmentCount} segments ·{' '}
            {result.meeting.participants.join(', ')}
          </div>
          <div className="layout">
            <TranscriptView segments={result.segments} query={query} />
            {settings.live ? <FeedbackPanel items={liveFeedback} /> : <SummaryPanel summary={result.summary} />}
          </div>
        </>
      )}

      <CommandPalette commands={commands} ctx={commandCtx} open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      {settingsOpen && (
        <SettingsPanel settings={settings} onChange={setSettings} onClose={() => setSettingsOpen(false)} />
      )}
      {manualOpen && <ManualView markdown={manualMarkdown} onClose={() => setManualOpen(false)} />}
    </div>
  );
}
