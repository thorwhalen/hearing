// The always-on-top copilot overlay, with no native shell.
//
// Chrome and Edge (116+) have the Document Picture-in-Picture API: a small
// window that stays above every other window, including the meeting app, and
// that this page can fill with its own React components. `useOverlay()` opens
// one; `<Overlay>` renders its children into it through a React portal, so the
// overlay shows the same live state as the page (no second app, no syncing).
//
// Where the API is missing (Firefox, Safari), the overlay opens as an ordinary
// popup window instead: it shows the same content but cannot stay on top.
// `alwaysOnTop` says which one the browser gives.
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

// The size the overlay opens at (the reader can resize it).
export const OVERLAY_SIZE = { width: 380, height: 520 };

// The Document Picture-in-Picture API, as far as this file uses it (not yet in TypeScript's DOM types).
interface DocumentPictureInPicture {
  requestWindow(options: { width: number; height: number }): Promise<Window>;
}

function pipApi(): DocumentPictureInPicture | null {
  const api = (globalThis as { documentPictureInPicture?: DocumentPictureInPicture }).documentPictureInPicture;
  return api ?? null;
}

export function supportsAlwaysOnTop(): boolean {
  return pipApi() !== null;
}

// Give the new window the page's styles: the <style> tags Vite injects in
// development and the <link rel=stylesheet> of a build.
export function copyStyles(from: Document, to: Document): void {
  for (const node of Array.from(from.head.querySelectorAll('style, link[rel="stylesheet"]'))) {
    to.head.append(node.cloneNode(true));
  }
  to.body.className = 'overlay-body';
}

export async function openOverlayWindow(size = OVERLAY_SIZE): Promise<Window | null> {
  const api = pipApi();
  const win = api
    ? await api.requestWindow(size)
    : window.open('', 'hearing-copilot', `popup,width=${size.width},height=${size.height}`);
  if (!win) return null; // a blocked popup
  win.document.title = 'hearing — copilot';
  copyStyles(document, win.document);
  return win;
}

export function useOverlay() {
  const [win, setWin] = useState<Window | null>(null);
  const [error, setError] = useState<string | null>(null);

  const open = useCallback(async () => {
    if (win && !win.closed) {
      win.focus();
      return;
    }
    try {
      const next = await openOverlayWindow();
      if (!next) setError('The browser blocked the overlay window. Allow pop-ups for this page.');
      setWin(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); // e.g. not opened from a click
    }
  }, [win]);

  const close = useCallback(() => {
    win?.close();
    setWin(null);
  }, [win]);

  useEffect(() => {
    if (!win) return;
    const gone = () => setWin(null); // the reader closed the window
    win.addEventListener('pagehide', gone);
    return () => win.removeEventListener('pagehide', gone);
  }, [win]);

  return { window: win, open, close, error, alwaysOnTop: supportsAlwaysOnTop() };
}

export function Overlay({ window: win, children }: { window: Window | null; children: ReactNode }) {
  if (!win || win.closed) return null;
  return createPortal(children, win.document.body);
}
