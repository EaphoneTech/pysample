# pysample

生成软件著作权文档的 python 工具。

pysample 读取 [@bring-it/sample](https://github.com/Airkro/bring-it/tree/master/packages/sample) 的配置文件，
扫描指定的源代码文件，生成 DOCX 格式的软件著作权源代码文档。

文档生成支持两种后端，可通过全局 `--backend` 选项切换：

- `builtin`（默认）：使用内置的 [python-docx](https://github.com/python-openxml/python-docx) 在进程内生成，纯 MIT/BSD 依赖，支持 `company` / `lineNumber` / `maxLines` 等字段，输出含标题页与页眉页脚。
- `external`：通过**子进程聚合方式**委托 [copyright-code-extractor](https://github.com/kirklin/copyright-code-extractor)（GPL-3.0）生成，输出风格为去注释、每页固定行数、页眉仅软件名 + 版本。

## 许可证

pysample 自身以 **MIT License** 分发。

默认安装（`uv tool install pysample`）仅包含 MIT/BSD 依赖（pathspec、typer-slim、python-docx），**不含任何 GPL 组件**。

仅当使用 `external` 后端时，pysample 才以**子进程聚合方式 (subprocess aggregation)** 调用 [copyright-code-extractor](https://github.com/kirklin/copyright-code-extractor) (GPL-3.0)：不 import / 不链接该 GPL 组件的任何模块。根据 FSF/GPL FAQ 关于「Mere Aggregation」的说明，此方式构成聚合关系而非衍生作品，pysample 不受 GPL 传染性条款约束。该 GPL 依赖通过可选依赖组 `external` 提供（`uv tool install "pysample[external]"`），默认安装不会引入它。

详见 [THIRD-PARTY-LICENSES.md](./THIRD-PARTY-LICENSES.md) 及
[licenses/GPL-3.0.txt](./licenses/GPL-3.0.txt)。

## 配置文件

配置文件路径为 `.bring-it/sample.config.json`，格式与 bring-it/sample 兼容。
例如:

```jsonc title=".bring-it/sample.config.json"
{
  "group": [
    {
      "cwd": ".",
      "prologue": ["prologue/*"],
      "patterns": ["**/*"],
      "epilogue": ["epilogue/*"],
      "extensions": ["js", "ts", "..."],
      "ignore": ["dist"],
      "title": "示例软件名称",
      "version": "v1.0",
      "company": "Cyberdyne Systems Corporation",
      "maxLines": 2000
    }
  ]
}
```

简单来说, 需要在 `patterns` 中指定要包括的文件, 在 `extensions` 中指定要包括的文件后缀名,
并填写 `title`、`version` 等信息。

> **注意**:
> - `company` / `lineNumber` 仅在 `builtin` 后端生效；使用 `external` 后端时这两个字段会被忽略（工具会输出警告）。
> - `prologue` / `epilogue` — 保持忽略。

## 快速初始化 (init)

如果不想手工编写 `.bring-it/sample.config.json`，可以用 `init` 命令交互式生成：

```bash
$ pysample init
```

`init` 会：

1. 自动探测项目中的常见源码格式（某语言文件数 ≥ 2 或 总字节 ≥ 1kB 即视为检测到），预填 `extensions`；
2. 依次询问软件名称 (title)、版本 (version)、是否采用自动探测的扩展名、额外扩展名、基准目录 (cwd) 与忽略目录 (ignore)；
3. 写出 `.bring-it/sample.config.json`（单个 group，`patterns` 默认为 `["**"]`）。

此外，直接运行 `pysample`（不带子命令）且未发现配置文件时，会交互式提示是否初始化（默认 Y）；
若已存在配置文件则直接开始生成文档。`pysample init` 在配置已存在时会提示是否重新初始化（默认 N）。

> 注：本项目依赖已从 `typer` 迁移为 `typer-slim`（仅改依赖名，代码仍 `import typer`，运行行为不变）。

## 后端选项 (`--backend`)

pysample 支持两种文档生成后端，通过顶层 `--backend` 选项切换（对所有 group 统一生效）：

- `--backend builtin`（默认）：内置 python-docx 生成，支持 `company` / `lineNumber` / `maxLines`，输出含标题页与页眉页脚，默认安装即可使用。
- `--backend external`：子进程委托 copyright-code-extractor 生成，输出为去注释、每页固定行数、页眉仅软件名 + 版本；需安装 `external` 可选依赖组（见下）。

例如：

```bash
$ pysample --backend external
```

## 输出

对于配置文件中的每一个 group, 会在 `.bring-it/sample/` 目录下生成 `{title}_{version}.docx`。

- `builtin` 后端：含标题页（软件名称、版本、公司、源代码字样）、窄边距页眉页脚（软件名 + 版本 + 页码）、正文按 `maxLines` 限制并可选行号。
- `external` 后端：由 copyright-code-extractor 生成，自动剥离注释与空行、每页固定行数、页眉居中软件名称与版本号。

## 用法

### 使用 uvx 直接运行（无需本地安装）

初次使用只需要安装 uv 即可。uvx 会自动拉取 python 和项目代码并运行，适合临时 / 一次性使用。

```bash
# builtin 后端（默认，纯 MIT，无 GPL 依赖）
$ uvx --from git+https://github.com/EaphoneTech/pysample@feat/use-copyright-code-extractor pysample

# 或使用 external 后端（额外安装 GPL 的 copyright-code-extractor 可选依赖）
$ uvx --from "git+https://github.com/EaphoneTech/pysample@feat/use-copyright-code-extractor#egg=pysample[external]" pysample --backend external
```

### 使用 uv tool 安装

将 pysample 作为本机应用程序安装，之后可直接用 `pysample` 命令运行。

```bash
# builtin 后端（默认，纯 MIT，无 GPL 依赖）
$ uv tool install --from "git+https://github.com/EaphoneTech/pysample@feat/use-copyright-code-extractor" pysample

# 或使用 external 后端（额外安装 GPL 的 copyright-code-extractor 可选依赖）
$ uv tool install --from "git+https://github.com/EaphoneTech/pysample@feat/use-copyright-code-extractor" "pysample[external]"
```

安装后就可以直接用 `pysample` 来运行了；使用 `uv tool upgrade pysample` 可以升级。

> 默认后端为 `builtin`（纯 MIT，无需 GPL 依赖）。仅当需要使用 `external` 后端时才通过上面的 `[external]` extra 安装 copyright-code-extractor。

### 使用 docker

镜像托管于 GitHub Container Registry，提供两个变体标签，分别对应两种后端：

- `latest`（默认，纯 MIT/BSD 依赖，无 GPL 组件）
- `external-latest`（额外聚合 GPL-3.0 的 copyright-code-extractor）

镜像的 `ENTRYPOINT` 为 `pysample`，因此 `docker run` 后接的参数会原样传给 `pysample`。
使用时把当前工作目录挂载进容器（`-v "$PWD":/work -w /work`），
工具会读取其中的 `.bring-it/sample.config.json` 并在 `.bring-it/sample/` 下生成 DOCX。

```bash
# builtin 后端（默认，纯 MIT，无 GPL 依赖）
$ docker pull ghcr.io/eaphonetech/pysample:latest
$ docker run --rm -v "$PWD":/work -w /work ghcr.io/eaphonetech/pysample:latest

# external 后端（GPL-3.0 聚合依赖，需显式指定 --backend external）
$ docker pull ghcr.io/eaphonetech/pysample:external-latest
$ docker run --rm -v "$PWD":/work -w /work ghcr.io/eaphonetech/pysample:external-latest --backend external
```

> **注意**：`external` 镜像仅在使用 `--backend external` 时才会调用 copyright-code-extractor；
> 即便拉取了 `external-latest` 镜像，不加该参数仍走 `builtin` 生成逻辑。
> 两个变体同样遵循「Mere Aggregation」聚合关系，许可证说明见
> [THIRD-PARTY-LICENSES.md](./THIRD-PARTY-LICENSES.md)。
