// The transcript viewer: me/them lanes (like a chat), ordered by time.
//
// Schema-driven: which fields we search is read off the zodal collection
// (`segments.getSearchableFields()`), not hand-coded. The me/them two-lane
// layout is a thin presentation choice on top of the schema's `side` field.
import { useMemo } from 'react';
import { clock } from '../api';
import { segments as segmentsCollection, type Segment } from '../schema';

interface Props {
  segments: Segment[];
  query: string;
}

export function TranscriptView({ segments, query }: Props) {
  // Search across exactly the fields zodal inferred as searchable (text, speaker).
  const searchable = useMemo(() => segmentsCollection.getSearchableFields(), []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const ordered = [...segments].sort((a, b) => a.startMs - b.startMs);
    if (!q) return ordered;
    return ordered.filter((s) =>
      searchable.some((f) => String((s as Record<string, unknown>)[f] ?? '').toLowerCase().includes(q)),
    );
  }, [segments, query, searchable]);

  if (segments.length === 0) {
    return <p className="empty">No transcript yet — upload an audio file above.</p>;
  }

  return (
    <div className="transcript">
      {visible.map((s) => (
        <div
          key={s.id}
          className={`bubble ${s.side}${s.isFinal ? '' : ' partial'}`}
          title={`${s.speaker} · ${s.channel} · ${clock(s.startMs)}–${clock(s.endMs)}`}
        >
          <div className="bubble-meta">
            <span className="speaker">{s.speaker}</span>
            <span className="time">{clock(s.startMs)}</span>
          </div>
          <div className="bubble-text">{s.text}</div>
        </div>
      ))}
      {visible.length === 0 && <p className="empty">No segments match “{query}”.</p>}
    </div>
  );
}
