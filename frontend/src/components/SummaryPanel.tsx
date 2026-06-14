// Renders the AI meeting notes (the agent's batch output). The backend returns
// lightly-structured markdown-ish text; we render headings (## ...) and bullets
// without pulling in a full markdown library — enough for a clean read.

interface Props {
  summary?: string;
}

export function SummaryPanel({ summary }: Props) {
  if (!summary) return null;
  const lines = summary.split('\n');
  return (
    <aside className="summary">
      <h2>AI notes</h2>
      {lines.map((line, i) => {
        if (line.startsWith('## ')) return <h3 key={i}>{line.slice(3)}</h3>;
        if (line.startsWith('- ')) return <li key={i}>{line.slice(2)}</li>;
        if (line.trim() === '') return <br key={i} />;
        return <p key={i}>{line}</p>;
      })}
    </aside>
  );
}
