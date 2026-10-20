// Settings modal. Edits the persisted Settings; defaults are the least-expensive
// options (local STT, no AI). Closing saves to localStorage.
//
// The fields are generated from the settings schema (settings.ts) by SchemaForm:
// this file only says what depends on the current values (the Whisper model is
// for the whisper engine only) and how the engine options read.
import { useState } from 'react';
import { type FormFieldConfig } from '@zodal/ui';
import { saveSettings, settings as settingsCollection, type Settings } from '../settings';
import { SchemaForm } from './SchemaForm';

const ENGINE_LABELS: Record<Settings['engine'], string> = {
  whisper: 'whisper — local, free',
  openai: 'openai — cloud (needs key)',
};

function adjust(config: FormFieldConfig, value: Settings): FormFieldConfig {
  if (config.name === 'model') return { ...config, disabled: value.engine !== 'whisper' };
  if (config.name === 'engine') {
    return {
      ...config,
      options: config.options?.map((o) => ({ ...o, label: ENGINE_LABELS[o.value as Settings['engine']] ?? o.label })),
    };
  }
  if (config.name === 'apiBase') return { ...config, placeholder: '(same origin — leave blank)' };
  return config;
}

interface Props {
  settings: Settings;
  onChange: (s: Settings) => void;
  onClose: () => void;
}

export function SettingsPanel({ settings, onChange, onClose }: Props) {
  const [s, setS] = useState<Settings>(settings);

  const close = () => {
    void saveSettings(s);
    onChange(s);
    onClose();
  };

  return (
    <div className="palette-backdrop" onClick={close}>
      <div className="settings" onClick={(e) => e.stopPropagation()}>
        <h2>Settings</h2>
        <p className="muted">Defaults are the cheapest options — local, on-device, no API calls.</p>
        <SchemaForm collection={settingsCollection} value={s} onChange={setS} adjust={adjust} />
        <div className="settings-actions">
          <button onClick={close}>Done</button>
        </div>
      </div>
    </div>
  );
}
