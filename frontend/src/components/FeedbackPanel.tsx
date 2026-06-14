// The live AI-copilot panel: the agent's per-segment feedback, newest first.
// Each item is a Feedback from the shared schema; `kind` drives the badge.
import { clock } from '../api';
import { type Feedback } from '../schema';

const KIND_LABEL: Record<Feedback['kind'], string> = {
  note: 'Note',
  suggested_question: 'Question',
  surfaced_doc: 'Doc',
  fact_check: 'Fact-check',
};

interface Props {
  items: Feedback[];
}

export function FeedbackPanel({ items }: Props) {
  return (
    <aside className="summary">
      <h2>Copilot {items.length > 0 && <span className="count">({items.length})</span>}</h2>
      {items.length === 0 && <p className="empty">Live feedback will appear here as people speak.</p>}
      {[...items].reverse().map((f) => (
        <div key={f.id} className={`fb fb-${f.kind}`}>
          <div className="fb-meta">
            <span className={`badge badge-${f.kind}`}>{KIND_LABEL[f.kind]}</span>
            <span className="time">{clock(f.atMs)}</span>
          </div>
          <div className="fb-body">{f.body}</div>
          {f.sourceUrl && (
            <a className="fb-src" href={f.sourceUrl} target="_blank" rel="noreferrer">
              source
            </a>
          )}
        </div>
      ))}
    </aside>
  );
}
