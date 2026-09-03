import contextlib
import itertools
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pathspec
import typer

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)
logger = logging.getLogger("pysample")

app = typer.Typer()

# 配置文件路径（与 bring-it/sample 兼容）
CONFIG_PATH = Path(".bring-it/sample.config.json")

# 自动探测用的「语言名 -> 扩展名」映射
LANGUAGE_MAP: dict[str, list[str]] = {
    "Python": ["py"],
    "JavaScript": ["js", "jsx", "mjs", "cjs"],
    "TypeScript": ["ts", "tsx"],
    "Java": ["java"],
    "Go": ["go"],
    "Rust": ["rs"],
    "C": ["c", "h"],
    "C++": ["cpp", "cc", "cxx", "hpp", "hxx"],
    "C#": ["cs"],
    "Ruby": ["rb"],
    "PHP": ["php"],
    "HTML": ["html", "htm"],
    "CSS": ["css"],
    "Shell": ["sh", "bash"],
    "Kotlin": ["kt", "kts"],
    "Swift": ["swift"],
    "Scala": ["scala"],
    "Lua": ["lua"],
    "SQL": ["sql"],
    "Vue": ["vue"],
}

# 源码探测时跳过的常见垃圾/产物目录
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "target",
    "out",
    ".idea",
    ".vscode",
}


def read_config(config_path: Path) -> dict[str, Any]:
    try:
        with open(config_path, encoding="utf-8") as file:
            config = json.load(file)
        logger.info("已从 %s 加载了配置文件", config_path)
        return config
    except Exception:
        logger.error("无法从 %s 加载配置文件", config_path.resolve())
        raise


def scan_files(
    base_dir: str,
    patterns: list[str],
    extensions: list[str],
    ignore_dirs: list[str],
    verbose: bool,
    title: str,
) -> list[Path]:
    base_path = Path(base_dir)
    if not base_path.exists() or not base_path.is_dir():
        logger.error("%s: 基础路径 %s 不存在或不是一个目录", title, base_path)
        raise ValueError(f"基础路径 {base_path} 不存在或不是一个目录")

    if patterns is None or len(patterns) == 0:
        logger.error("%s: 未指定扫描模式 'patterns'", title)
        raise ValueError("未指定扫描模式")

    if extensions is None or len(extensions) == 0:
        logger.error("%s: 未指定文件后缀 'extensions'", title)
        raise ValueError("未指定文件后缀")

    # 在这里将 patterns 拆分为 已经是文件的 , 和需要 glob 的
    matched_files: list[Path] = []
    glob_patterns: list[str] = []

    for p in patterns:
        if p is not None:
            pp = Path(p)
            if pp.exists() and pp.is_file():
                if verbose:
                    logger.debug("直接命中文件: %s with pattern: %s", base_path, p)
                matched_files.append(pp)
                continue
        glob_patterns.append(p)

    # 创建一个包含手动指定 ignore_dirs 的 pathspec 规则列表
    ignore_patterns = ignore_dirs[:]  # 复制 ignore_dirs 列表

    # 尝试读取 .gitignore 文件并添加到忽略规则中
    gitignore_path = base_path / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, encoding="utf-8") as f:
            gitignore_content = f.read()
        # 过滤掉空行和注释行
        gitignore_patterns = [
            line.strip()
            for line in gitignore_content.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        ignore_patterns.extend(gitignore_patterns)

    # 使用 pathspec 创建忽略规则
    ignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)

    for pattern, ext in itertools.product(glob_patterns, extensions):
        if not pattern.endswith("/"):
            pattern += "/"
        glob_pattern_str = f"{pattern}**/*.{ext}" if pattern else f"**/*.{ext}"
        if verbose:
            logger.debug(
                "正在扫描路径: %s with pattern: %s", base_path, glob_pattern_str
            )
        for file_path in base_path.glob(glob_pattern_str):
            if file_path.is_file():
                # 计算相对于 base_path 的路径用于匹配忽略规则
                relative_path = file_path.relative_to(base_path)

                # 检查是否匹配忽略规则
                if not ignore_spec.match_file(str(relative_path)):
                    matched_files.append(relative_path)
                    logger.debug("匹配的文件: %s", relative_path)

    logger.info("总匹配文件数: %d", len(matched_files))
    return matched_files


def _prepare_temp_directory(matched_files: list[Path], base_dir: Path) -> Path:
    """将扫描命中的文件复制到临时目录，保持相对目录结构。

    Returns:
        临时目录的 Path。
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="pysample_"))
    base_resolved = base_dir.resolve()

    for f in matched_files:
        # 解析为绝对路径
        abs_f = f if f.is_absolute() else (base_resolved / f).resolve()

        # 尝试获取相对于 base_dir 的相对路径
        try:
            rel = abs_f.relative_to(base_resolved)
        except ValueError:
            # 文件在 base_dir 外部时，回退到仅用文件名
            rel = Path(abs_f.name)

        dest = temp_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_f, dest)
        logger.debug("暂存文件: %s -> %s", abs_f, dest)

    return temp_dir


def _write_extractor_config(
    temp_dir: Path, output_file: Path, group: dict[str, Any]
) -> Path:
    """生成 copyright-code-extractor 所需的 .copyright-extractor.json 文件。

    Returns:
        配置文件的 Path。
    """
    max_lines = group.get("maxLines", 0)
    config: dict[str, Any] = {
        "project_root": str(temp_dir),
        "output_file": str(output_file.resolve()),
        "software_name": group.get("title", "未命名文档"),
        "software_version": group.get("version", "V1.0"),
    }

    if max_lines > 0:
        config["lines_to_extract"] = max_lines
    else:
        config["extract_all"] = True

    config_path = temp_dir / ".copyright-extractor.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    logger.debug("已生成配置文件: %s", config_path)
    return config_path


def generate(verbose: bool) -> None:
    """遍历配置中的 group，扫描源码并委托 copyright-code-extractor 生成 DOCX。"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("详细日志已启用")
    else:
        logging.getLogger().setLevel(logging.INFO)

    config = read_config(CONFIG_PATH)

    for i, group in enumerate(config.get("group", [])):
        if verbose:
            logger.debug("处理第 %d 个组 %s", i + 1, group.get("title", "(未命名)"))

        base_dir = group.get("cwd", "")
        patterns = group.get("patterns", ["**"])
        extensions = group.get("extensions", [])
        ignore_dirs = group.get("ignore", [])
        title = group.get("title", "未命名文档")
        version = group.get("version", "1.0")

        matched_files = scan_files(
            base_dir,
            patterns,
            extensions,
            ignore_dirs,
            title=title,
            verbose=verbose,
        )
        logger.info("文件扫描完成，共 %d 个文件", len(matched_files))

        if not matched_files:
            logger.warning("%s: 未匹配到任何文件，跳过", title)
            continue

        output_dir = Path("./.bring-it/sample")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{title}_{version}.docx"

        base_path = Path(base_dir).resolve()

        # 暂存命中文件到临时目录（保留目录结构），以便 copyright-code-extractor
        # 能通过目录扫描方式处理（该工具不支持传入文件列表）
        temp_dir = _prepare_temp_directory(matched_files, base_path)

        try:
            # 生成 copyright-code-extractor 配置文件
            config_file = _write_extractor_config(temp_dir, output_file, group)

            # 通过子进程委托给 copyright-code-extractor（GPL-3.0）。
            # 使用 sys.executable -m 确保在任何 uvx / uv tool / pip 等
            # 安装方式下都能找到正确的解释器环境中的包。
            cmd = [
                sys.executable,
                "-m",
                "copyright_code_extractor.cli",
                str(temp_dir),
                "-c",
                str(config_file),
            ]
            logger.info("正在调用 copyright-code-extractor...")
            logger.debug("命令: %s", " ".join(cmd))

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(
                    "copyright-code-extractor 执行失败 (exit code %d):\n%s",
                    result.returncode,
                    result.stderr,
                )
                raise RuntimeError(f"copyright-code-extractor failed: {result.stderr}")

            if result.stdout:
                logger.info("%s", result.stdout.strip())

            logger.info("DOCX 文件已生成: %s", output_file)

        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug("已清理临时目录: %s", temp_dir)


def detect_languages(base_dir: str = ".") -> tuple[list[str], list[str]]:
    """扫描项目中常见源码格式，返回 (检测到的语言名列表, 去重扩展名列表)。

    判定为「已检测到」的条件：某语言的文件数 >= 2 或 总字节数 >= 1024 (1kB)。
    """
    base_path = Path(base_dir)
    if not base_path.exists() or not base_path.is_dir():
        return [], []

    # 扩展名 -> 语言名 反向映射
    ext_to_lang: dict[str, str] = {}
    for lang, exts in LANGUAGE_MAP.items():
        for ext in exts:
            ext_to_lang[ext] = lang

    lang_count: dict[str, int] = {}
    lang_size: dict[str, int] = {}

    for root, dirs, files in os.walk(base_path):
        # 原地修剪，跳过垃圾/产物目录以加快遍历
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            lang = ext_to_lang.get(ext)
            if lang is None:
                continue
            lang_count[lang] = lang_count.get(lang, 0) + 1
            with contextlib.suppress(OSError):
                lang_size[lang] = (
                    lang_size.get(lang, 0) + (base_path / root / fname).stat().st_size
                )

    detected_langs: list[str] = []
    detected_exts: list[str] = []
    for lang, exts in LANGUAGE_MAP.items():
        count = lang_count.get(lang, 0)
        size = lang_size.get(lang, 0)
        if count >= 2 or size >= 1024:
            detected_langs.append(lang)
            for ext in exts:
                if ext not in detected_exts:
                    detected_exts.append(ext)

    logger.info(
        "自动探测到 %d 种语言: %s",
        len(detected_langs),
        ", ".join(detected_langs) or "(无)",
    )
    return detected_langs, detected_exts


def run_init() -> None:
    """交互式收集信息并写出 .bring-it/sample.config.json。"""
    logger.info("开始初始化 pysample 配置...")

    _, detected_exts = detect_languages(".")

    title = typer.prompt("软件名称 (title)", default=Path.cwd().name)
    version = typer.prompt("软件版本 (version)", default="V1.0")

    if detected_exts:
        logger.info("自动探测到的源码扩展名: %s", ", ".join(detected_exts))
        use_detected = typer.confirm("是否使用上述自动探测的扩展名？", default=True)
        extensions = list(detected_exts) if use_detected else []
    else:
        logger.warning("未自动探测到任何源码，请手动补充扩展名。")
        extensions = []

    extra = typer.prompt("额外的文件后缀（逗号分隔，可留空）", default="").strip()
    for e in extra.split(","):
        e = e.strip().lstrip(".").lower()
        if e and e not in extensions:
            extensions.append(e)

    if not extensions:
        logger.warning("未指定任何扩展名，初始化后将无法扫描到文件。")

    cwd = typer.prompt("基准目录 (cwd)", default=".")

    ignore_input = typer.prompt(
        "忽略目录（逗号分隔，可留空，.gitignore 已自动生效）",
        default="",
    ).strip()
    ignore = [d.strip() for d in ignore_input.split(",") if d.strip()]

    config: dict[str, Any] = {
        "group": [
            {
                "cwd": cwd,
                "patterns": ["**"],
                "extensions": extensions,
                "ignore": ignore,
                "title": title,
                "version": version,
            }
        ]
    }

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    logger.info("已生成配置文件: %s", CONFIG_PATH.resolve())


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", help="启用详细日志输出"),
) -> None:
    """生成软件著作权源代码文档（bring-it/sample 兼容）。

    若未发现 .bring-it/sample.config.json 会交互式提示初始化。
    """
    # 有子命令（如 init）时交给子命令自行处理，避免重复执行文档生成
    if ctx.invoked_subcommand is not None:
        return

    if not CONFIG_PATH.exists():
        if typer.confirm(
            "未发现 .bring-it/sample.config.json，是否现在初始化？(Y/n)",
            default=True,
        ):
            run_init()
        else:
            logger.error(
                "未初始化配置文件，无法继续生成文档。可运行 `pysample init` 进行初始化。"
            )
            raise typer.Exit(code=1)

    generate(verbose)


@app.command()
def init() -> None:
    """交互式初始化/重新初始化 .bring-it/sample.config.json。"""
    if CONFIG_PATH.exists() and not typer.confirm(
        "已存在 .bring-it/sample.config.json，是否重新初始化？(y/N)",
        default=False,
    ):
        logger.info("已取消重新初始化，未做任何改动。")
        raise typer.Exit()
    run_init()


if __name__ == "__main__":
    app()
