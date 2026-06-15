// The in-app manual: renders the project's MANUAL.md (the same file in the repo)
// to HTML with `marked`. Single source of truth — the markdown is imported raw
// at build time from misc/docs/MANUAL.md.
import { marked } from 'marked';

interface Props {
  markdown: string;
  onClose: () => void;
}

export function ManualView({ markdown, onClose }: Props) {
  const html = marked.parse(markdown, { async: false }) as string;
  return (
    <div className="palette-backdrop" onClick={onClose}>
      <div className="manual" onClick={(e) => e.stopPropagation()}>
        <div className="manual-bar">
          <strong>Manual</strong>
          <button onClick={onClose}>✕</button>
        </div>
        {/* trusted local content (our own repo doc) */}
        <div className="manual-body" dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </div>
  );
}
