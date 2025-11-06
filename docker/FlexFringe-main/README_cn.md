# README #

flexfringe（原名DFASAT），一个用C++编写的灵活状态合并框架。

## 此仓库包含的内容 ##

此仓库包含flexfringe的最新发布版本。

## 如何设置 ##

flexfringe编译时无需外部依赖项。目前支持使用make和cmake的构建链。

对于专业用户：如果您想要使用SAT约简并自动调用SAT求解器，您需要提供求解器二进制文件的路径。flexfringe已经用lingeling进行了测试（您可以从 http://fmv.jku.at/lingeling/ 获取并运行其build.sh）。
**请注意：** SAT求解仅适用于学习普通DFA。当前实现未经验证是否正确。如果您依赖SAT求解，请使用较旧的提交。

您可以通过运行以下命令来构建和编译flexfringe项目：

`$ make clean all`

或者，使用CMake：

`$ mkdir build && cd build && cmake ..`
`$ make`

在主目录中构建名为*flexfringe*的可执行文件。还有一个CMakelists.txt用于使用cmake构建。我们在Linux（Ubuntu 16+）、MacOS（10.14）和Windows 10上测试了工具链。对于后者，可以使用CLion附带的CMake进行构建。

## 如何运行 ##

运行 ./flexfringe --help 获取帮助。

我们提供了几个.ini文件作为存储常用设置的快捷方式。

示例：

`$ ./flexfringe --ini ini/batch-overlap.ini data/staminadata/1_training.txt.dat`

更多信息请查看.ini文件，使用--help标志获取选项的简短描述。

### Docker

对于跨平台解决方案，您可以使用Docker运行FlexFringe：

```
docker run -it ghcr.io/tudelft-cda-lab/flexfringe:main
```

这会在docker容器内提供一个shell，位于源仓库目录，源文件夹中包含二进制文件。

### 输入文件 ###

默认输入格式遵循Abadingo格式：

```
样本数量 字母表大小
标签 长度 符号1 符号2 ... 符号N
.
.
.
```
对于每个符号，可以通过/附加额外数据，即`标签 长度 符号1/数据1 符号2/数据2 ... 符号N/数据N`。这些可以表示输出（例如，对于Mealy或Moore机器），或自定义评估函数所需的任何其他信息。

实值属性，例如用于实时自动机，可以通过:附加，即`标签 长度 符号1:实数1,实数2,实数n ...`。属性数量必须在头部的字母表大小之后指定，即`样本数量 字母表大小:属性数量`。

### 输出文件 ###

flexfringe将在指定的输出目录（默认为./）中生成几个.dot文件：

*  pre\:\*.dot是在合并/搜索过程中创建的中间dot文件。
*  dfafinal.dot是最终结果的dot文件
*  dfafinal.dot.json是最终结果

您可以通过以下方式绘制dot文件：

`$ dot -Tpdf file.dot -o outfile.pdf`
或
`$ ./show.sh final.dot`

在安装graphviz的dot后。
要使用生成的模型进行语言接受测试或作为分布函数，最好解析JSON文件。您可以在 https://github.com/laxris/flexfringe-colab 的Jupyter notebook中找到示例。

## 文档 ##

*flexfringe*在*./doc*目录中包含部分Doxygen风格的文档。可以使用Doxygen文件中的设置重新生成。

## 贡献指南 ##

*  Fork并实现，请求拉取。
*  您可以在./source/evaluation中找到示例评估文件。确保注册您自己的文件，以便能够通过-h和--heuristic-name标志访问它。

### 编写测试 ###

单元测试不完整。*flexfringe*使用Catch2框架（参见[教程](https://github.com/catchorg/Catch2/blob/master/docs/tutorial.md)和*tests*文件夹中的一些示例）。

### 日志记录 ###
日志记录不完整。*flexfringe*使用loguru框架（参见[Loguru文档](https://github.com/emilk/loguru/blob/master/README.md)）。*flexfringe*使用流版本。请使用`LOG_S(LEVEL) << "消息"`语法实现日志记录。

## 联系人 ##

*   Tom Catshoek（科学程序员和维护者）
*   Christian Hammerschmidt（在线/流模式、交互模式和灵活评估函数机制的作者）
*   Sicco Verwer（原作者；关于批处理模式、RTI+实现和SAT约简的问题最好联系他）
*   Robert Baumgartner

前贡献者包括：
*   Sofia Tsoni（前科学程序员和维护者）

## 徽章 ##
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ae975ed72f9c4e1bb19b18dc44aacf1f)](https://app.codacy.com/gh/tudelft-cda-lab/FlexFringe?utm_source=github.com&utm_medium=referral&utm_content=tudelft-cda-lab/FlexFringe&utm_campaign=Badge_Grade_Settings)

## 致谢和许可证 ##

*flexfinge*依赖于许多开源包和库。您可以在source/utility子目录中找到相应的许可证文件。
最值得注意的是，我们使用了：

*   CLI11用于命令行解析
*   Catch用于单元测试
*   Keith O'Hara的StatsLib C++和GCE-Math C++库（Apache版本2.0）
*   Niels Lohmann的Modern C++ JSON库（版本3.1.2）<http://nlohmann.me> 来自 https://github.com/nlohmann/json

## 构建Doxygen文档

此项目的文档可以使用

COMPILE_DOCS=ON

标志与cmake命令一起构建。我们使用Doxygen和Sphinx。编译文档的要求有：

*   Doxygen（使用版本1.8.20测试）
*   Sphinx（使用版本3.3.1测试）。我们使用rtd主题，安装见下文。
*   breathe（使用版本4.24.0测试）

在Linux上可以使用以下命令安装：

```shell
apt-get install doxygen
```
,

```shell
pip install sphinx_rtd_theme
```

, 和

```shell
pip install breathe
```
.

重要提示：如果添加了新的类、函数、结构等，并且它们应该出现在文档中，则必须将它们添加到docs/index.rst文件的底部。有关更多信息和简短的快速入门指南，请查看例如：

https://breathe.readthedocs.io/en/latest/quickstart.html
https://breathe.readthedocs.io/en/latest/directives.html 