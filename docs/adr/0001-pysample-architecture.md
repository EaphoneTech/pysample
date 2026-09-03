# ADR 0001: pysample 架构设计

## 元数据

- **日期**: 2026-07-16
- **状态**: 已接受
- **作者**: Xiaoyu Guo
- **更新**: 2026-07-16 — 重构为委托架构，以后端生成委托给 copyright-code-extractor
- **更新**: 2026-09-03 — 补充决策 9/10（init 子命令、双后端）；新增决策 11（Docker 运行模式）
- **更新**: 2026-09-03 — 新增决策 12（双变体 Docker CI：Dockerfile 参数化 + matrix 发布 tag 体系）

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

**决策**: 使用 Typer 作为命令行参数解析框架，运行时依赖为 `typer-slim`
（PyPI 上完整 Typer 的别名，代码仍 `import typer`）。目前有 `--verbose` 选项及 `init` 子命令。

**理由**:
- copyright-code-extractor 已经依赖 `typer>=0.16.0` + `rich>=14.0.0`，
  使用 Typer 不引入新的传递依赖，反而减少了项目自己的依赖列表
- 2026-09 将依赖从 `typer` 迁移为 `typer-slim`：仅改依赖名，行为不变；
  typer-slim 自 Typer 0.22 起仅为完整 Typer 的别名，rich 仍由 copyright-code-extractor 间接引入，属预期
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

### 9. init 子命令与交互式初始化

**决策**: 新增 `pysample init` 子命令，以及裸 `pysample` 的无配置自动提示，交互式生成
`.bring-it/sample.config.json`。

**理由**:
- 降低上手成本：用户无需手工编写 JSON 配置即可开始使用
- 复用 Typer 的 `typer.prompt` / `typer.confirm` 实现交互，沿用既有 CLI 框架
- `detect_languages()` 自动探测项目中的常见源码格式（某语言文件数 ≥2 或 总字节 ≥1kB 即视为检测到），
  自动预填 `extensions`，减少手工配置
- 命令分发采用 `app.callback(invoke_without_command=True)` + `ctx.invoked_subcommand` 判断：
  裸 `pysample` 执行文档生成（无配置时提示初始化，默认 Y），`pysample init` 处理初始化
  （已存在配置时提示重新初始化，默认 N）；两条路径共用 `run_init()`，避免逻辑重复

**权衡**:
- 初始化仅生成单 group 的简化配置（`patterns=["**/*"]`，title/version/cwd/ignore 由用户确认），
  复杂多 group 场景仍需手工编辑
- 自动探测为启发式，阈值（2 文件 / 1kB）用于避免极小样本误判；最终扩展名由用户确认并可追加

### 10. 双后端与全局 `--backend` 选项

**决策**: 将 develop 分支（内置 python-docx 自生成）与 feat/use-copyright-code-extractor 分支（子进程委托 copyright-code-extractor）两种后端统一为一个全局 CLI 选项 `--backend {builtin,external}`，默认 `builtin`。

- `builtin`：进程内用 python-docx 生成，默认安装仅含 MIT/BSD 依赖（pathspec、typer-slim、python-docx），支持 `company` / `lineNumber` / `maxLines`，输出含标题页与页眉页脚。
- `external`：复用既有子进程委托 copyright-code-extractor 的逻辑（GPL-3.0 聚合合规），输出风格为去注释、每页固定行数、页眉仅软件名 + 版本。

**理由**:
- develop 与 feat 分支本质是「后端生成策略」不同，统一为选项后一份工具同时支持两种输出风格与依赖策略，避免长期维护两份分支。
- 默认 `builtin` 使默认安装保持 MIT/BSD 纯净：GPL 组件 copyright-code-extractor 作为可选依赖组 `external`（PEP 621 `[project.optional-dependencies]`）提供，仅 `uv tool install "pysample[external]"` 时才引入，默认 `uv tool install pysample` 不含任何 GPL 依赖。
- `external` 后端下若 group 配置了 `company` / `lineNumber`，工具输出 warning 并忽略，保持字段语义清晰。
- 仅全局 `--backend`（不按 group），保持实现简单；CLI 框架统一为 Typer + 标准库 logging，不引入 develop 分支的 click/loguru。

**权衡**:
- 内置 python-docx 生成与 external 输出风格不同（标题页、行号、注释剥离等），用户需按需求选择。
- `external` 缺失依赖时，`_generate_external_doc()` 用 `importlib.util.find_spec` 预判并给出安装指引，避免晦涩异常。

### 11. Docker 运行模式（容器化分发）

**决策**: 新增 `Dockerfile`（多阶段构建，参考 `biggates/deplowly` 的 `Dockerfile` 模式），支持以容器方式分发与运行 pysample。

- **builder 阶段**：`ghcr.io/astral-sh/uv:python3.12-trixie-slim`（自带 uv），设 `UV_COMPILE_BYTECODE=1` + `UV_LINK_MODE=copy`（copy 保证 venv 可被 COPY 到 runner）。先 `COPY pyproject.toml uv.lock` 后 `uv sync --frozen --no-install-project --no-dev` 缓存依赖层，再 `COPY . .` 并 `uv sync --frozen --no-dev [--extra external]` 安装项目（hatchling 打包 `main.py`，生成 console script `pysample`，decision 3 的包入口）。
- **runner 阶段**：`python:3.12-slim-trixie`，`COPY --from=builder /app /app`，`PATH` 注入 `.venv/bin`，`ENTRYPOINT ["pysample"]`。builder/runner 同用 trixie 以保证 venv 二进制兼容。
- `ARG VARIANT=builtin`（默认）参数化 optional 依赖组：builtin（`uv sync --no-dev`，仅 MIT/BSD）与
  external（`uv sync --no-dev --extra external`，额外引入 GPL-3.0 的 copyright-code-extractor）共用单 Dockerfile，变体差异仅一行；
  本地构建 `docker build .` 默认即 builtin，行为不变。
- 需要 external 后端时，镜像构建阶段 `docker build . --build-arg VARIANT=external`，运行时再叠加 `--backend external`。
- `uv sync --frozen` 强制使用已提交的 `uv.lock`，构建可复现（lock 与 pyproject 不一致则构建失败，倒逼提交 lock）。PyPI 镜像由 `pyproject.toml` 的 `tool.uv.index`（aliyun，default）自动生效，无需在 Dockerfile 写 `--index-url`。
- 新增 `.dockerignore` 排除 `.git` / `.github` / `docs` / `*.md` / `.codebuddy`，避免无关文件进入构建上下文与镜像。

**理由**:
- 容器分发消除了不同主机 Python 版本与系统字体的差异（标题页 Microsoft YaHei 等输出依赖本地字体，固定基础镜像保证输出一致），契合软著文档「格式稳定」的诉求。
- 项目已是 uv 生态（`pyproject.toml` + `uv.lock`，CI 用 uv），改用 uv 多阶段与现有一致，且依赖层缓存 + `--frozen` 可复现优于裸 `pip install`。
- 默认 builtin 与全局 `--backend` 选项天然对齐，Docker 层无需额外分支或环境变量。
- `ENTRYPOINT` 复用既有的 console script，Docker 仅作为**部署 seam（聚合）**，不重写入口契约。

**权衡**:
- 默认镜像不含 external；需 external 的用户必须自行构建带 `VARIANT=external` 的变体，否则运行 `--backend external`
  会因缺失依赖而由 decision 10 的 `find_spec` 守卫报错（行为一致，但镜像内报错体验弱于本地）。
- 容器与 `uvx` / `uv tool install` 是两条并列分发路径，需同步维护依赖变更（含 `uv.lock` 随 pyproject 提交）。
- 基础镜像由 `python:3.13-slim` 改为 `python:3.12`（匹配 CI 与 `requires-python>=3.12`），且 builder/runner 统一 trixie；若后续需 3.13 须同步调整两边版本避免 venv 不兼容。

### 12. 双变体 Docker CI 与发布 tag 体系

**决策**: CI 拆分为两个作业（参考 `biggates/deplowly` 的 `ci.yml` 模式），文件为 `.github/workflows/ci.yml`，两个镜像变体推送到 `ghcr.io`（沿用既有 `GITHUB_TOKEN` 凭据）：

- **`test` 作业（正常编译）**：在 `push`（develop / `v*` tag）、`pull_request`、`workflow_dispatch` 时运行 `ruff check .` + `python -m py_compile main.py`。pysample 为单文件工具、无 `src/`/`tests/`（decision 8 明确无测试），故不引入 `mypy`/`pytest` 以免误失败；仅做 lint 与语法编译校验。
- **`image` 作业（发布版本）**：`needs: test` 门禁，且 `if: startsWith(github.ref, 'refs/tags/v') || github.event_name == 'workflow_dispatch'` —— 即**仅推送 `v*` tag 时真正推送镜像**，`workflow_dispatch` 仅构建不推送（用于验证 Dockerfile）。
  - 通过 `strategy.matrix.variant: [builtin, external]` 双变体并行构建，变体差异由 `build-args: PIP_EXTRA=...` 传入（decision 11 的 `ARG`）。
  - 使用 `docker/metadata-action@v6` 生成 tag 体系：
    - 标准版：`latest` + `v{version}` + `v{major}.{minor}` + `sha-<hash>`（如 `pysample:latest`、`pysample:v1.0.0`、`pysample:v1.0`）
    - external 版：经 `flavor: prefix=external-` 统一加前缀 → `external-latest`、`external-v1.0.0`、`external-v1.0`、`external-sha-<hash>`
  - `push: ${{ startsWith(github.ref, 'refs/tags/v') }}` —— 只有 tag 事件才真正推送，`workflow_dispatch`/非 tag 仅本地构建校验。
- `IMAGE_NAME` 经 `${GITHUB_REPOSITORY,,}` 小写化（github.repository 含大写 `EaphoneTech`，ghcr.io 要求镜像名全小写），修复历史大写推送失败隐患。
- 多平台 `linux/amd64,linux/arm64`（启用 `setup-qemu-action` 支持 arm 模拟）构建，并启用 `cache-from/to: type=gha` 复用 GitHub Actions 缓存。

**理由**:
- 发布版本才用 metadata-action 生成 `latest` + `v{version}`（semver 解析 `v*` tag），保证 `latest` 始终指向受控发布而非任意提交；正常编译（push/PR）仅跑 `test` 作业，不构建、不污染 `latest`。
- `external-` 前缀将 GPL-3.0 聚合依赖的镜像与纯净 MIT/BSD 镜像在 tag 维度彻底分离，与 decision 2/10 的「默认纯净、external 可选」边界一致；用户 `docker run ghcr.io/eaphontech/pysample:external-latest --backend external` 明确知道自己拉取了含 GPL 的变体。
- 双变体共用单 `Dockerfile`（`ARG PIP_EXTRA`）+ matrix 并行，避免复制维护成本（DRY），总耗时≈单变体。

**权衡**:
- `latest` 仅在 `v*` tag 发布时更新；日常 develop 推送只验证构建（不推送），如需在 develop 上验证最新镜像可用 `workflow_dispatch` 手动触发（但默认不推送，避免污染 `latest`）。
- 正常编译路径不推送任何 tag，故无 sha 溯源镜像；溯源依赖 Release 的 `sha-<hash>` tag。

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
| 需要 PDF 输出 | 在 `.copyright-extractor.json` 中启用 `export_pdf`（external 后端） |
| 需要单元测试 | 将 `scan_files` 提取到独立模块，mock `subprocess.run` |
| 代码超过 800 行 | 按职责拆分: `config.py` / `scanner.py` / `adaptor.py` / `cli.py` |
| 需要自定义配置路径 | 添加 `--config` CLI 选项 |
| Docker 运行模式 | 已实现（decision 11）：`python:3.13-slim` + ENTRYPOINT `pysample`；默认 builtin，需 external 时构建带 `[external]` 的变体 |
| 内置 python-docx 后端 | 已落地（decision 10），默认 `builtin` 即进程内生成，无需从历史恢复 |

## 术语对齐

| 本项目用语 | codebase-design 术语 |
|-----------|---------------------|
| `main.py` 中的每个函数 | **模块 (Module)** |
| 函数签名 + 行为约定 | **接口 (Interface)** |
| 函数体 | **实现 (Implementation)** |
| 配置文件、CLI 参数 | 外部 **seam** |
| copyright-code-extractor subprocess | 外部工具 / aggregate component |
| 暂存目录 `.copyright-extractor.json` | 跨进程通信接口 |
| `Dockerfile` + `ENTRYPOINT pysample` | 部署 seam（聚合）：镜像内复用 console script，不重写入口契约 |
