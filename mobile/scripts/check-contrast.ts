// Fails (exit 1) if any text colour drops below 7:1 contrast (WCAG AAA) on the app backgrounds.
// Run: pnpm test   (Node 22.18+ runs TypeScript directly)
import { backgrounds, foregrounds, palette } from '../src/theme/colors.ts';

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Sanity: black on white is 21:1.
if (Math.abs(contrast('#000000', '#FFFFFF') - 21) > 0.01) throw new Error('contrast formula broken');

const pairs: [string, string, string, string][] = [
  ...foregrounds.flatMap((fg) =>
    backgrounds.map((bg): [string, string, string, string] => [fg, bg, palette[fg], palette[bg]]),
  ),
  ['onPrimary', 'primary', palette.onPrimary, palette.primary],
  ['onPrimary', 'ok', palette.onPrimary, palette.ok],
  ['onPrimary', 'danger', palette.onPrimary, palette.danger],
];

let failed = false;
// Card edges are boundaries, not text: WCAG 1.4.11 asks 3:1 against what they sit on.
for (const bg of ['bg', 'page'] as const) {
  const ratio = contrast(palette.line, palette[bg]);
  failed ||= ratio < 3;
  console.log(`${ratio >= 3 ? 'PASS' : 'FAIL'}  line on ${bg}: ${ratio.toFixed(2)}:1 (3:1 for edges)`);
}
for (const [fgName, bgName, fg, bg] of pairs) {
  const ratio = contrast(fg, bg);
  const pass = ratio >= 7;
  failed ||= !pass;
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${fgName} on ${bgName}: ${ratio.toFixed(2)}:1`);
}
process.exit(failed ? 1 : 0);
