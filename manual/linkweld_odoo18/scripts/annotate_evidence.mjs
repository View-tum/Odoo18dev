import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

import jpeg from 'jpeg-js';
import { PNG } from 'pngjs';

const RED = [217, 48, 37, 255];
const WHITE = [255, 255, 255, 255];

const DIGITS = {
  '0': ['111', '101', '101', '101', '111'],
  '1': ['010', '110', '010', '010', '111'],
  '2': ['111', '001', '111', '100', '111'],
  '3': ['111', '001', '111', '001', '111'],
  '4': ['101', '101', '111', '001', '001'],
  '5': ['111', '100', '111', '001', '111'],
  '6': ['111', '100', '111', '101', '111'],
  '7': ['111', '001', '010', '010', '010'],
  '8': ['111', '101', '111', '101', '111'],
  '9': ['111', '101', '111', '001', '111'],
};

const setPixel = (png, x, y, color) => {
  if (x < 0 || y < 0 || x >= png.width || y >= png.height) return;
  const offset = ((Math.trunc(y) * png.width) + Math.trunc(x)) * 4;
  png.data[offset] = color[0];
  png.data[offset + 1] = color[1];
  png.data[offset + 2] = color[2];
  png.data[offset + 3] = color[3];
};

const drawCircle = (png, cx, cy, radius, thickness, color) => {
  const outer = radius + (thickness / 2);
  const inner = radius - (thickness / 2);

  for (let y = Math.floor(cy - outer); y <= Math.ceil(cy + outer); y += 1) {
    for (let x = Math.floor(cx - outer); x <= Math.ceil(cx + outer); x += 1) {
      const distance = Math.hypot(x - cx, y - cy);
      if (distance >= inner && distance <= outer) setPixel(png, x, y, color);
    }
  }
};

const drawFilledCircle = (png, cx, cy, radius, color) => {
  for (let y = cy - radius; y <= cy + radius; y += 1) {
    for (let x = cx - radius; x <= cx + radius; x += 1) {
      if (Math.hypot(x - cx, y - cy) <= radius) setPixel(png, x, y, color);
    }
  }
};

const drawLabel = (png, cx, cy, value) => {
  const text = String(value);
  const scale = 2;
  const glyphWidth = 3 * scale;
  const gap = scale;
  const width = (text.length * glyphWidth) + ((text.length - 1) * gap);
  const startX = Math.round(cx - (width / 2));
  const startY = Math.round(cy - (5 * scale / 2));

  [...text].forEach((digit, index) => {
    const glyph = DIGITS[digit];
    if (!glyph) return;
    glyph.forEach((row, rowIndex) => {
      [...row].forEach((bit, columnIndex) => {
        if (bit !== '1') return;
        for (let dy = 0; dy < scale; dy += 1) {
          for (let dx = 0; dx < scale; dx += 1) {
            setPixel(
              png,
              startX + (index * (glyphWidth + gap)) + (columnIndex * scale) + dx,
              startY + (rowIndex * scale) + dy,
              WHITE,
            );
          }
        }
      });
    });
  });
};

export async function annotateEvidence({ inputPath, outputPath, callouts }) {
  const original = await readFile(inputPath);
  let png;

  if (original[0] === 0xff && original[1] === 0xd8) {
    const decoded = jpeg.decode(original, { formatAsRGBA: true, useTArray: true });
    png = new PNG({ width: decoded.width, height: decoded.height });
    png.data.set(decoded.data);
  } else {
    png = PNG.sync.read(original);
  }

  callouts.forEach(({ x, y, radius, label }) => {
    drawCircle(png, x, y, radius, 5, RED);
    const badgeX = Math.round(x - radius + 10);
    const badgeY = Math.round(y - radius + 10);
    drawFilledCircle(png, badgeX, badgeY, 15, WHITE);
    drawFilledCircle(png, badgeX, badgeY, 12, RED);
    drawLabel(png, badgeX, badgeY, label);
  });

  await writeFile(outputPath, PNG.sync.write(png));
}

export async function annotateManifest({ manifestPath, ids = [] }) {
  const absoluteManifestPath = resolve(manifestPath);
  const baseDirectory = dirname(absoluteManifestPath);
  const manifest = JSON.parse(await readFile(absoluteManifestPath, 'utf8'));
  const selected = ids.length > 0
    ? manifest.screenshots.filter(({ id }) => ids.includes(id))
    : manifest.screenshots;
  const outputPaths = [];

  for (const screenshot of selected) {
    const outputPath = resolve(baseDirectory, screenshot.output);
    await annotateEvidence({
      inputPath: resolve(baseDirectory, screenshot.input),
      outputPath,
      callouts: screenshot.callouts,
    });
    outputPaths.push(outputPath);
  }

  return outputPaths;
}

const scriptPath = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href : '';
if (import.meta.url === scriptPath) {
  const [manifestPath, ...ids] = process.argv.slice(2);
  if (!manifestPath) throw new Error('Usage: node annotate_evidence.mjs <manifest.json> [screenshot-id ...]');
  const outputPaths = await annotateManifest({ manifestPath, ids });
  outputPaths.forEach((outputPath) => console.log(outputPath));
}
