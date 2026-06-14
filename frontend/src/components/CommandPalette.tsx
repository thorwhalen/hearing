// A ⌘K command palette. Reads the command registry (one definition per
// operation) and runs the selected command. The same Command objects also
// project to AI/MCP tools (commands.toAITools) — define once, use everywhere.
import { useEffect, useMemo, useRef, useState } from 'react';
import { type Command, type CommandContext, paletteEntries } from '../commands';

interface Props {
  commands: Command[];
  ctx: CommandContext;
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ commands, ctx, open, onClose }: Props) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const entries = useMemo(() => paletteEntries(commands), [commands]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? entries.filter((e) => e.label.toLowerCase().includes(q)) : entries;
  }, [entries, query]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActive(0);
      inputRef.current?.focus();
    }
  }, [open]);

  if (!open) return null;

  const run = (i: number) => {
    const entry = filtered[i];
    if (!entry) return;
    entry.command.run(entry.args, ctx);
    onClose();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
    else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      run(active);
    }
  };

  return (
    <div className="palette-backdrop" onClick={onClose}>
      <div className="palette" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="palette-input"
          placeholder="Type a command…  (Esc to close)"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
        />
        <ul className="palette-list">
          {filtered.map((e, i) => (
            <li
              key={e.id}
              className={i === active ? 'active' : ''}
              onMouseEnter={() => setActive(i)}
              onClick={() => run(i)}
            >
              {e.label}
            </li>
          ))}
          {filtered.length === 0 && <li className="empty">no matching command</li>}
        </ul>
      </div>
    </div>
  );
}
