# pysample

生成软件著作权文档的 python 工具

## 配置文件

该文件读取 [@bring-it/sample](https://github.com/Airkro/bring-it/tree/master/packages/sample) 的配置文件: `.bring-it/sample.config.json`，例如:

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
      "lineNumber": true
    }
  ]
}
```

简单来说, 需要在 `patterns` 中指定要包括的文件, 在 `extensions` 中指定要包括的文件的后缀名, 并填写 `title`, `version` 和 `company` 这些信息。

## 输出

对于配置文件中的每一个 group, 会在 `.bring-it/sample/` 目录下生成 `{title}_{version}.docx`

## 用法

```bash
uvx --from git+https://github.com/EaphoneTech/pysample.git pysample
```

```bash
uvx --default-index http://mirrors.aliyun.com/pypi/simple/ --from git+https://github.com/EaphoneTech/pysample.git pysample
```
