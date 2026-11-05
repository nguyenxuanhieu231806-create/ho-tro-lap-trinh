"""Read bounded DOCX/TXT documents in structural order, without executing content."""
from __future__ import annotations

import hashlib
import io
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_EXPANDED_BYTES = 40 * 1024 * 1024
MAX_TEXT_CHARS = 1_000_000
MAX_IMAGES = 100
MAX_BLOCKS = 5000
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
W = "{" + NS["w"] + "}"


def _xml(data: bytes):
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Tài liệu có khai báo XML không được hỗ trợ.")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("Cấu trúc Word không hợp lệ.") from exc


def _mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def parse_document(filename: str, data: bytes) -> dict:
    """Return blocks/images/warnings; page metadata is deliberately absent."""
    name = Path(filename.replace("\\", "/")).name
    extension = Path(name).suffix.lower()
    if not name or not data or len(data) > MAX_FILE_BYTES:
        raise ValueError("Tệp trống hoặc vượt giới hạn 10 MiB.")
    if extension not in {".txt", ".docx"}:
        raise ValueError("Chỉ hỗ trợ Word .docx và văn bản .txt UTF-8. Hãy chuyển .doc sang .docx trước.")
    result = {"blocks": [], "images": [], "warnings": [], "unsupported": [],
              "parser": "fit-structured-docx-txt-v1", "filename": name}

    def add(kind, text, locator, section="", **extra):
        if len(result["blocks"]) >= MAX_BLOCKS:
            raise ValueError("Tài liệu vượt giới hạn 5.000 khối nội dung; hãy chia thành các tài liệu nhỏ hơn.")
        block = {"id": f"b{len(result['blocks']) + 1:06d}", "kind": kind,
                 "text": text, "locator": locator, "section": section,
                 "order": len(result["blocks"]), **extra}
        result["blocks"].append(block)
        return block

    if extension == ".txt":
        try:
            content = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Tệp .txt phải dùng UTF-8; chưa tự đoán bảng mã.") from exc
        if "\x00" in content or len(content) > MAX_TEXT_CHARS:
            raise ValueError("Tệp văn bản không hợp lệ hoặc vượt một triệu ký tự.")
        lines = content.replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)
        pending, first, fenced = [], 1, False
        for index, line in enumerate(lines, 1):
            if not pending:
                first = index
            pending.append(line)
            if line.lstrip().startswith("```"):
                fenced = not fenced
            if (not line.strip() and not fenced) or index == len(lines):
                value = "".join(pending)
                if value.strip():
                    kind = "code" if value.lstrip().startswith("```") else "paragraph"
                    add(kind, value, f"Dòng {first}–{index}" if first != index else f"Dòng {first}",
                        line_start=first, line_end=index)
                pending.clear()
        return result

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("Tệp .docx không phải gói Word hợp lệ.") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > 2000 or sum(part.file_size for part in infos) > MAX_EXPANDED_BYTES:
            raise ValueError("Tài liệu có quá nhiều phần hoặc dữ liệu giải nén vượt 40 MiB.")
        if any(part.flag_bits & 1 or part.file_size > 8 * 1024 * 1024 for part in infos):
            raise ValueError("Không hỗ trợ tệp mã hóa hoặc phần nhúng quá lớn.")
        names = {part.filename for part in infos}
        if len(names) != len(infos):
            raise ValueError("Gói Word có phần trùng tên, không xác định được nội dung đáng tin cậy.")
        if "word/document.xml" not in names:
            raise ValueError("Tệp thiếu nội dung Word.")
        if any("vbaproject" in item.lower() or item.startswith("word/embeddings/") for item in names):
            result["unsupported"].append("Macro hoặc đối tượng nhúng: hãy xuất bản Word không có đối tượng này.")
        document = _xml(archive.read("word/document.xml"))
        relationships = {}
        rel_name = "word/_rels/document.xml.rels"
        if rel_name in names:
            for relationship in _xml(archive.read(rel_name)):
                relationships[relationship.get("Id")] = dict(relationship.attrib)
        if document.find(".//w:txbxContent", NS) is not None:
            result["unsupported"].append("Có hộp văn bản chưa được xác định thứ tự đọc; hãy chuyển thành đoạn văn trước khi công bố.")
        if document.find(".//w:pict", NS) is not None:
            result["unsupported"].append("Có ảnh/đối tượng VML cũ chưa được đọc; hãy chuyển sang ảnh inline chuẩn trong Word.")
        if any("officeDocument/2006/math" in node.tag for node in document.iter()):
            result["unsupported"].append("Có công thức Word chưa được trích chắc chắn; hãy bổ sung biểu diễn văn bản trước khi công bố.")
        if document.find(".//w:ins", NS) is not None or document.find(".//w:del", NS) is not None:
            result["unsupported"].append("Có thay đổi đang theo dõi; hãy chấp nhận hoặc từ chối thay đổi trong Word trước khi nạp lại.")
        for part in ("word/footnotes.xml", "word/endnotes.xml"):
            if part in names:
                tree = _xml(archive.read(part))
                if any((node.text or "").strip() for node in tree.iter(W + "t")):
                    result["unsupported"].append("Có chú thích chân trang/cuối tài liệu chưa được ánh xạ; hãy chuyển nội dung chú thích vào văn bản chính.")
        heading_stack = []
        paragraph_number = 0
        table_number = 0

        def section():
            return " / ".join(heading_stack)

        def paragraph(element, locator=None):
            nonlocal paragraph_number
            paragraph_number += 1
            locator = locator or f"Đoạn {paragraph_number}"
            style_node = element.find("w:pPr/w:pStyle", NS)
            style = style_node.get(W + "val", "") if style_node is not None else ""
            text_parts = []
            text_number = 0

            def flush():
                nonlocal text_number
                text = "".join(text_parts)
                text_parts.clear()
                if not text.strip():
                    return
                text_number += 1
                label = locator + (f", phần {text_number}" if text_number > 1 else "")
                match = re.search(r"heading\s*([1-9])", style, re.I)
                if match and text_number == 1:
                    level = int(match.group(1))
                    del heading_stack[level - 1:]
                    heading_stack.append(text.strip())
                block = add("code" if "code" in style.lower() else "paragraph", text, label, section(), style=style)
                if (style.lower() == "caption" or re.match(r"\s*(?:Hình|Figure|Ảnh|Sơ đồ)\s+\S", text, re.I)):
                    prior = result["blocks"][-2] if len(result["blocks"]) > 1 else None
                    if prior and prior["kind"] == "image":
                        image = next(item for item in result["images"] if item["id"] == prior["image_id"])
                        image["caption"] = text
                        image["caption_block_id"] = block["id"]

            def walk(node):
                if node.tag in {W + "del", W + "txbxContent"}:
                    return
                if node.tag == W + "t":
                    text_parts.append(node.text or "")
                elif node.tag == W + "tab":
                    text_parts.append("\t")
                elif node.tag in {W + "br", W + "cr"}:
                    text_parts.append("\n")
                elif node.tag == W + "drawing":
                    flush()
                    if not node.findall(".//a:blip", NS):
                        result["unsupported"].append(f"Đối tượng đồ họa không phải ảnh tại {locator}; hãy chuyển thành ảnh kèm mô tả.")
                    for blip in node.findall(".//a:blip", NS):
                        rid = blip.get("{" + NS["r"] + "}embed")
                        rel = relationships.get(rid, {})
                        if rel.get("TargetMode") == "External" or not rel.get("Target"):
                            result["unsupported"].append(f"Ảnh liên kết ngoài tại {locator}; không tự tải từ Internet.")
                            continue
                        target = posixpath.normpath(posixpath.join("word", rel["Target"]))
                        if not target.startswith("word/media/") or target not in names:
                            result["unsupported"].append(f"Không đọc được ảnh tại {locator}.")
                            continue
                        if len(result["images"]) >= MAX_IMAGES:
                            raise ValueError("Tài liệu vượt giới hạn 100 ảnh.")
                        image_data = archive.read(target)
                        props = node.find(".//wp:docPr", NS)
                        image_id = f"i{len(result['images']) + 1:04d}"
                        anchor = node.find("wp:anchor", NS) is not None
                        image_block = add("image", "", locator + f", ảnh {len(result['images']) + 1}",
                                          section(), image_id=image_id, anchor=anchor)
                        result["images"].append({"id": image_id, "data": image_data,
                            "mime": _mime(image_data), "hash": hashlib.sha256(image_data).hexdigest(),
                            "block_id": image_block["id"], "locator": image_block["locator"],
                            "alt_text": props.get("descr", "") if props is not None else "",
                            "caption": "", "reviewed": False, "anchor": anchor})
                        if anchor:
                            result["warnings"].append(f"Ảnh nổi tại {locator}: vị trí gắn đoạn được giữ; cần đối chiếu bố cục và mô tả.")
                elif node.tag == W + "object":
                    result["unsupported"].append(f"Đối tượng nhúng tại {locator} chưa được đọc.")
                else:
                    for child in node:
                        walk(child)
            walk(element)
            flush()

        def table(element, locator=None):
            nonlocal table_number
            table_number += 1
            locator = locator or f"Bảng {table_number}"
            table_block = add("table", "", locator, section())
            rows, lines = [], []
            has_header = False
            for row_index, row in enumerate(element.findall("w:tr", NS), 1):
                has_header = has_header or (row_index == 1 and row.find("w:trPr/w:tblHeader", NS) is not None)
                cells = []
                column = 1
                for cell in row.findall("w:tc", NS):
                    span = cell.find("w:tcPr/w:gridSpan", NS)
                    merge = cell.find("w:tcPr/w:vMerge", NS)
                    colspan = int(span.get(W + "val", "1")) if span is not None else 1
                    colspan = max(1, min(colspan, 1000))
                    native = []
                    for item in cell:
                        if item.tag == W + "p":
                            # Preserve tables as tables; extract inline images in their cell position.
                            before = len(result["blocks"])
                            paragraph(item, f"{locator}, hàng {row_index}, cột {column}")
                            added = result["blocks"][before:]
                            native.extend(block["text"] for block in added if block["kind"] in {"paragraph", "code"})
                            for block in added:
                                block["table_context"] = locator
                        elif item.tag == W + "tbl":
                            result["unsupported"].append(f"Bảng lồng tại {locator}, hàng {row_index}, cột {column}; hãy chuyển bảng phẳng để nạp đầy đủ.")
                    text = "\n".join(native)
                    cells.append({"column": column, "colspan": colspan,
                                  "vmerge": merge.get(W + "val", "continue") if merge is not None else None,
                                  "text": text})
                    column += colspan
                rows.append(cells)
                lines.append(f"Hàng {row_index}: " + " | ".join(f"Cột {c['column']}: {c['text']}" for c in cells))
            # Cell paragraphs are retained for precise locations; the table block is a structured view,
            # not a second independent text source to count as separate evidence.
            table_block.update(text="\n".join(lines), rows=rows, has_header=has_header)

        body = document.find("w:body", NS)
        if body is None:
            raise ValueError("Tài liệu không có phần nội dung chính.")
        for child in body:
            if child.tag == W + "p":
                paragraph(child)
            elif child.tag == W + "tbl":
                table(child)
            elif child.tag == W + "sdt":
                control = child.find("w:sdtContent", NS)
                if control is None:
                    result["unsupported"].append("Khối điều khiển nội dung Word không có nội dung đọc được.")
                else:
                    for item in control:
                        if item.tag == W + "p":
                            paragraph(item)
                        elif item.tag == W + "tbl":
                            table(item)
                        else:
                            result["unsupported"].append("Có cấu trúc lồng trong khối điều khiển chưa đọc được; hãy chuyển thành văn bản thường.")
            elif child.tag != W + "sectPr":
                result["unsupported"].append("Có khối Word đặc biệt chưa được xác định thứ tự đọc; hãy xuất Word đơn giản hơn.")
        for name_part in sorted(names):
            if re.fullmatch(r"word/(?:header|footer)\d+\.xml", name_part):
                tree = _xml(archive.read(name_part))
                if any((n.text or "").strip() for n in tree.iter(W + "t")) or tree.find(".//w:drawing", NS) is not None:
                    result["warnings"].append("Có đầu/chân trang: không suy ra số trang từ phần này; nội dung chính được trích riêng.")
                    text = " ".join(n.text or "" for n in tree.iter(W + "t"))
                    if text.strip():
                        add("supplementary", text, f"Phần {Path(name_part).name}", "Đầu/chân trang")
                    if tree.find(".//w:drawing", NS) is not None or tree.find(".//w:pict", NS) is not None:
                        result["unsupported"].append("Có ảnh đầu/chân trang chưa được ánh xạ; hãy chuyển ảnh cần hỏi đáp vào nội dung chính.")
        if sum(len(block["text"]) for block in result["blocks"]) > MAX_TEXT_CHARS:
            raise ValueError("Tài liệu vượt giới hạn một triệu ký tự trích xuất.")
        result["warnings"] = list(dict.fromkeys(result["warnings"]))
        result["unsupported"] = list(dict.fromkeys(result["unsupported"]))
        if result["images"]:
            result["warnings"].append("Ảnh chưa được OCR tự động. Hãy mô tả chính xác hoặc đánh dấu ảnh trang trí trước khi công bố.")
        return result


def chunk_blocks(blocks: list[dict], limit: int = 1000) -> list[dict]:
    """Keep every nonempty content span with stable offsets and no invented pages."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 500 <= limit <= 4000:
        raise ValueError("Giới hạn chia đoạn phải từ 500 đến 4.000 ký tự.")
    chunks = []
    for block in blocks:
        if block.get("table_context") or block.get("decorative"):
            # These cell spans are represented by the table block, avoiding duplicate chunks.
            continue
        text = block.get("text", "")
        if not text.strip():
            continue
        position = 0
        table_context = ""
        if block["kind"] == "table":
            first_line = text.split("\n", 1)[0]
            if len(first_line) <= 350:
                table_context = "Ngữ cảnh hàng đầu của bảng: " + first_line + "\n"
        while position < len(text):
            context = table_context if position > 0 else ""
            available = limit - len(context)
            end = min(position + available, len(text))
            if end < len(text):
                boundary = text.rfind("\n", position + available // 2, end)
                if block["kind"] == "code" and boundary < 0:
                    boundary = text.rfind("\n", position, end)
                    if boundary < 0:
                        raise ValueError("Có dòng mã dài hơn giới hạn chia đoạn; hãy xuống dòng hợp lệ trước khi công bố.")
                if boundary < 0:
                    boundary = text.rfind(" ", position + available // 2, end)
                if boundary >= 0:
                    end = boundary + 1
            value = text[position:end]
            if value.strip():
                chunks.append({"block_id": block["id"], "text": context + value,
                               "locator": block["locator"], "section": block.get("section", ""),
                               "kind": block["kind"], "offset_start": position, "offset_end": end,
                               "context_text": context, "image_id": block.get("image_id")})
            position = end
    return chunks
