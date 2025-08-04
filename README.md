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
      "lineNumber": true,
      "maxLines": 2000
    }
  ]
}
```

简单来说, 需要在 `patterns` 中指定要包括的文件, 在 `extensions` 中指定要包括的文件的后缀名, 并填写 `title`, `version` 和 `company` 这些信息。

## 输出

对于配置文件中的每一个 group, 会在 `.bring-it/sample/` 目录下生成 `{title}_{version}.docx`

## 用法

### 使用 uv 直接运行

不需要将本仓库 clone 到本地, uv 会处理。

```bash
$ uvx --from git+https://github.com/EaphoneTech/pysample.git pysample
```

### 使用 uv tool 安装

使用下面的方式, 可以将 pysample 作为一个应用程序安装到本机:

```bash
$ uvx install --from git+https://github.com/EaphoneTech/pysample.git pysample
Resolved 8 packages in 1.90s
    Updated https://github.com/EaphoneTech/pysample.git (5b31b6503d1a904c1ad27e0b241821ed67af8f75)
      Built pysample @ git+https://github.com/EaphoneTech/pysample.git@5b31b6503d1a904c1ad27e0b241821ed67af8f75
Prepared 1 package in 6.58s
Installed 8 packages in 95ms
 + click==8.2.1
 + colorama==0.4.6
 + loguru==0.7.3
 + lxml==6.0.0
 + pysample==0.1.0 (from git+https://github.com/EaphoneTech/pysample.git@5b31b6503d1a904c1ad27e0b241821ed67af8f75)
 + python-docx==1.2.0
 + typing-extensions==4.14.1
 + win32-setctime==1.2.0
Installed 1 executable: pysample.exe
```

安装后就可以直接用 `pysample` 来运行了。

### 使用 docker

TODO: 目前还未完成

```bash
docker run --rm xxx
```
