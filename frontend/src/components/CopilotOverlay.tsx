// What the always-on-top overlay shows: the latest lines of the transcript and
// the copilot's feedback, from the same state the main page draws.
import { clock } from '../api';
import { type Feedback, type Segment } from '../schema';
import { FeedbackPanel } from './FeedbackPanel';

// How many of the latest transcript lines the overlay keeps in view.
export const OVERLAY_LINES = 4;

interface Props {
  segments: Segment[];
  feedback: Feedback[];
  recording: boolean;
}

export function CopilotOverlay({ segments, feedback, recording }: Props) {
  const latest = segments.slice(-OVERLAY_LINES);
  return (
    <div className="overlay">
      <p className={`status${recording ? ' recording' : ''}`}>{recording ? '● recording' : 'not recording'}</p>
      <ol className="overlay-lines">
        {latest.map((s) => (
          <li key={s.id} className={`side-${s.side}`}>
            <span className="muted small">{clock(s.startMs)} {s.speaker}</span> {s.text}
          </li>
        ))}
      </ol>
      <FeedbackPanel items={feedback} />
    </div>
  );
}
