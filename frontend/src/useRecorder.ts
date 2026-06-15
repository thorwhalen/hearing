// A tiny microphone-recording hook (browser MediaRecorder).
//
// Frontend-novice note: the browser can only record the MICROPHONE — it cannot
// capture the other participants' audio (system audio). So this gives a
// "me"-only recording. For the full me/them capture, use the native path
// (BlackHole + the CLI) — see the manual.
import { useCallback, useRef, useState } from 'react';

export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not access the microphone.');
    }
  }, []);

  // Stop and resolve the recorded audio as a File (or null if nothing recorded).
  const stop = useCallback((): Promise<File | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder) {
        resolve(null);
        return;
      }
      recorder.onstop = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const type = recorder.mimeType || 'audio/webm';
        if (chunksRef.current.length === 0) {
          resolve(null);
          return;
        }
        const ext = type.includes('ogg') ? 'ogg' : 'webm';
        resolve(new File(chunksRef.current, `recording.${ext}`, { type }));
      };
      recorder.stop();
    });
  }, []);

  return { recording, error, start, stop };
}
