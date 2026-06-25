import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const files = [
  {
    label: "customer_r001",
    path: "C:/Users/tumsu/Downloads/Requirement on New System_R001.xlsx",
  },
  {
    label: "ours_manday",
    path: "C:/365_project/TheCool18e/Dev/output/ams_workflow_editable_new/AMS_TH_PRESENT_PACKAGE/02_AMS_Workflow_Mapping_with_Manday.xlsx",
  },
];

for (const file of files) {
  const blob = await FileBlob.load(file.path);
  const workbook = await SpreadsheetFile.importXlsx(blob);
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 16000,
    tableMaxRows: 8,
    tableMaxCols: 12,
    tableMaxCellChars: 140,
  });
  console.log(`### ${file.label}`);
  console.log(summary.ndjson);
}
