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