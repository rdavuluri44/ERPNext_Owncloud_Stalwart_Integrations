// Fails (exit 1) if screen code or texts use emoji or text symbols as icons (owner's design brief: outlined
// vector icons only). Run: pnpm test
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

// Emoji, pictographs, dingbats, check marks, ballot boxes, arrows used as icons, and their \u escapes in code.
const SYMBOLS = /[←-⇿⌀-⏿■-➿⤀-⥿⬀-⯿\u{1F000}-\u{1FAFF}]|\\u(2[13][0-9A-F]{2}|2[5-7][0-9A-F]{2}|2B[0-9A-F]{2})|\\u\{1F/u;

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === '__tests__' ? [] : files(path);
    return /\.(tsx?|json)$/.test(name) ? [path] : [];
  });
}

const found = files('src').flatMap((path) =>
  readFileSync(path, 'utf8')
    .split('\n')
    .map((line, i) => ({ path, line: i + 1, text: line.trim() }))
    .filter(({ text }) => SYMBOLS.test(text)),
);
for (const f of found) console.log(`SYMBOL  ${f.path}:${f.line}  ${f.text.slice(0, 100)}`);
console.log(found.length ? `${found.length} symbol(s) used as icons: use <Icon> instead` : 'no emoji or symbol icons');
process.exit(found.length ? 1 : 0);
