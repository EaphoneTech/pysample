import json
from pathlib import Path
from typing import Any

import click
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from loguru import logger


def read_config(config_path: str) -> dict[str, Any]:
    try:
        with open(config_path, encoding="utf-8") as file:
            config = json.load(file)
        logger.info("配置文件已从 {} 加载", config_path)
        return config
    except Exception as e:
        logger.error("无法从 {} 加载配置文件: {}", config_path, e)
        raise


def scan_files(
    base_dir: str,
    patterns: list[str],
    extensions: list[str],
    ignore_dirs: list[str],
    verbose: bool,
) -> list[Path]:
    base_path = Path(base_dir)
    if not base_path.exists() or not base_path.is_dir():
        logger.error("基础路径 {} 不存在或不是一个目录", base_path)
        raise ValueError(f"基础路径 {base_path} 不存在或不是一个目录")

    matched_files: list[Path] = []

    for pattern in patterns:
        for ext in extensions:
            if verbose:
                logger.debug("正在扫描路径: {}/{}.{}", base_path, pattern, ext)
            for file_path in base_path.glob(f"{pattern}.{ext}"):
                if file_path.is_file() and all(
                    ignore_dir not in file_path.parts for ignore_dir in ignore_dirs
                ):
                    relative_path = file_path.relative_to(base_path)
                    matched_files.append(relative_path)
                    logger.debug("匹配的文件: {}", relative_path)

    logger.info("总匹配文件数: {}", len(matched_files))
    return matched_files


def remove_consecutive_blank_lines(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = [
        line.replace("\t", "    ") for line in lines if len(line.strip()) > 0
    ]

    return "\n".join(cleaned_lines)


def set_font(doc):
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Microsoft YaHei"
    rFonts = font.element.rPr.rFonts
    rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")


def add_title_page(doc: Document, title: str, version: str, company: str) -> None:
    # 计算剩余空间并将公司信息放置在接近底部的位置
    section = doc.sections[0]
    page_height = (
        section.page_height.cm
        - section.top_margin.cm
        - section.bottom_margin.cm
        - 0.4  # section.header
        - 0.4  # section.footer
    )
    current_height = (
        2.5  # 假设标题行高约为2.5cm
        + 0.5  # 假设版本行高约为0.5cm
        + 0.5  # 假设“源代码”行高约为0.5cm
        + 8  # 手动再调整一下
    )  # 假设段间距为1.5cm

    remaining_space = (page_height - current_height) / 2

    # 添加空白段落以填充剩余空间
    blank_paragraph = doc.add_paragraph("")
    blank_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    blank_paragraph.paragraph_format.space_after = Pt(
        remaining_space * 28.35
    )  # cm to pt conversion

    # 创建标题页
    title_paragraph = doc.add_paragraph(title)
    title_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    title_run = title_paragraph.runs[0]
    title_run.bold = True
    title_run.font.size = Pt(26)  # 一号字体大小约为26pt

    # 添加版本信息
    version_paragraph = doc.add_paragraph(version)
    version_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    version_run = version_paragraph.runs[0]
    version_run.font.size = Pt(14)

    # 添加“源代码”字样
    source_code_paragraph = doc.add_paragraph("源代码")
    source_code_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    source_code_run = source_code_paragraph.runs[0]
    source_code_run.font.size = Pt(14)

    # 添加空白段落以填充剩余空间
    blank_paragraph = doc.add_paragraph("")
    blank_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    blank_paragraph.paragraph_format.space_after = Pt(
        remaining_space * 28.35
    )  # cm to pt conversion

    # 添加公司信息
    company_paragraph = doc.add_paragraph(company)
    company_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    company_run = company_paragraph.runs[0]
    company_run.font.size = Pt(14)

    # 添加分页符
    doc.add_page_break()


def add_header_footer(doc: Document, title: str, version: str) -> None:
    # 设置页边距为最窄
    section = doc.sections[0]
    section.top_margin = Cm(0.5)
    section.bottom_margin = Cm(0.5)
    section.left_margin = Cm(0.6)
    section.right_margin = Cm(0.6)
    section.header_distance = Cm(0.1)
    section.footer_distance = Cm(0.1)

    # 设置页眉高度
    header = section.header
    header.height = Cm(0.2)
    header_paragraph = header.paragraphs[0]
    header_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    header_paragraph.paragraph_format.space_before = Pt(0)
    header_paragraph.paragraph_format.space_after = Pt(0)

    # 添加页眉内容
    header_run = header_paragraph.add_run(f"{title} {version}\t\t\t")
    header_run.font.size = Pt(10)

    # 添加当前页码到页眉右侧
    run = header_paragraph.add_run()
    fldSimple = OxmlElement("w:fldSimple")
    fldSimple.set(qn("w:instr"), " PAGE ")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fldSimple.append(r)
    run._r.append(fldSimple)

    # 添加斜杠到页眉右侧
    run = header_paragraph.add_run("/")
    run.font.size = Pt(10)

    # 添加总页码到页眉右侧
    run = header_paragraph.add_run()
    fldSimple = OxmlElement("w:fldSimple")
    fldSimple.set(qn("w:instr"), " NUMPAGES ")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fldSimple.append(r)
    run._r.append(fldSimple)

    # 设置页脚高度
    footer = section.footer
    footer.height = Cm(0.2)
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    footer_paragraph.paragraph_format.space_before = Pt(0)
    footer_paragraph.paragraph_format.space_after = Pt(0)

    # 添加页脚内容
    footer_run = footer_paragraph.add_run(f"{title} {version}\t\t\t")
    footer_run.font.size = Pt(10)

    # 添加当前页码到页脚右侧
    run = footer_paragraph.add_run()
    fldSimple = OxmlElement("w:fldSimple")
    fldSimple.set(qn("w:instr"), " PAGE ")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fldSimple.append(r)
    run._r.append(fldSimple)

    # 添加斜杠到页脚右侧
    run = footer_paragraph.add_run("/")
    run.font.size = Pt(10)

    # 添加总页码到页脚右侧
    run = footer_paragraph.add_run()
    fldSimple = OxmlElement("w:fldSimple")
    fldSimple.set(qn("w:instr"), " NUMPAGES ")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fldSimple.append(r)
    run._r.append(fldSimple)

    # 添加制表符并设置其位置
    tab_stops = header_paragraph.paragraph_format.tab_stops
    tab_stops.add_tab_stop(Cm(20), WD_TAB_ALIGNMENT.RIGHT)
    tab_stops = footer_paragraph.paragraph_format.tab_stops
    tab_stops.add_tab_stop(Cm(20), WD_TAB_ALIGNMENT.RIGHT)


def add_main_content(
    doc: Document,
    files: list[Path],
    include_line_numbers: bool,
    max_lines: int = 2000,
) -> None:
    total_lines = 0  # 初始化总行数计数器

    for i, file_path in enumerate(files):
        full_path = Path(file_path)
        try:
            with open(full_path, encoding="utf-8") as file:
                content = file.read()
                content = remove_consecutive_blank_lines(content)
                lines = content.splitlines()

                if include_line_numbers:
                    numbered_lines = [
                        f"{i + 1}: {line}"
                        for i, line in enumerate(lines, start=total_lines + 1)
                    ]
                    content = "\n".join(numbered_lines)

                # 如果当前不是最后一个文件且总行数加上当前文件行数超过 max_lines, 则跳过后续文件
                if (
                    i < len(files) - 1
                    and max_lines is not None
                    and total_lines + len(lines) > max_lines
                ):
                    logger.info("已达到行数限制 {}", max_lines)
                    break

                doc.add_paragraph(content)
                total_lines += len(lines)  # 更新总行数计数器
                logger.debug("加入第 {} 个文件 {}", i + 1, full_path)

        except Exception as e:
            logger.error("无法读取文件 {}: {}", full_path, e)


def add_content_to_docx(
    doc: Document,
    title: str,
    version: str,
    company: str,
    files: list[Path],
    include_line_numbers: bool,
) -> None:
    # 设置全局字体
    set_font(doc)

    # 添加页眉和页脚
    add_header_footer(doc, title, version)

    # 添加标题页
    add_title_page(doc, title, version, company)

    # 添加正文内容
    add_main_content(doc, files, include_line_numbers)


@click.command()
@click.option("--verbose", is_flag=True, default=False, help="启用详细日志输出")
def main(verbose: bool) -> None:
    config_path = ".bring-it/sample.config.json"

    if verbose:
        logger.level("DEBUG")
        logger.info("详细日志已启用")
    else:
        logger.level("INFO")

    config = read_config(config_path)

    for group in config.get("group", []):
        base_dir = group.get("cwd", "")
        patterns = group.get("patterns", [])
        extensions = group.get("extensions", [])
        ignore_dirs = group.get("ignore", [])
        title = group.get("title", "未命名文档")
        version = group.get("version", "1.0")
        company = group.get("company", "未知公司")
        include_line_numbers = group.get("lineNumber", False)

        matched_files = scan_files(base_dir, patterns, extensions, ignore_dirs, verbose)
        output_file = Path(f"./.bring-it/sample/{title}_{version}.docx")

        doc = Document()
        add_content_to_docx(
            doc, title, version, company, matched_files, include_line_numbers
        )
        doc.save(output_file)
        logger.info("DOCX 文件已生成: {}", output_file)


if __name__ == "__main__":
    main()
