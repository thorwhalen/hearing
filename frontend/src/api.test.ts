import { afterEach, describe, expect, it } from 'vitest';
import { resolveApiBase } from './api';

function setLocation(hostname?: string) {
  if (hostname === undefined) {
    delete (globalThis as unknown as { location?: unknown }).location;
  } else {
    (globalThis as unknown as { location: unknown }).location = {
      hostname,
      origin: `https://${hostname}`,
    };
  }
}

afterEach(() => setLocation(undefined));

describe('resolveApiBase', () => {
  it('an explicit setting always wins', () => {
    setLocation('thorwhalen.com');
    expect(resolveApiBase('http://host:9000')).toBe('http://host:9000');
  });

  it('localhost origin -> same origin (blank)', () => {
    setLocation('localhost');
    expect(resolveApiBase('')).toBe('');
  });

  it('remote host -> local backend (compute is local)', () => {
    setLocation('thorwhalen.com');
    expect(resolveApiBase('')).toBe('http://localhost:8000');
  });

  it('no location -> same origin', () => {
    setLocation(undefined);
    expect(resolveApiBase()).toBe('');
  });
});
