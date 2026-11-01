/** Runs `fn` on the next tick and returns the cancel function (the repo's idiom for effects that start loading data). */
export function runSoon(fn: () => void): () => void {
  const timer = window.setTimeout(fn, 0);
  return () => window.clearTimeout(timer);
}
