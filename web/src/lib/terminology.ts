/** Port of frontend/terminology.js. Apply only to generated labels, never to source evidence. */
export function translator(terms: Record<string, string>) {
  // Longest phrases win; ASCII boundaries allow Korean particles (Claim이).
  const keys = Object.keys(terms).sort((a, b) => b.length - a.length);
  if (!keys.length) return (value: string) => value;
  const escape = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(
    keys
      .map(
        (key) =>
          (/^[A-Za-z]/.test(key) ? "(?<![A-Za-z])" : "") +
          escape(key) +
          (/[A-Za-z]$/.test(key) ? "(?![A-Za-z])" : ""),
      )
      .join("|"),
    "g",
  );
  return (value: string) => value.replace(pattern, (match) => terms[match]);
}
