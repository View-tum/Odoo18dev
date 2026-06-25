from pathlib import Path
import xml.etree.ElementTree as ET

present_path = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH\04_Workflow_Business_Flow_AMS.drawio")
package_path = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE\06_AMS_R001_Blueprint_Swimlane_TH.drawio")

EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
    "strokeColor=#334155;strokeWidth=1.35;endArrow=block;endFill=1;fontSize=12;"
    "fontColor=#111827;labelBackgroundColor=#FFFFFF;fontFamily=Arial;"
)
PROCESS_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#D9EAD3;strokeColor=#334155;"
    "fontColor=#111827;spacing=10;fontSize=12;fontFamily=Arial;"
)


def is_decision(cell):
    return cell.get("vertex") == "1" and (
        "rhombus" in (cell.get("style") or "") or "?" in (cell.get("value") or "")
    )


def norm_label(decision_text, label, used):
    raw = (label or "").strip()
    text = (decision_text or "").lower()
    low = raw.lower()
    if low.startswith("yes") or low.startswith("no"):
        return raw
    if raw in {"Pass", "ผ่าน"}:
        return "Yes / Pass"
    if raw in {"Fail", "ไม่ผ่าน"}:
        return "No / Fail"
    if raw == "Buy":
        return "Yes / Buy"
    if raw == "Make":
        return "No / Make"
    if raw == "Stock":
        return "No / Use stock"
    if not raw:
        if "qc pass" in text or text == "pass?":
            return "No / Fail or rework" if "Yes" in used else "Yes / Pass"
        if "forecast" in text or "file/api" in text:
            return "Yes / File or API" if "Yes" not in used else "No / Manual input"
        if "best supplier" in text:
            return "No / compare again" if "Yes" in used else "No / compare again"
        if "approval" in text or "budget" in text:
            return "No / standard route" if "No" not in used else "Yes / approval needed"
        return "Yes" if "Yes" not in used else "No"
    if "pass" in low:
        return f"Yes / {raw}"
    if "fail" in low or "return" in low:
        return f"No / {raw}"
    return raw


def add_process(root, cell_id, value, x, y, w=190, h=64):
    cell = ET.SubElement(root, "mxCell", {
        "id": cell_id,
        "value": value,
        "style": PROCESS_STYLE,
        "vertex": "1",
        "parent": "1",
    })
    ET.SubElement(cell, "mxGeometry", {
        "x": str(x),
        "y": str(y),
        "width": str(w),
        "height": str(h),
        "as": "geometry",
    })
    return cell


def add_edge(root, cell_id, source, target, label):
    cell = ET.SubElement(root, "mxCell", {
        "id": cell_id,
        "value": label,
        "style": EDGE_STYLE,
        "edge": "1",
        "parent": "1",
        "source": source,
        "target": target,
    })
    ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    return cell


def geom_xy(cell):
    geo = cell.find("mxGeometry")
    if geo is None:
        return 0.0, 0.0
    return float(geo.get("x") or 0), float(geo.get("y") or 0)


def ensure_missing_branch(page_name, root, decision, outgoing, used):
    decision_text = decision.get("value") or ""
    decision_id = decision.get("id")
    x, y = geom_xy(decision)
    base = f"yn_{page_name}_{decision_id}".replace(" ", "_").replace("/", "_")
    changed = 0

    if "ต้อง Custom?" in decision_text and "No" not in used:
        node_id = f"{base}_no_node"
        edge_id = f"{base}_no_edge"
        if root.find(f"mxCell[@id='{node_id}']") is None:
            add_process(root, node_id, "ใช้ Standard / Config ต่อ", x + 190, y + 90)
            add_edge(root, edge_id, decision_id, node_id, "No / ใช้ Standard")
            changed += 1

    if "FA / Customer Forecast" in decision_text and "No" not in used and outgoing:
        edge_id = f"{base}_no_edge"
        if root.find(f"mxCell[@id='{edge_id}']") is None:
            add_edge(root, edge_id, decision_id, outgoing[0].get("target"), "No / Manual RFQ or PO")
            changed += 1

    if "Standard enough?" in decision_text and "Yes" not in used:
        node_id = f"{base}_yes_node"
        edge_id = f"{base}_yes_edge"
        if root.find(f"mxCell[@id='{node_id}']") is None:
            add_process(root, node_id, "ใช้ Standard Odoo + UAT", x + 210, y - 80)
            add_edge(root, edge_id, decision_id, node_id, "Yes / Standard enough")
            changed += 1

    return changed


def fix_file(path):
    tree = ET.parse(path)
    mxfile = tree.getroot()
    changed = 0
    decision_count = 0
    edge_count = 0

    for page in mxfile.findall("diagram"):
        page_name = page.get("name") or "Page"
        graph_root = page.find(".//root")
        if graph_root is None:
            continue
        cells = list(graph_root.findall("mxCell"))
        decisions = [cell for cell in cells if is_decision(cell)]
        for decision in decisions:
            decision_count += 1
            outgoing = [
                cell for cell in graph_root.findall("mxCell")
                if cell.get("edge") == "1" and cell.get("source") == decision.get("id")
            ]
            used = set()
            for edge in outgoing:
                label = norm_label(decision.get("value") or "", edge.get("value") or "", used)
                if label != (edge.get("value") or ""):
                    edge.set("value", label)
                    changed += 1
                if label.lower().startswith("yes"):
                    used.add("Yes")
                if label.lower().startswith("no"):
                    used.add("No")
                edge_count += 1
            changed += ensure_missing_branch(page_name, graph_root, decision, outgoing, used)

    tree.write(path, encoding="utf-8", xml_declaration=False)
    return {"path": str(path), "decision_count": decision_count, "decision_edges": edge_count, "changed": changed}


results = []
results.append(fix_file(present_path))
package_path.write_text(present_path.read_text(encoding="utf-8"), encoding="utf-8")
results.append({"path": str(package_path), "copied_from_present": True})
print(results)
