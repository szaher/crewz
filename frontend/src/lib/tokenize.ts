// Lightweight token count estimator for LLM prompts
// Heuristic: ~1 token per 4 characters of word content, plus a small
// overhead for punctuation/symbols. This is an approximation meant for UI.

export function estimateTokens(text: string): number {
  if (!text) return 0;

  // Split on whitespace to get word-ish chunks
  const words = text.trim().length > 0 ? text.trim().split(/\s+/) : [];
  let count = 0;

  for (const w of words) {
    // Approx 1 token per 4 chars for word content
    const wordLen = w.replace(/[^A-Za-z0-9_]/g, '').length;
    if (wordLen > 0) count += Math.ceil(wordLen / 4);
  }

  // Add overhead for punctuation/symbols (including braces)
  const symbols = (text.match(/[^\w\s]/g) || []).length;
  count += Math.ceil(symbols * 0.5);

  return count;
}

