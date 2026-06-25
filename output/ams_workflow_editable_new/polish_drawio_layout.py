from __future__ import annotations

import copy
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(r"C:\365_project\TheCool18e\Dev\output\ams_workflow_editable_new")
DRAWIO = ROOT / "AMS_Editable_Swimlane_Workflows.drawio"
BACKUP = ROOT / "AMS_Editable_Swimlane_Workflows_before_layout.drawio"
POLISHED = ROOT / "AMS_Editable_Swimlane_Workflows_polished.drawio"
AUDIT = ROOT / "layout_audit.json"


def geom(cell: ET.Element) -> ET.Element | None:
    return cell.find("mxGeometry")


def nums(cell: ET.Element) -> tuple[float, float, float, float] | None:
    g = geom(cell)
    if g is None:
        return None
    try:
        return (
            float(g.attrib.get("x", "0")),
            float(g.attrib.get("y", "0")),
            float(g.attrib.get("width", "0")),
            float(g.attrib.get("height", "0")),
        )
    except ValueError:
        return None


def set_nums(cell: ET.Element, x: float, y: float, w: float, h: float) -> None:
    g = geom(cell)
    if g is None:
        g = ET.SubElement(cell, "mxGeometry")
        g.set("as", "geometry")
    g.set("x", str(round(x)))
    g.set("y", str(round(y)))
    g.set("width", str(round(w)))
    g.set("height", str(round(h)))


def style(cell: ET.Element) -> str:
    return cell.attrib.get("style", "")


def set_style(cell: ET.Element, additions: dict[str, str], flags: list[str] | None = None) -> None:
    current = [part for part in style(cell).split(";") if part]
    values: dict[str, str] = {}
    ordered_flags: list[str] = []
    for part in current:
        if "=" in part:
            key, value = part.split("=", 1)
            values[key] = value
        else:
            ordered_flags.append(part)
    values.update(additions)
    if flags:
        for flag in flags:
            if flag not in ordered_flags:
                ordered_flags.append(flag)
    cell.set("style", ";".join(ordered_flags + [f"{k}={v}" for k, v in values.items()]) + ";")


def is_vertex(cell: ET.Element) -> bool:
    return cell.attrib.get("vertex") == "1"


def is_edge(cell: ET.Element) -> bool:
    return cell.attrib.get("edge") == "1"


def is_lane(cell: ET.Element) -> bool:
    return is_vertex(cell) and "swimlane" in style(cell)


def is_text(cell: ET.Element) -> bool:
    return is_vertex(cell) and style(cell).startswith("text;")


def is_note(cell: ET.Element) -> bool:
    return is_vertex(cell) and "shape=note" in style(cell)


def is_layout_node(cell: ET.Element) -> bool:
    return is_vertex(cell) and not is_lane(cell) and not is_text(cell)


def node_size(cell: ET.Element) -> tuple[int, int]:
    s = style(cell)
    value = cell.attrib.get("value", "")
    lines = value.count("\n") + 1
    if "rhombus" in s:
        return 176, 116
    if "shape=note" in s:
        return 720, 92
    if "shape=cylinder" in s:
        return 250, 88
    if "shape=document" in s:
        return 250, 84
    if "shape=parallelogram" in s:
        return 250, 84
    if "arcSize=50" in s:
        return 220, 84
    if "fillColor=#FCE4D6" in s or "fillColor=#E2F0D9" in s:
        return 270, 88
    return 250, 84 if lines <= 2 else 94


def group_columns(nodes: list[ET.Element]) -> dict[str, int]:
    centers: list[tuple[str, float]] = []
    for cell in nodes:
        box = nums(cell)
        if not box:
            continue
        x, _, w, _ = box
        centers.append((cell.attrib["id"], x + w / 2))
    centers.sort(key=lambda item: item[1])
    groups: list[list[tuple[str, float]]] = []
    for item in centers:
        if not groups or abs(item[1] - sum(v for _, v in groups[-1]) / len(groups[-1])) > 120:
            groups.append([item])
        else:
            groups[-1].append(item)
    result: dict[str, int] = {}
    for index, group in enumerate(groups):
        for cell_id, _ in group:
            result[cell_id] = index
    return result


def nearest_lane_index(box: tuple[float, float, float, float], lanes: list[ET.Element]) -> int:
    _, y, _, h = box
    center = y + h / 2
    best = 0
    best_distance = 10**9
    for index, lane in enumerate(lanes):
        lane_box = nums(lane)
        if not lane_box:
            continue
        _, ly, _, lh = lane_box
        if ly <= center <= ly + lh:
            return index
        distance = abs(center - (ly + lh / 2))
        if distance < best_distance:
            best = index
            best_distance = distance
    return best


def update_edge_style(cell: ET.Element) -> None:
    set_style(
        cell,
        {
            "edgeStyle": "orthogonalEdgeStyle",
            "rounded": "1",
            "orthogonalLoop": "1",
            "jettySize": "auto",
            "html": "1",
            "strokeColor": "#334155",
            "strokeWidth": "1.35",
            "endArrow": "block",
            "endFill": "1",
            "fontSize": "12",
            "fontColor": "#111827",
            "labelBackgroundColor": "#FFFFFF",
            "spacing": "4",
        },
    )


def polish_legend(graph: ET.Element) -> None:
    graph.set("dx", "1600")
    graph.set("dy", "980")
    graph.set("pageWidth", "1600")
    graph.set("pageHeight", "980")
    cells = graph.find("root")
    if cells is None:
        return
    vertices = [cell for cell in list(cells) if is_vertex(cell)]
    for cell in vertices:
        if is_text(cell):
            box = nums(cell)
            if not box:
                continue
            if box[1] < 50:
                set_nums(cell, 50, 26, 1500, 44)
                set_style(cell, {"fontSize": "26", "fontColor": "#5B1747"})
            else:
                set_nums(cell, 50, 76, 1500, 34)
                set_style(cell, {"fontSize": "14", "fontColor": "#475569"})
    nodes = [cell for cell in vertices if not is_text(cell)]
    shape_nodes = [cell for cell in nodes if not is_edge(cell)]
    positions = [
        (120, 170),
        (470, 170),
        (820, 170),
        (1170, 170),
        (120, 450),
        (470, 450),
        (820, 450),
        (1170, 450),
        (250, 735),
        (620, 735),
        (960, 715),
    ]
    for cell, (x, y) in zip(shape_nodes, positions):
        if is_note(cell):
            set_nums(cell, x, y, 520, 108)
        elif "rhombus" in style(cell):
            set_nums(cell, x, y - 12, 240, 124)
        else:
            set_nums(cell, x, y, 250, 104)
        set_style(cell, {"fontSize": "13", "spacing": "10", "shadow": "0"})
    for cell in cells:
        if is_edge(cell):
            update_edge_style(cell)


def polish_lane_page(graph: ET.Element) -> dict[str, object]:
    cells = graph.find("root")
    if cells is None:
        return {}
    lane_cells = sorted([cell for cell in list(cells) if is_lane(cell)], key=lambda c: nums(c)[1] if nums(c) else 0)
    if not lane_cells:
        return {}
    layout_nodes = [cell for cell in list(cells) if is_layout_node(cell)]
    regular_nodes = [cell for cell in layout_nodes if not is_note(cell)]
    column_map = group_columns(regular_nodes)
    col_count = max(column_map.values(), default=-1) + 1
    lane_count = len(lane_cells)
    lane_h = 216 if lane_count <= 6 else 232
    top = 132
    left = 44
    work_x = 285
    spacing = 310
    page_w = max(1700, int(work_x + max(col_count - 1, 0) * spacing + 420))
    page_h = int(top + lane_count * lane_h + 115)
    graph.set("dx", str(page_w))
    graph.set("dy", str(page_h))
    graph.set("pageWidth", str(page_w))
    graph.set("pageHeight", str(page_h))
    for cell in list(cells):
        if is_text(cell):
            box = nums(cell)
            if not box:
                continue
            if box[1] < 50:
                set_nums(cell, 50, 28, page_w - 100, 42)
                set_style(cell, {"fontSize": "26", "fontColor": "#5B1747"})
            else:
                set_nums(cell, 50, 76, page_w - 100, 34)
                set_style(cell, {"fontSize": "14", "fontColor": "#475569"})
    for index, lane in enumerate(lane_cells):
        set_nums(lane, left, top + index * lane_h, page_w - left * 2, lane_h)
        set_style(
            lane,
            {
                "html": "1",
                "horizontal": "0",
                "startSize": "46",
                "fillColor": "#F8FAFC",
                "strokeColor": "#CBD5E1",
                "fontColor": "#111827",
                "fontStyle": "1",
                "fontSize": "13",
            },
        )
    old_lane_by_id = {lane.attrib["id"]: nums(lane) for lane in lane_cells}
    lane_assignments: dict[str, int] = {}
    for cell in layout_nodes:
        box = nums(cell)
        if not box:
            continue
        lane_assignments[cell.attrib["id"]] = nearest_lane_index(box, lane_cells)
    stacked: dict[tuple[int, int], list[ET.Element]] = {}
    for cell in regular_nodes:
        col = column_map.get(cell.attrib["id"], 0)
        lane = lane_assignments.get(cell.attrib["id"], 0)
        stacked.setdefault((lane, col), []).append(cell)
    for (lane_index, col), group in stacked.items():
        center_x = work_x + col * spacing
        center_y = top + lane_index * lane_h + lane_h / 2
        total_h = sum(node_size(cell)[1] for cell in group) + max(0, len(group) - 1) * 14
        y = center_y - total_h / 2
        for cell in group:
            w, h = node_size(cell)
            set_nums(cell, center_x - w / 2, y, w, h)
            set_style(cell, {"fontSize": "12", "spacing": "10", "whiteSpace": "wrap", "html": "1", "shadow": "0"})
            y += h + 14
    notes = [cell for cell in layout_nodes if is_note(cell)]
    for index, cell in enumerate(notes):
        lane_index = lane_assignments.get(cell.attrib["id"], lane_count - 1)
        w, h = node_size(cell)
        x = min(work_x + 20 + index * 36, page_w - w - 80)
        y = top + lane_index * lane_h + lane_h / 2 - h / 2
        set_nums(cell, x, y, w, h)
        set_style(cell, {"fontSize": "12", "spacing": "10", "whiteSpace": "wrap", "html": "1", "shadow": "0"})
    for cell in list(cells):
        if is_edge(cell):
            update_edge_style(cell)
    return {
        "lanes": lane_count,
        "columns": col_count,
        "page_width": page_w,
        "page_height": page_h,
        "old_lane_snapshot": {k: v for k, v in old_lane_by_id.items() if v},
    }


def audit_diagram(diagram: ET.Element) -> dict[str, object]:
    graph = diagram.find("mxGraphModel")
    if graph is None:
        return {}
    root = graph.find("root")
    if root is None:
        return {}
    lanes = sorted([cell for cell in list(root) if is_lane(cell)], key=lambda c: nums(c)[1] if nums(c) else 0)
    nodes = [cell for cell in list(root) if is_layout_node(cell)]
    boxes: list[tuple[str, str, float, float, float, float, int | None]] = []
    for cell in nodes:
        box = nums(cell)
        if not box:
            continue
        lane_index = nearest_lane_index(box, lanes) if lanes else None
        label = re.sub(r"\s+", " ", cell.attrib.get("value", "")).strip()[:80]
        boxes.append((cell.attrib["id"], label, *box, lane_index))
    overlaps: list[dict[str, str]] = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            _, la, ax, ay, aw, ah, _ = a
            _, lb, bx, by, bw, bh, _ = b
            if ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by:
                overlaps.append({"a": la, "b": lb})
    lane_gaps: list[float] = []
    for lane_index in sorted({b[6] for b in boxes if b[6] is not None}):
        lane_boxes = sorted([b for b in boxes if b[6] == lane_index], key=lambda b: b[2])
        for left, right in zip(lane_boxes, lane_boxes[1:]):
            ly1, lh1 = left[3], left[5]
            ly2, lh2 = right[3], right[5]
            vertical_overlap = min(ly1 + lh1, ly2 + lh2) - max(ly1, ly2)
            if vertical_overlap > min(lh1, lh2) * 0.25:
                lane_gaps.append(right[2] - (left[2] + left[4]))
    outside = 0
    if lanes:
        for _, _, x, y, w, h, lane_index in boxes:
            lane_box = nums(lanes[lane_index or 0])
            if not lane_box:
                continue
            lx, ly, lw, lh = lane_box
            if x < lx or y < ly or x + w > lx + lw or y + h > ly + lh:
                outside += 1
    return {
        "page": diagram.attrib.get("name"),
        "node_count": len(nodes),
        "lane_count": len(lanes),
        "overlap_count": len(overlaps),
        "min_same_lane_gap": round(min(lane_gaps), 1) if lane_gaps else None,
        "nodes_outside_lanes": outside,
        "page_width": int(float(graph.attrib.get("pageWidth", "0"))),
        "page_height": int(float(graph.attrib.get("pageHeight", "0"))),
        "overlap_examples": overlaps[:5],
    }


def main() -> None:
    if not BACKUP.exists():
        shutil.copy2(DRAWIO, BACKUP)
    tree = ET.parse(BACKUP)
    mxfile = tree.getroot()
    mxfile.set("modified", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    diagnostics: list[dict[str, object]] = []
    for diagram in mxfile.findall("diagram"):
        graph = diagram.find("mxGraphModel")
        if graph is None:
            continue
        if diagram.attrib.get("name") == "Symbol Legend":
            polish_legend(graph)
            diagnostics.append({"page": diagram.attrib.get("name"), "layout": "legend"})
        else:
            result = polish_lane_page(graph)
            diagnostics.append({"page": diagram.attrib.get("name"), **result})
    polished_tree = copy.deepcopy(tree)
    tree.write(DRAWIO, encoding="utf-8", xml_declaration=False)
    polished_tree.write(POLISHED, encoding="utf-8", xml_declaration=False)
    audits = [audit_diagram(diagram) for diagram in ET.parse(DRAWIO).getroot().findall("diagram")]
    AUDIT.write_text(json.dumps({"diagnostics": diagnostics, "audit": audits}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"drawio": str(DRAWIO), "polished_copy": str(POLISHED), "backup": str(BACKUP), "pages": len(audits), "audit": audits}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
