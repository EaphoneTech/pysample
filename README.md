# pysample

生成软件著作权的 python 工具

## 配置文件

该文件读取 [@bring-it/sample](https://github.com/Airkro/bring-it/tree/master/packages/sample) 的配置文件，例如:

```jsonc
// .bring-it/sample.config.json
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

## 输出

对于配置文件中的每一个 group, 会在 `.bring-it/sample/` 目录下生成 `{title}_{version}.docx`
