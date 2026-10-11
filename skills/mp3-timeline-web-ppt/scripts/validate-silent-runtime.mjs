import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('usage: node validate-silent-runtime.mjs <presentation-src>');
  process.exit(2);
}

const extensions = new Set(['.ts', '.tsx', '.js', '.jsx', '.html', '.css']);
const files = [];

function walk(folder) {
  for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === 'dist') continue;
    const target = path.join(folder, entry.name);
    if (entry.isDirectory()) walk(target);
    else if (extensions.has(path.extname(entry.name))) files.push(target);
  }
}

walk(path.resolve(root));
const source = files.map((file) => `\n/* ${file} */\n${fs.readFileSync(file, 'utf8')}`).join('');
const forbidden = [
  ['caption query parameter', /[?&]captions?=/i],
  ['HTML text track', /<track\b/i],
  ['caption or subtitle UI', /(className|class)\s*=\s*["'`][^"'`]*(caption|subtitle)|data-(caption|subtitle)/i],
  ['M audio shortcut', /KeyM/],
  ['mutable muted state', /setMuted\s*\(|\.muted\s*=\s*(false|!)/],
  ['positive runtime volume', /\.volume\s*=\s*(?:0?\.[0-9]*[1-9][0-9]*|[1-9][0-9]*(?:\.[0-9]+)?)/],
  ['audible control copy', /有声|取消静音|打开声音|unmute|sound on/i],
];

const failures = forbidden.filter(([, pattern]) => pattern.test(source)).map(([label]) => label);
if (!/data-ppt-clock/.test(source)) failures.push('missing data-ppt-clock audio hook');
if (!/\bmuted\b/.test(source)) failures.push('missing muted audio declaration');
if (!/\.volume\s*=\s*0\b/.test(source)) failures.push('missing hard volume 0 assignment');

if (failures.length) {
  console.error(`FAIL silent runtime contract:\n${failures.map((item) => `- ${item}`).join('\n')}`);
  process.exit(1);
}

console.log(`PASS silent runtime contract files=${files.length}`);
