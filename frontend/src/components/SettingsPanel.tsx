// Settings modal. Edits the persisted Settings; defaults are the least-expensive
// options (local STT, no AI). Closing saves to localStorage.
import { useState } from 'react';
import { saveSettings, type Settings } from '../settings';

interface Props {
  settings: Settings;
  onChange: (s: Settings) => void;
  onClose: () => void;
}

export function SettingsPanel({ settings, onChange, onClose }: Props) {
  const [s, setS] = useState<Settings>(settings);

  const set = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setS((prev) => ({ ...prev, [key]: value }));

  const close = () => {
    saveSettings(s);
    onChange(s);
    onClose();
  };

  return (
    <div className="palette-backdrop" onClick={close}>
      <div className="settings" onClick={(e) => e.stopPropagation()}>
        <h2>Settings</h2>
        <p className="muted">Defaults are the cheapest options — local, on-device, no API calls.</p>

        <label>
          STT engine
          <select value={s.engine} onChange={(e) => set('engine', e.target.value as Settings['engine'])}>
            <option value="whisper">whisper — local, free</option>
            <option value="openai">openai — cloud (needs key)</option>
          </select>
        </label>

        <label>
          Whisper model
          <select value={s.model} onChange={(e) => set('model', e.target.value)} disabled={s.engine !== 'whisper'}>
            {['tiny', 'base', 'small', 'medium', 'large-v3'].map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>

        <label className="row">
          <input type="checkbox" checked={s.aiNotes} onChange={(e) => set('aiNotes', e.target.checked)} />
          AI notes (Claude — needs API key)
        </label>
        <label className="row">
          <input type="checkbox" checked={s.live} onChange={(e) => set('live', e.target.checked)} />
          Live stream (segments appear as they finalize)
        </label>

        <label>
          API base URL
          <input
            type="text"
            placeholder="(same origin — leave blank)"
            value={s.apiBase}
            onChange={(e) => set('apiBase', e.target.value)}
          />
          <span className="muted small">
            Set to http://localhost:8000 to run compute on your own machine while the UI is hosted elsewhere.
          </span>
        </label>

        <div className="settings-actions">
          <button onClick={close}>Done</button>
        </div>
      </div>
    </div>
  );
}
