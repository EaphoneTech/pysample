# 第三方许可声明 (Third-Party Licenses)

本项目 (pysample, MIT License) 使用以下第三方组件：

---

## copyright-code-extractor (GNU General Public License v3.0)

- **项目地址**: https://github.com/kirklin/copyright-code-extractor
- **许可证**: GNU General Public License v3.0 (GPL-3.0)
- **用途**: 生成软件著作权源代码文档（DOCX 格式）

### 聚合声明 (Aggregation Notice)

pysample 通过 **子进程调用 (subprocess)** 方式使用 copyright-code-extractor，
即通过 `sys.executable -m copyright_code_extractor.cli` 以独立进程方式运行该工具。

根据 GPL FAQ 关于「聚合 (Mere Aggregation)」的说明以及 FSF 的官方解释，
通过 fork/exec 调用 GPL 程序（包括通过 subprocess、管道或文件交换数据）构成 **聚合 (aggregate)**，
而非衍生作品 (derivative work)。聚合方式不会导致 GPL 的传染性条款 (copyleft) 适用于 pysample。

具体而言：
1. pysample **不 import / 不链接** copyright-code-extractor 的任何模块，不与之运行于
   同一进程地址空间；
2. pysample 不复制、不修改、不分发 copyright-code-extractor 的源代码或二进制文件；
3. copyright-code-extractor 由用户通过 PyPI（uv/pip）单独安装，作为运行时环境中的独立工具存在；
4. 二者之间的通信仅限于命令行参数和文件系统，不构成 GPL 意义上的「intimate data communication
   or control flow between subprograms」。

**结论**: pysample 与其依赖的 copyright-code-extractor 之间是「聚合 (aggregation)」关系，
pysample 仍可根据 MIT 许可证分发。本声明依 FSF/GPL FAQ 及
[catalog-sig 邮件列表](https://mail.python.org/pipermail/catalog-sig/2013-February/005022.html) 中
Vinay Sajip 的合规性结论编写。

### GPL-3.0 全文

copyright-code-extractor 的 GPL-3.0 许可证全文随本项目附带，
位于 `licenses/GPL-3.0.txt`。
