// Berekent alle dash.calc-uitkomsten van het dashboard met de ruwe datasets.
// Gebruik: node tools/calc.js src/dashboard.html raw.json out.json
const fs = require('fs');
const [page, rawPath, outPath] = process.argv.slice(2);
const html = fs.readFileSync(page, 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const blocks = [];
for (const sc of scripts) { let i = 0; while ((i = sc.indexOf('dash.calc(', i)) >= 0) { let d = 0, j = i; for (; j < sc.length; j++) { const c = sc[j]; if (c === '(') d++; else if (c === ')') { d--; if (d === 0) break; } } blocks.push(sc.slice(i, j + 2)); i = j; } }
const head = scripts[scripts.length - 1].split('/* ---------------- Opmaak-hulpjes')[0];
const C = {}; const dash = { calc: (id, o) => C[id] = o };
eval(head);
for (const b of blocks) { const id = b.match(/dash\.calc\('([^']+)'/)[1]; if (!C[id]) { try { eval(b); } catch (e) { console.error('blockerr', id, e.message); } } }
const R = JSON.parse(fs.readFileSync(rawPath, 'utf8'));
let left = Object.keys(C), g = 0;
while (left.length && g++ < 60) { for (const id of [...left]) { if (C[id].inputs.every(i => R[i])) { try { R[id] = C[id].fn(...C[id].inputs.map(i => R[i])); } catch (e) { console.error('ERR', id, e.message); R[id] = []; } left = left.filter(x => x !== id); } } }
if (left.length) { console.error('missing', left); process.exit(1); }
fs.writeFileSync(outPath, JSON.stringify(R));
console.log('calcs', Object.keys(C).length, 'ok');
