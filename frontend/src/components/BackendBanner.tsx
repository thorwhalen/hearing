// Shown when the hearing backend can't be reached. The app is useless without it
// (no transcription), so we say so loudly ON LANDING — not after a wasted
// recording — with exact run instructions.
interface Props {
  url: string;
  onRecheck: () => void;
  onHelp: () => void;
}

export function BackendBanner({ url, onRecheck, onHelp }: Props) {
  return (
    <div className="banner" role="alert">
      <div className="banner-title">⚠ No hearing backend found at {url || 'this page'}</div>
      <div>
        Recording and transcription need the backend running on <b>your machine</b>. The
        compute (speech-to-text, AI) runs locally — this page only sends it audio.
      </div>
      <div className="banner-how">
        In a terminal, run: <code>hearing serve</code>
        {'  '}(first time: <code>pip install 'hearing[whisper,http]'</code>). Then{' '}
        <button onClick={onRecheck}>Recheck</button> or <button onClick={onHelp}>open Help</button>.
      </div>
    </div>
  );
}
