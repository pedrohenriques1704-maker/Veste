const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');

const source = fs.readFileSync(new URL('../app.js', `file://${__filename}`), 'utf8');

function choose(candidates, rotationWeights = {}, limit = 3) {
  const chosen = [];
  const used = new Set();
  const chosenPieceUse = new Map();
  const priority = candidate =>
    candidate.score - candidate.ids.reduce((sum, id) => sum + (rotationWeights[id] || 0), 0);

  while (chosen.length < limit) {
    let best = null;
    let bestScore = -Infinity;
    for (const candidate of candidates) {
      if (used.has(candidate.key)) continue;
      const maxOverlap = chosen.reduce((max, previous) => Math.max(
        max,
        candidate.ids.filter(id => previous.ids.includes(id)).length /
          Math.max(previous.ids.length, candidate.ids.length, 1)
      ), 0);
      const repeats = candidate.ids.reduce((sum, id) => sum + (chosenPieceUse.get(id) || 0), 0);
      const value = priority(candidate) - 32 * maxOverlap - 16 * repeats;
      if (value > bestScore) {
        bestScore = value;
        best = candidate;
      }
    }
    if (!best) break;
    chosen.push(best);
    used.add(best.key);
    for (const id of best.ids) chosenPieceUse.set(id, (chosenPieceUse.get(id) || 0) + 1);
  }
  return chosen;
}

const candidates = [
  { key: 'a1', ids: ['top-1', 'bottom-1', 'shoe-1'], score: 100 },
  { key: 'a2', ids: ['top-1', 'bottom-2', 'shoe-1'], score: 99 },
  { key: 'a3', ids: ['top-1', 'bottom-3', 'shoe-1'], score: 98 },
  { key: 'b1', ids: ['top-2', 'bottom-4', 'shoe-2'], score: 94 },
  { key: 'c1', ids: ['top-3', 'bottom-5', 'shoe-3'], score: 93 },
  { key: 'd1', ids: ['top-4', 'bottom-6', 'shoe-4'], score: 92 }
];

test('a result round does not fill all cards with the highest-ranked pieces', () => {
  const selected = choose(candidates);
  assert.equal(selected[0].key, 'a1');
  assert.deepEqual(selected.slice(1).map(item => item.key), ['b1', 'c1']);
});

test('recently suggested pieces lose priority on the next round', () => {
  const recent = Object.fromEntries(['top-1', 'bottom-1', 'shoe-1', 'top-2', 'bottom-4', 'shoe-2'].map(id => [id, 18]));
  const selected = choose(candidates, recent);
  assert.equal(selected[0].key, 'c1');
  assert.ok(selected.some(item => item.key === 'd1'));
});

test('the production generator uses rotation history and per-round piece usage', () => {
  const activeGenerator = source.match(/generateCandidates=function\(ctx\)\{[\s\S]*?currentContext=function/);
  assert.ok(activeGenerator, 'active look generator was not found');
  assert.match(activeGenerator[0], /rotationWeights/);
  assert.match(activeGenerator[0], /chosenPieceUse=new Map\(\)/);
  assert.match(activeGenerator[0], /repeatedPieces/);
  assert.match(source, /function rememberLookRotation\(context,candidates\)/);
});
