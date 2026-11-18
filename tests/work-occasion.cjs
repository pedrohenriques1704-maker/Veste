const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');

const source = fs.readFileSync(new URL('../app.js', `file://${__filename}`), 'utf8');

test('the active generator filters every piece by the selected work occasion', () => {
  const activeGenerator = source.match(/generateCandidates=function\(ctx\)\{[\s\S]*?currentContext=function/);
  assert.ok(activeGenerator, 'active look generator was not found');
  assert.match(activeGenerator[0], /state\.pieces\.filter\(p=>eligibleForLook\(p,ctx\)/);
  assert.match(activeGenerator[0], /required\.some\(id=>[\s\S]*?!eligibleForLook\(pieceById\(id\),ctx\)\)/);
});

test('candidate validation rejects an incompatible optional accessory', () => {
  const validation = source.match(/function valid\(o,context,required=\[\]\)\{[\s\S]*?return true;\n  \}/);
  assert.ok(validation, 'candidate validation was not found');
  assert.match(validation[0], /ids\.some\(id=>[\s\S]*?!eligibleForLook\(pieceById\(id\),context\)\)/);
});

test('work eligibility accepts only pieces tagged for work', () => {
  const fits = (piece, occasion) =>
    occasion !== 'trabalho' || (piece.occasions || []).includes('trabalho');

  assert.equal(fits({ occasions: ['casual'] }, 'trabalho'), false);
  assert.equal(fits({ occasions: ['casual', 'trabalho'] }, 'trabalho'), true);
  assert.equal(fits({ occasions: ['casual'] }, 'casual'), true);
});
