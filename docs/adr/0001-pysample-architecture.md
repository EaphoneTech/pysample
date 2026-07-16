# ADR 0001: pysample 架构设计

## 元数据

- **日期**: 2026-07-16
- **状态**: 已接受
- **作者**: Xiaoyu Guo
- **更新**: 2026-07-16 — 重构为委托架构，以后端生成委托给 copyright-code-extractor

## 背景

pysample 是一个生成软件著作权源代码文档的 CLI 工具。它读取 JSON 配置文件，根据指定的模式
扫描项目中的源代码文件，然后将文件内容整理输出为 DOCX 格式的文档。

该工具的设计目标是与 [bring-it/sample](https://github.com/Airkro/bring-it/tree/master/packages/sample)
配置文件兼容，用户可以复用现有的配置。

## 决策

### 1. 委托架构：后端生成委托给 copyright-code-extractor

**决策**: 将 DOCX 生成的后半部分完全委托给 [copyright-code-extractor](https://github.com/kirklin/copyright-code-extractor)
(GPL-3.0)。pysample 保留配置文件读取 (`read_config`) 和文件扫描 (`scan_files`) 作为前置适配层，
通过以下流程完成整个工作流：

1. 读取 `.bring-it/sample.config.json`
2. 对每个 group 调用 `scan_files()` 获取精确的文件列表（支持 bring-it `patterns` 的精确文件匹配）
3. 将命中文件复制到临时目录（保留相对目录结构）
4. 生成 `.copyright-extractor.json` 配置文件
5. 子进程调用 `sys.executable -m copyright_code_extractor.cli <temp_dir> -c <config>`
6. 清理临时目录

**理由**:
- copyright-code-extractor 已经实现了完整的 docx 生成能力（注释剥离、行数分页、页眉页脚、
  可选 PDF 导出），无需在 pysample 中重复实现
- pysample 的独特价值在于 bring-it 配置文件兼容和精确文件控制（`patterns` + `extensions` + `ignore`），
  这是 copyright-code-extractor 不具备的
- 子进程调用而非库导入，使 pysample 保持 MIT License（不 import / 不链接 GPL 代码）

**权衡**:
- 输出格式变更为 copyright-code-extractor 的风格（自动剥离注释、固定每页 50 行、页眉仅软件名+版本、
  不再有独立标题页、不再使用 Microsoft YaHei）
- bring-it `lineNumber` 字段废弃（external tool 不支持行号标注）
- bring-it `company` 字段不再出现在输出文档中
- 需要将命中文件复制到临时目录（软著场景文件量级小，可接受）

### 2. GPL 聚合合规（Mere Aggregation）

**决策**: pysample 以 **子进程聚合 (subprocess aggregation)** 方式调用 GPL-3.0 的 copyright-code-extractor。
具体措施：

1. **技术隔离**: 通过 `sys.executable -m copyright_code_extractor.cli` 以 fork/exec 方式启动独立进程。
   不 import / 不 import / 不链接 copyright-code-extractor 的任何模块，不与之运行于同一进程地址空间。
2. **声明**: `THIRD-PARTY-LICENSES.md` 声明聚合关系及合规依据（引 FSF/GPL FAQ「Mere Aggregation」+
   [catalog-sig 邮件](https://mail.python.org/pipermail/catalog-sig/2013-February/005022.html) 的 Vinay Sajip 结论）。
3. **附带 GPL 文本**: `licenses/GPL-3.0.txt` 包含 copyright-code-extractor 的 GPL-3.0 许可证全文。
4. **随包携带**: `pyproject.toml` 中声明 `license-files = ["licenses/*"]`，确保发布包包含 GPL 全文。

**理由**:
- GPL FAQ 明确：通过 fork/exec 和 pipe 通信的独立程序构成「聚合 (aggregate)」而非衍生作品，
  聚合中的 GPL 组件不会将 GPL 传染给聚合中的其他组件
- copyright-code-extractor 仅作为运行时依赖声明，由 uv/pip 在用户环境中单独安装，
  pysample 不分发其二进制文件
- 第三方许可声明是开源项目的最佳实践——诚实、透明地说明所有依赖的许可证状态

### 3. 单文件模块结构

**决策**: 所有代码放在一个 `main.py` 文件中，包入口直接指向 `main:main`。

**理由**:
- 代码量小（~200 行），拆分多个文件会增加导航成本却没有足够的收益
- 用户通过 `uvx` 或 `uv tool install` 直接从 GitHub 安装，单文件降低了分发的复杂度
- CLI 工具天然是"完成一件事"的模式，过早拆分会制造浅模块（shallow modules）

**权衡**: 随着功能增长（例如加入 Docker 运行模式、支持更多输出格式），单文件将变得难以维护。

### 4. Typer 作为 CLI 框架

**决策**: 使用 Typer 作为命令行参数解析框架，目前仅有 `--verbose` 一个选项。

**理由**:
- copyright-code-extractor 已经依赖 `typer>=0.16.0` + `rich>=14.0.0`，
  使用 Typer 不引入新的传递依赖，反而减少了项目自己的依赖列表
- Typer 基于 type hints 定义 CLI 接口，比 Click 的装饰器风格更现代
- Typer 实例可直接作为 `app` 入口点，支持 `typer.run()` 和子命令扩展

### 5. Python 内置 logging 作为日志库

**决策**: 使用 Python 标准库 `logging` 替代 `loguru` 作为日志输出。

**理由**:
- `logging` 是标准库，无需额外依赖，减少项目的依赖数量
- 项目日志需求简单（仅控制台输出 INFO/DEBUG 两个级别），不需要 loguru 的高级特性
  （自动着色、结构化日志、`@logger.catch` 等）
- 使用 `%(levelname)-8s | %(message)s` 格式模拟 loguru 的输出风格

**权衡**: 失去 loguru 的彩色输出和自动异常捕获，但控制了对外部依赖的需求。

### 6. 配置文件驱动而非命令行参数驱动

**决策**: 所有业务参数通过 JSON 配置文件 `.bring-it/sample.config.json` 传入，CLI 仅接受 `--verbose` 标志。

**理由**:
- 软件著作权文档的参数数量多（多组文件集合、标题、版本等），全部通过 CLI 参数传入会非常冗长
- 配置文件可版本控制，与项目共存，可在 CI 中使用
- 与 bring-it/sample 生态兼容，降低用户迁移成本

### 7. pathspec + .gitignore 集成

**决策**: 使用 `pathspec` 库解析 `.gitignore` 规则，将其与用户配置的 `ignore` 列表合并，
在扫描文件时统一应用过滤。

**理由**:
- 软件著作权文档需要排除 `node_modules`、`dist` 等构建产物，这些通常已在 `.gitignore` 中定义
- 自动尊重项目的 `.gitignore` 减少了配置重复
- `pathspec` 使用 `gitwildmatch` 规则，与 Git 行为完全一致

### 8. 无测试

**决策**: 项目当前不包含任何测试代码。

**理由**:
- 项目处于早期阶段，功能仍在快速迭代
- 外部依赖（文件系统、子进程调用）使测试设置成本较高

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

`scan_files()` 是最深的模块：接口只有 5 个参数 + 1 个返回值 `list[Path]`，
但内部封装了路径解析、模式匹配、.gitignore 集成和错误处理。

### 中等深度模块

- **`_prepare_temp_directory()`**: 将命中文件暂存到临时目录并保留相对目录结构的适配逻辑。
- **`_write_extractor_config()`**: bring-it 配置到 copyright-code-extractor 配置的翻译层。

### 浅模块 (Shallow Modules)

- **`read_config()`**: `Path → dict` 的薄封装，仅增加 try/except 日志。
- **`main()`**: 编排函数，按顺序调用子模块，将复杂性委托出去。

## 未来演进方向

| 触发器 | 建议动作 |
|--------|---------|
| 需要恢复自建 docx 生成 | 从 Git 历史恢复 python-docx 函数 |
| 需要 PDF 输出 | 在 `.copyright-extractor.json` 中启用 `export_pdf` |
| 需要单元测试 | 将 `scan_files` 提取到独立模块，mock `subprocess.run` |
| 代码超过 800 行 | 按职责拆分: `config.py` / `scanner.py` / `adaptor.py` / `cli.py` |
| 需要自定义配置路径 | 添加 `--config` CLI 选项 |
| Docker 运行模式完成 | 需更新 Dockerfile 以适配新的依赖关系 |

## 术语对齐

| 本项目用语 | codebase-design 术语 |
|-----------|---------------------|
| `main.py` 中的每个函数 | **模块 (Module)** |
| 函数签名 + 行为约定 | **接口 (Interface)** |
| 函数体 | **实现 (Implementation)** |
| 配置文件、CLI 参数 | 外部 **seam** |
| copyright-code-extractor subprocess | 外部工具 / aggregate component |
| 暂存目录 `.copyright-extractor.json` | 跨进程通信接口 |
