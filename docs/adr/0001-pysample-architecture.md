# ADR 0001: pysample 架构设计

## 元数据

- **日期**: 2026-07-16
- **状态**: 已接受
- **作者**: Xiaoyu Guo

## 背景

pysample 是一个生成软件著作权源代码文档的 CLI 工具。它读取 JSON 配置文件，根据指定的模式扫描项目中的源代码文件，然后将文件内容整理输出为 DOCX 格式的文档。

该工具的设计目标是与 [bring-it/sample](https://github.com/Airkro/bring-it/tree/master/packages/sample) 配置文件兼容，用户可以复用现有的配置。

## 决策

### 1. 单文件模块结构

**决策**: 所有代码放在一个 `main.py` 文件中（387 行），包入口直接指向 `main:main`。

**理由**:
- 代码量小，不到 400 行，拆分多个文件会增加导航成本却没有足够的收益
- 用户通过 `uvx` 或 `uv tool install` 直接从 GitHub 安装，单文件降低了分发的复杂度
- CLI 工具天然是"完成一件事"的模式，过早拆分会制造浅模块（shallow modules）

**权衡**: 随着功能增长（例如加入 Docker 运行模式、支持更多输出格式），单文件将变得难以维护。当代码超过 ~800 行或需要为不同输出格式引入 adapter 时，应重新评估。

### 2. Click 作为 CLI 框架

**决策**: 使用 Click 作为命令行参数解析框架，目前仅有 `--verbose` 一个选项。

**理由**:
- Click 是 Python CLI 工具的事实标准，生态成熟
- 接口简洁 —— 一个 `@click.command()` 装饰器 + `@click.option()` 即完成定义
- 未来扩展子命令（如 `pysample generate`、`pysample init`）时有清晰的升级路径

### 3. 配置文件驱动而非命令行参数驱动

**决策**: 所有业务参数（文件模式、输出标题、版本等）通过 JSON 配置文件 `.bring-it/sample.config.json` 传入，CLI 仅接受 `--verbose` 标志。

**理由**:
- 软件著作权文档的参数数量多（多组文件集合、标题、版本、公司名等），全部通过 CLI 参数传入会非常冗长
- 配置文件可版本控制，与项目共存，可在 CI 中使用
- 与 bring-it/sample 生态兼容，降低用户迁移成本

**权衡**: 配置文件路径硬编码为 `.bring-it/sample.config.json`，缺乏灵活性。后续可能需要支持 `--config` 选项。

### 4. python-docx 直接操作 OOXML

**决策**: 使用 python-docx 库直接操作底层 OOXML 元素（如 `OxmlElement`、`qn` 命名空间）来实现页眉/页脚的页码字段。

**理由**:
- python-docx 的高层 API 不直接支持插入 Word 域代码（如 `PAGE`、`NUMPAGES`），必须下降到 OOXML 层
- 这是 python-docx 的已知限制，直接操作 OOXML 是社区推荐的做法

**权衡**: OOXML 操作代码（`add_header_footer` 函数，约 90 行）是文件中复杂度最高的模块。它暴露了底层 XML 细节，如果未来需要支持更多 Word 域或样式，应考虑提取为一个独立的 Word 文档模板模块。

### 5. pathspec + .gitignore 集成

**决策**: 使用 `pathspec` 库解析 `.gitignore` 规则，将其与用户配置的 `ignore` 列表合并，在扫描文件时统一应用过滤。

**理由**:
- 软件著作权文档需要排除 `node_modules`、`dist` 等构建产物，这些通常已在 `.gitignore` 中定义
- 自动尊重项目的 `.gitignore` 减少了配置重复
- `pathspec` 使用 `gitwildmatch` 规则，与 Git 行为完全一致

### 6. 无抽象层（No Internal Seams）

**决策**: 当前代码中没有定义任何抽象接口（interface/abstract class）。所有函数直接相互调用，`add_content_to_docx()` 是最顶层编排函数，按顺序调用 `set_font()` → `add_header_footer()` → `add_title_page()` → `add_main_content()`。

**理由**:
- 目前只有一个输出目标（DOCX），只有一个文件来源（本地文件系统），缺少可变性（variation）的驱动
- "一个 adapter 意味着假设的 seam；两个 adapter 才意味着真实的 seam" —— 当前不需要引入 seam

**风险**: 以下场景出现时，缺乏 seam 将导致重构成本:
- 需要支持 PDF 或其他输出格式
- 需要从非本地文件系统读取源码（如 Git 仓库）
- 需要为模块编写单元测试（当前无测试）

### 7. 无测试

**决策**: 项目当前不包含任何测试代码。

**理由**:
- 项目处于早期阶段，功能仍在快速迭代
- 外部依赖（文件系统、DOCX 生成）使测试设置成本较高

**风险**: 这是一个技术债务。`scan_files()` 和 `remove_consecutive_blank_lines()` 是纯逻辑函数，已有清晰的接口，测试成本低。其他函数依赖 `python-docx` 的 `Document` 对象，测试需要内存中的 Document fixture。

## 模块深度分析

### 深模块 (Deep Modules)

```
┌─────────────────────────────────┐
│  scan_files()                   │  ← 5 个参数
├─────────────────────────────────┤
│  - 区分直接文件与 glob 模式       │
│  - .gitignore 解析与合并         │
│  - pathspec 规则匹配             │
│  - 相对路径计算                  │
│  - verbose 日志                 │
│  - 错误处理（base_dir 不存在等）  │
└─────────────────────────────────┘
```

`scan_files()` 是最深的模块：接口只有 5 个参数 + 1 个返回值 `list[Path]`，但内部封装了路径解析、模式匹配、.gitignore 集成和错误处理，为调用者提供高杠杆。

### 中等深度模块

- **`add_header_footer()`**: OOXML 域代码的复杂操作隐藏在简单的 `(doc, title, version)` 接口后，但 OOXML 细节泄漏到了调用方对 docx 库的认知要求中。
- **`remove_consecutive_blank_lines()`**: 极简接口（`str → str`），内部处理空白行合并和 tab 替换。

### 浅模块 (Shallow Modules)

- **`add_content_to_docx()`**: 纯编排函数，按固定顺序调用 4 个子函数，无分支逻辑。接口参数 6 个，几乎等于其实现。这是典型的"浅编排器"——它将复杂性委托给子模块，自身没有增加行为深度。
- **`read_config()`**: `Path → dict` 的薄封装，仅增加 try/except 日志。可以内联到 `main()` 中。

## 未来演进方向

| 触发器 | 建议动作 |
|--------|---------|
| 需要支持 PDF 输出 | 引入 `DocumentGenerator` 接口，将 DOCX 逻辑移到 adapter |
| 需要单元测试 | 将 `scan_files` 和文本处理函数提取到独立模块，为 `Document` 创建 fixture |
| 代码超过 800 行 | 按职责拆分: `config.py` / `scanner.py` / `docx_writer.py` / `cli.py` |
| 需要自定义配置路径 | 添加 `--config` CLI 选项 |
| Docker 运行模式完成 | 需要验证 Dockerfile（当前依赖 pip 而非 uv，且 COPY 顺序需要优化以利用缓存） |

## 术语对齐

| 本项目用语 | codebase-design 术语 |
|-----------|---------------------|
| `main.py` 中的每个函数 | **模块 (Module)** |
| 函数签名 + 行为约定 | **接口 (Interface)** |
| 函数体 | **实现 (Implementation)** |
| 配置文件、CLI 参数 | 外部 **seam** |
| python-docx Document | 外部依赖，非 adapter（只有一个使用者） |
