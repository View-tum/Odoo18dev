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

const drawFilledRectangle = (png, x, y, width, height, color) => {
  for (let row = y; row < y + height; row += 1) {
    for (let column = x; column < x + width; column += 1) {
      setPixel(png, column, row, color);
    }
  }
};

const drawRectangle = (png, x, y, width, height, thickness, color) => {
  drawFilledRectangle(png, x, y, width, thickness, color);
  drawFilledRectangle(png, x, y + height - thickness, width, thickness, color);
  drawFilledRectangle(png, x, y, thickness, height, color);
  drawFilledRectangle(png, x + width - thickness, y, thickness, height, color);
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

const foregroundScore = (png, x, y, width, height) => {
  let score = 0;
  const startX = Math.max(0, Math.round(x));
  const startY = Math.max(0, Math.round(y));
  const endX = Math.min(png.width, Math.round(x + width));
  const endY = Math.min(png.height, Math.round(y + height));
  for (let row = startY; row < endY; row += 1) {
    for (let column = startX; column < endX; column += 1) {
      const offset = ((row * png.width) + column) * 4;
      const red = png.data[offset];
      const green = png.data[offset + 1];
      const blue = png.data[offset + 2];
      const gray = ((red * 30) + (green * 59) + (blue * 11)) / 100;
      const spread = Math.max(red, green, blue) - Math.min(red, green, blue);
      if (gray < 190 || (spread > 34 && gray < 238)) score += 1;
    }
  }
  return score;
};

const badgePosition = (png, callout, badgeWidth, badgeHeight) => {
  const { x, y, width, height } = callout;
  const candidates = [
    [x + 4, y - badgeHeight - 3],
    [x + 4, y + 4],
    [x + 4, y + height + 3],
    [x - badgeWidth - 3, y + 4],
    [x + width + 3, y + 4],
  ].map(([candidateX, candidateY]) => [
    Math.max(0, Math.min(Math.round(candidateX), png.width - badgeWidth)),
    Math.max(0, Math.min(Math.round(candidateY), png.height - badgeHeight)),
  ]);
  return candidates.reduce((best, candidate) => {
    const score = foregroundScore(
      png,
      candidate[0] - 2,
      candidate[1] - 2,
      badgeWidth + 4,
      badgeHeight + 4,
    );
    if (!best || score < best.score) return { position: candidate, score };
    return best;
  }, null).position;
};

const validateCallout = (callout, png) => {
  const { shape, x, y, width, height, label } = callout;
  if (shape !== 'rectangle') throw new Error('Callout shape must be rectangle');
  if (![x, y, width, height].every(Number.isFinite)) {
    throw new Error('Rectangle callout coordinates must be finite numbers');
  }
  if (width <= 0 || height <= 0) throw new Error('Rectangle callout dimensions must be positive');
  if (x < 0 || y < 0 || x + width > png.width || y + height > png.height) {
    throw new Error('Rectangle callout must remain inside the screenshot bounds');
  }
  if (!/^\d+$/.test(String(label))) throw new Error('Callout label must contain digits only');
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

  callouts.forEach((callout) => {
    validateCallout(callout, png);
    const { x, y, width, height, label } = callout;
    const borderThickness = 3;
    const badgeWidth = String(label).length > 1 ? 30 : 24;
    const badgeHeight = 24;
    const [badgeX, badgeY] = badgePosition(png, callout, badgeWidth, badgeHeight);

    drawRectangle(png, x, y, width, height, borderThickness, RED);
    drawFilledRectangle(png, badgeX, badgeY, badgeWidth, badgeHeight, RED);
    drawLabel(png, badgeX + (badgeWidth / 2), badgeY + (badgeHeight / 2), label);
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
