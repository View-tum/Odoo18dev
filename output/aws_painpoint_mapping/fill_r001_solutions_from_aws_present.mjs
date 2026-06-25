import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const mode = process.argv[2] || "inspect";

const outputDir = "C:/365_project/TheCool18e/Dev/output/aws_painpoint_mapping";
const r001Path = "C:/Users/tumsu/Desktop/AMS_Present/ams_source_files/02_Requirement_on_New_System_R001.xlsx";
const awsPath = "C:/Users/tumsu/Desktop/AMS_Present/AWS_Present.xlsx";
const backupPath = "C:/Users/tumsu/Desktop/AMS_Present/ams_source_files/02_Requirement_on_New_System_R001_backup_before_solution.xlsx";
const filledPath = "C:/Users/tumsu/Desktop/AMS_Present/ams_source_files/02_Requirement_on_New_System_R001_With_Solution.xlsx";
const previewPath = path.join(outputDir, "r001_solution_filled_preview.png");

function sourceRowNumber(value) {
  if (!value) return null;
  const text = String(value);
  const match = text.match(/A(\d+)/);
  return match ? Number(match[1]) : null;
}

function clean(value) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function buildSolution(row) {
  const odooFit = clean(row[5]);
  const apps = clean(row[6]);
  const fit = clean(row[7]);
  const standardCustom = clean(row[8]);
  const pain = clean(row[9]);
  const md = clean(row[11]);
  const priority = clean(row[12]);
  const parts = [];
  if (odooFit) parts.push(`Odoo Solution: ${odooFit}`);
  if (apps) parts.push(`Module: ${apps}`);
  if (fit || standardCustom) parts.push(`Fit: ${[fit, standardCustom].filter(Boolean).join(" / ")}`);
  if (pain) parts.push(`Pain Point: ${pain}`);
  if (md || priority) parts.push(`Estimate/Priority: ${[md ? `${md} MD` : "", priority].filter(Boolean).join(" / ")}`);
  return parts.join("\n");
}

function styleHeader(range) {
  range.format = {
    fill: "#6B0F3F",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "middle",
    borders: { preset: "all", style: "thin", color: "#FFFFFF" },
  };
}

function styleBody(range) {
  range.format = {
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#CBD5E1" },
  };
}

async function importWorkbook(filePath) {
  const blob = await FileBlob.load(filePath);
  return SpreadsheetFile.importXlsx(blob);
}

async function inspectFiles() {
  for (const [label, filePath] of [["R001", r001Path], ["AWS_PRESENT", awsPath]]) {
    console.log(`=== ${label} ===`);
    const wb = await importWorkbook(filePath);
    const sheets = await wb.inspect({
      kind: "sheet",
      include: "id,name",
      maxChars: 6000,
    });
    console.log(sheets.ndjson);

    for (const sheetName of ["Requirement", "06 R001 Requirement Links", "Pain Point Mapping"]) {
      try {
        const region = await wb.inspect({
          kind: "region",
          sheetId: sheetName,
          range: sheetName === "Requirement" ? "A1:F82" : "A1:R55",
          maxChars: 30000,
          tableMaxRows: sheetName === "Requirement" ? 82 : 55,
          tableMaxCols: sheetName === "Requirement" ? 6 : 18,
          tableMaxCellChars: 180,
        });
        console.log(`=== ${label} ${sheetName} ===`);
        console.log(region.ndjson);
      } catch {
      }
    }
  }
}

async function inspectFilled() {
  const wb = await importWorkbook(filledPath);
  const summary = await wb.inspect({
    kind: "sheet,region",
    sheetId: "Requirement",
    range: "A1:K64",
    maxChars: 24000,
    tableMaxRows: 64,
    tableMaxCols: 11,
    tableMaxCellChars: 160,
  });
  console.log(summary.ndjson);
  const preview = await wb.render({
    sheetName: "Requirement",
    range: "A1:K64",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
  const errors = await wb.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "final formula error scan",
  });
  console.log("=== FORMULA ERRORS ===");
  console.log(errors.ndjson);
  console.log(previewPath);
}

async function applySolutions() {
  await fs.mkdir(outputDir, { recursive: true });
  try {
    await fs.access(backupPath);
  } catch {
    await fs.copyFile(r001Path, backupPath);
  }

  const r001 = await importWorkbook(r001Path);
  const aws = await importWorkbook(awsPath);
  const reqSheet = r001.worksheets.getItem("Requirement");
  const awsSheet = aws.worksheets.getItem("06 R001 Requirement Links");
  const mapping = awsSheet.getRange("A5:R49").values;
  const dataRows = mapping.slice(1).filter((row) => row[0] !== null && row[0] !== undefined);

  reqSheet.getRange("D4:K4").values = [[
    "Solution",
    "Link AWS Present",
    "Odoo Module",
    "Standard vs Custom",
    "Pain Point Mapping",
    "MD",
    "Priority",
    "Present Note",
  ]];
  styleHeader(reqSheet.getRange("D4:K4"));

  for (const row of dataRows) {
    const sourceRow = sourceRowNumber(row[13]);
    if (!sourceRow) continue;
    const solution = buildSolution(row);
    reqSheet.getRange(`D${sourceRow}:K${sourceRow}`).values = [[
      solution,
      `เปิด AWS Present Seq ${row[0]}`,
      clean(row[6]),
      clean(row[8]),
      clean(row[10]),
      clean(row[11]),
      clean(row[12]),
      clean(row[17]),
    ]];
  }

  styleBody(reqSheet.getRange("D5:K64"));
  reqSheet.getRange("A:A").format.columnWidth = 8;
  reqSheet.getRange("B:B").format.columnWidth = 48;
  reqSheet.getRange("C:C").format.columnWidth = 9;
  reqSheet.getRange("D:D").format.columnWidth = 58;
  reqSheet.getRange("E:E").format.columnWidth = 22;
  reqSheet.getRange("F:F").format.columnWidth = 32;
  reqSheet.getRange("G:G").format.columnWidth = 24;
  reqSheet.getRange("H:H").format.columnWidth = 44;
  reqSheet.getRange("I:I").format.columnWidth = 9;
  reqSheet.getRange("J:J").format.columnWidth = 12;
  reqSheet.getRange("K:K").format.columnWidth = 56;
  reqSheet.getRange("A4:K4").format.rowHeight = 38;
  reqSheet.getRange("A5:K64").format.rowHeight = 92;
  reqSheet.freezePanes.freezeRows(4);

  const preview = await r001.render({
    sheetName: "Requirement",
    range: "A1:K64",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

  const errors = await r001.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "formula error scan",
  });
  console.log("=== FORMULA ERRORS ===");
  console.log(errors.ndjson);

  const output = await SpreadsheetFile.exportXlsx(r001);
  let savedPath = r001Path;
  try {
    await output.save(r001Path);
  } catch (error) {
    if (error && error.code === "EBUSY") {
      savedPath = filledPath;
      await output.save(filledPath);
    } else {
      throw error;
    }
  }
  console.log(savedPath);
  console.log(backupPath);
  console.log(previewPath);
}

if (mode === "inspect") {
  await inspectFiles();
} else if (mode === "apply") {
  await applySolutions();
} else if (mode === "inspect-filled") {
  await inspectFilled();
}
