import test from 'node:test';
import assert from 'node:assert/strict';
import { vectorizeImageData } from '../vector-engine.js';

function image(width, height, pixelAt) {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      data.set(pixelAt(x, y), (y * width + x) * 4);
    }
  }
  return { width, height, data };
}

test('traces a solid raster region into real SVG path geometry', () => {
  const source = image(8, 8, (x, y) => (x >= 2 && x <= 5 && y >= 2 && y <= 5 ? [240, 30, 20, 255] : [0, 0, 0, 0]));
  const result = vectorizeImageData(source, { colors: 4, curve: 'polygon', minArea: 0 });
  assert.match(result.svg, /<path d="M /);
  assert.match(result.svg, /fill="#f/);
  assert.doesNotMatch(result.svg, /<image|data:image/);
  assert.equal(result.stats.width, 8);
  assert.equal(result.stats.height, 8);
  assert.equal(result.stats.paths, 1);
});

test('keeps disconnected regions as separate contours', () => {
  const source = image(9, 5, (x, y) => ((x === 1 || x === 7) && y === 2 ? [30, 180, 250, 255] : [0, 0, 0, 0]));
  const result = vectorizeImageData(source, { colors: 3, curve: 'polygon', minArea: 0 });
  assert.equal(result.stats.paths, 2);
});

test('does not create visible geometry from transparent pixels', () => {
  const source = image(4, 4, () => [255, 0, 0, 0]);
  const result = vectorizeImageData(source);
  assert.equal(result.stats.paths, 0);
  assert.doesNotMatch(result.svg, /<path/);
});

test('is deterministic for identical image data and settings', () => {
  const source = image(12, 9, (x, y) => ((x + y) % 3 ? [220, 70, 40, 255] : [30, 100, 230, 200]));
  const settings = { colors: 6, detail: 0.7, curve: 'smooth', alphaBins: 2 };
  const first = vectorizeImageData(source, settings);
  const second = vectorizeImageData(source, settings);
  assert.equal(first.svg, second.svg);
  assert.equal(first.stats.width, second.stats.width);
  assert.equal(first.stats.height, second.stats.height);
  assert.equal(first.stats.colorsUsed, second.stats.colorsUsed);
  assert.equal(first.stats.paths, second.stats.paths);
});

test('preserves holes with even-odd SVG path geometry', () => {
  const source = image(9, 9, (x, y) => (x >= 1 && x <= 7 && y >= 1 && y <= 7 && !(x >= 3 && x <= 5 && y >= 3 && y <= 5) ? [220, 220, 220, 255] : [0, 0, 0, 0]));
  const result = vectorizeImageData(source, { colors: 2, curve: 'polygon', minArea: 0 });
  assert.equal(result.stats.paths, 2);
  assert.match(result.svg, /fill-rule="evenodd"/);
});

test('separates regions that touch at one corner', () => {
  const source = image(4, 4, (x, y) => ((x === y && (x === 1 || x === 2)) ? [220, 80, 20, 255] : [0, 0, 0, 0]));
  const result = vectorizeImageData(source, { colors: 2, curve: 'polygon', minArea: 0 });
  assert.equal(result.stats.paths, 2);
});

test('keeps separate opacity bands for translucent regions', () => {
  const source = image(6, 4, (x, y) => (y < 2 ? [80, 160, 240, 255] : [80, 160, 240, 64]));
  const result = vectorizeImageData(source, { colors: 2, alphaBins: 2, minArea: 0, curve: 'polygon' });
  assert.equal(result.stats.colorsUsed, 1);
  assert.equal(result.stats.paths, 2);
  assert.match(result.svg, /fill-opacity="1\.00000"/);
  assert.match(result.svg, /fill-opacity="0\.25098"/);
});

test('removes isolated regions below the configured area threshold', () => {
  const source = image(9, 5, (x, y) => ((x >= 1 && x <= 3 && y >= 1 && y <= 3) || (x === 7 && y === 2) ? [190, 90, 30, 255] : [0, 0, 0, 0]));
  const result = vectorizeImageData(source, { colors: 2, minArea: 2, curve: 'polygon' });
  assert.equal(result.stats.paths, 1);
  assert.equal(result.stats.componentsRemoved, 1);
});

test('clamps browser settings to supported ranges', () => {
  const source = image(4, 4, (x, y) => (x === y ? [20, 80, 140, 255] : [0, 0, 0, 0]));
  const result = vectorizeImageData(source, {
    colors: 999,
    alphaBins: 99,
    detail: -10,
    minArea: -1,
    cornerAngle: 999,
    transparentThreshold: -20,
    curve: 'unknown',
  });
  assert.equal(result.stats.width, 4);
  assert.equal(result.stats.height, 4);
  assert.ok(result.stats.colorsUsed <= 64);
});


test('indexes multiple visible color classes without changing deterministic contours', () => {
  const source = image(20, 12, (x, y) => {
    if (x < 6) return [240, 30, 20, 255];
    if (x < 13) return [20, 180, 60, 255];
    if (y < 6) return [30, 80, 230, 255];
    return [0, 0, 0, 0];
  });
  const settings = { colors: 4, alphaBins: 1, curve: 'polygon', minArea: 0 };
  const first = vectorizeImageData(source, settings);
  const second = vectorizeImageData(source, settings);
  assert.equal(first.svg, second.svg);
  assert.equal(first.stats.paths, 3);
  assert.equal(first.stats.colorsUsed, 3);
});

test('rejects invalid ImageData dimensions and pixel-buffer lengths', () => {
  assert.throws(
    () => vectorizeImageData({ width: 0, height: 4, data: new Uint8ClampedArray(0) }),
    /positive integers/
  );
  assert.throws(
    () => vectorizeImageData({ width: 2, height: 2, data: new Uint8ClampedArray(15) }),
    /does not match/
  );
});

test('uses finite fallbacks for non-finite settings', () => {
  const source = image(5, 5, (x, y) => (x === y ? [220, 70, 40, 255] : [0, 0, 0, 0]));
  const result = vectorizeImageData(source, {
    colors: Number.NaN, detail: Number.POSITIVE_INFINITY, minArea: Number.NaN,
    cornerAngle: Number.NaN, alphaBins: Number.NaN, transparentThreshold: Number.NaN,
  });
  assert.match(result.svg, /<svg/);
  assert.doesNotMatch(result.svg, /NaN|Infinity/);
});
