# pysample

生成软件著作权文档的 python 工具。

pysample 读取 [@bring-it/sample](https://github.com/Airkro/bring-it/tree/master/packages/sample) 的配置文件，
扫描指定的源代码文件，然后**委托** [copyright-code-extractor](https://github.com/kirklin/copyright-code-extractor)
（GPL-3.0）通过子进程生成 DOCX 格式的软件著作权源代码文档。

## 许可证

pysample 自身以 **MIT License** 分发。

pysample 将 [copyright-code-extractor](https://github.com/kirklin/copyright-code-extractor)
(GPL-3.0) 声明为运行时依赖，并以**子进程聚合方式 (subprocess aggregation)** 调用，
不 import / 不链接该 GPL 组件的任何模块。
根据 FSF/GPL FAQ 关于「Mere Aggregation」的说明，此方式构成聚合关系而非衍生作品，
pysample 不受 GPL 传染性条款约束，继续以 MIT License 分发。

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

> **注意**: 以下字段在此版本中已废弃或不再生效:
> - `lineNumber` — 不再输出行号（copyright-code-extractor 不支持行号标注）
> - `company` — 不再出现在输出文档中（copyright-code-extractor 页眉仅含软件名与版本）
> - `prologue` / `epilogue` — 保持忽略

## 输出

对于配置文件中的每一个 group, 会在 `.bring-it/sample/` 目录下生成 `{title}_{version}.docx`。

输出将由 copyright-code-extractor 生成：自动剥离注释与空行、每页固定行数、
页眉居中软件名称与版本号。

## 用法

### 使用 uv 直接运行

不需要将本仓库 clone 到本地, uv 会处理。

```bash
$ uvx --from git+https://github.com/EaphoneTech/pysample@feat/use-copyright-code-extractor pysample
```

### 使用 uv tool 安装

使用下面的方式, 可以将 pysample 作为一个应用程序安装到本机:

```bash
$ uv tool install --from git+https://github.com/EaphoneTech/pysample@feat/use-copyright-code-extractor pysample
```

安装后就可以直接用 `pysample` 来运行了。

安装后，使用 `uv tool upgrade pysample` 可以升级。

### 使用 docker

TODO: 目前还未完成

```bash
docker run --rm xxx
```
