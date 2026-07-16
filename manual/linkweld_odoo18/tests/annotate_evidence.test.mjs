import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import jpeg from 'jpeg-js';
import { PNG } from 'pngjs';

import { annotateEvidence, annotateManifest } from '../scripts/annotate_evidence.mjs';

const sha256 = (buffer) => createHash('sha256').update(buffer).digest('hex');

test('creates numbered callouts without modifying the original screenshot', async () => {
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
    callouts: [{ x: 60, y: 40, radius: 20, label: 1 }],
  });

  const originalAfter = await readFile(inputPath);
  const output = await readFile(outputPath);
  const annotated = PNG.sync.read(output);
  const pixelOffset = ((18 * annotated.width) + 60) * 4;

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
    callouts: [{ x: 60, y: 40, radius: 20, label: 2 }],
  });

  const originalAfter = await readFile(inputPath);
  const annotated = PNG.sync.read(await readFile(outputPath));
  const pixelOffset = ((18 * annotated.width) + 60) * 4;

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
        callouts: [{ x: 60, y: 40, radius: 20, label: 1 }],
      }],
    }),
  );

  const rendered = await annotateManifest({ manifestPath, ids: ['SHOT-01'] });

  assert.deepEqual(rendered, [outputPath]);
  assert.equal(PNG.sync.read(await readFile(outputPath)).width, 120);
});
