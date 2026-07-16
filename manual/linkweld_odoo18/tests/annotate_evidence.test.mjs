import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import jpeg from 'jpeg-js';
import { PNG } from 'pngjs';

import { annotateEvidence, annotateManifest } from '../scripts/annotate_evidence.mjs';

const sha256 = (buffer) => createHash('sha256').update(buffer).digest('hex');
const isRed = (png, x, y) => {
  const offset = ((y * png.width) + x) * 4;
  return png.data[offset] > 180
    && png.data[offset + 1] < 100
    && png.data[offset + 2] < 100;
};

const rectangleBorderRatio = (png, callout) => {
  const pixels = [];
  for (let x = callout.x; x < callout.x + callout.width; x += 1) {
    pixels.push([x, callout.y], [x, callout.y + callout.height - 1]);
  }
  for (let y = callout.y; y < callout.y + callout.height; y += 1) {
    pixels.push([callout.x, y], [callout.x + callout.width - 1, y]);
  }
  return pixels.filter(([x, y]) => isRed(png, x, y)).length / pixels.length;
};

test('creates numbered rectangular callouts without modifying the original screenshot', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'linkweld-annotation-'));
  const inputPath = join(directory, 'original.png');
  const outputPath = join(directory, 'annotated.png');

  const source = new PNG({ width: 120, height: 80 });
  source.data.fill(255);
  await writeFile(inputPath, PNG.sync.write(source));

  const originalBefore = await readFile(inputPath);

  await annotateEvidence({
    inputPath,
    outputPath,
    callouts: [{ shape: 'rectangle', x: 40, y: 20, width: 40, height: 40, label: 1 }],
  });

  const originalAfter = await readFile(inputPath);
  const output = await readFile(outputPath);
  const annotated = PNG.sync.read(output);
  const pixelOffset = ((20 * annotated.width) + 60) * 4;

  assert.equal(sha256(originalAfter), sha256(originalBefore));
  assert.equal(annotated.width, 120);
  assert.equal(annotated.height, 80);
  assert.ok(output.length > originalBefore.length);
  assert.ok(
    annotated.data[pixelOffset] > 180
      && annotated.data[pixelOffset + 1] < 100
      && annotated.data[pixelOffset + 2] < 100,
  );
});

test('accepts a JPEG screenshot and writes a pixel-faithful annotated PNG', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'linkweld-jpeg-annotation-'));
  const inputPath = join(directory, 'original.jpg');
  const outputPath = join(directory, 'annotated.png');
  const rgba = Buffer.alloc(120 * 80 * 4, 255);
  await writeFile(inputPath, jpeg.encode({ data: rgba, width: 120, height: 80 }, 90).data);
  const originalBefore = await readFile(inputPath);

  await annotateEvidence({
    inputPath,
    outputPath,
    callouts: [{ shape: 'rectangle', x: 40, y: 20, width: 40, height: 40, label: 2 }],
  });

  const originalAfter = await readFile(inputPath);
  const annotated = PNG.sync.read(await readFile(outputPath));
  const pixelOffset = ((20 * annotated.width) + 60) * 4;

  assert.equal(sha256(originalAfter), sha256(originalBefore));
  assert.equal(annotated.width, 120);
  assert.equal(annotated.height, 80);
  assert.ok(
    annotated.data[pixelOffset] > 180
      && annotated.data[pixelOffset + 1] < 100
      && annotated.data[pixelOffset + 2] < 100,
  );
});

test('renders selected screenshots from a relative-path annotation manifest', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'linkweld-manifest-'));
  const inputPath = join(directory, 'original.png');
  const outputPath = join(directory, 'annotated.png');
  const manifestPath = join(directory, 'manifest.json');
  const source = new PNG({ width: 120, height: 80 });
  source.data.fill(255);
  await writeFile(inputPath, PNG.sync.write(source));
  await writeFile(
    manifestPath,
    JSON.stringify({
      screenshots: [{
        id: 'SHOT-01',
        input: 'original.png',
        output: 'annotated.png',
        callouts: [{ shape: 'rectangle', x: 40, y: 20, width: 40, height: 40, label: 1 }],
      }],
    }),
  );

  const rendered = await annotateManifest({ manifestPath, ids: ['SHOT-01'] });

  assert.deepEqual(rendered, [outputPath]);
  assert.equal(PNG.sync.read(await readFile(outputPath)).width, 120);
});

test('rejects a rectangular callout outside the screenshot bounds', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'linkweld-out-of-bounds-'));
  const inputPath = join(directory, 'original.png');
  const outputPath = join(directory, 'annotated.png');
  const source = new PNG({ width: 120, height: 80 });
  source.data.fill(255);
  await writeFile(inputPath, PNG.sync.write(source));

  await assert.rejects(
    annotateEvidence({
      inputPath,
      outputPath,
      callouts: [{ shape: 'rectangle', x: 100, y: 20, width: 30, height: 30, label: 1 }],
    }),
    /inside the screenshot bounds/,
  );
});

test('keeps every project rectangle in bounds with complete visible borders', async () => {
  const manualRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const manifestPath = resolve(manualRoot, 'register', 'annotation_manifest.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const errors = [];

  for (const screenshot of manifest.screenshots) {
    const inputBuffer = await readFile(resolve(dirname(manifestPath), screenshot.input));
    const input = inputBuffer[0] === 0xff && inputBuffer[1] === 0xd8
      ? jpeg.decode(inputBuffer, { formatAsRGBA: true, useTArray: true })
      : PNG.sync.read(inputBuffer);
    const output = PNG.sync.read(await readFile(resolve(dirname(manifestPath), screenshot.output)));

    if (input.width !== output.width || input.height !== output.height) {
      errors.push(`${screenshot.id}: input/output dimensions differ`);
      continue;
    }

    screenshot.callouts.forEach((callout) => {
      const inBounds = callout.x >= 0
        && callout.y >= 0
        && callout.x + callout.width <= output.width
        && callout.y + callout.height <= output.height;
      if (!inBounds) {
        errors.push(`${screenshot.id} box ${callout.label}: outside screenshot bounds`);
        return;
      }
      const ratio = rectangleBorderRatio(output, callout);
      if (ratio < 0.8) {
        errors.push(`${screenshot.id} box ${callout.label}: red border ratio ${ratio.toFixed(3)}`);
      }
    });
  }

  assert.deepEqual(errors, []);
});
