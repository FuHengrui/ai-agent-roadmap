@@h1 第二章　Jupyter Notebook、镜像配置与开发工具链
@@sub 阶段 17 · 数据科学与智能分析基础　|　环境搭建　|　难度 ★☆☆

@@why 这一章在解决什么问题
**环境装好了，但"好用"还差三步：官方源下载慢到怀疑人生；Jupyter Notebook 听说过但没真正用过，不知道它的文件、单元格、快捷键是怎么回事；PyCharm 和 VSCode 二选一选不明白。** 这三步不解决，你的数据分析体验会一直"卡卡的"。

这一章就是"顺滑化"三件套：**换国内镜像源 → 上手 Jupyter Notebook → 配好 IDE 与项目依赖管理**。学完你能回答：conda/pip 怎么换源、Jupyter 怎么装怎么启动怎么操作、PyCharm/VSCode 怎么选、requirements.txt 和 pyproject.toml 是干嘛的、uv 为什么是效率神器。

@@map 这一章在整个知识库里的位置
**上一章**：装好 Anaconda 并掌握 conda 虚拟环境——环境"能跑"了
**本章** ← 你在这里：把环境调到"好用"——换源提速、Jupyter 交互开发、IDE 配置、依赖管理
**下一章**：Matplotlib 基础与图形定制——你手上的第一个绘图库，所有案例的练习都建议放在 Jupyter 里跑
**再往后**：Seaborn → NumPy → Pandas → MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"的完整数据分析链路

@@note info 学习提示
本章实操密度高，建议边看边在终端敲。**换源（第 ①② 点）做完一劳永逸**；Jupyter（第 ③-⑧ 点）是数据分析的默认工作台，快捷键背最常用的几个就行；IDE 和依赖管理（第 ⑨-⑪ 点）先建立概念，用到再翻。

@@point ① conda 换源：.condarc 与国内镜像
@@need 要解决什么
conda 默认走官方源，在国内下载包慢、还经常超时断流。**换国内镜像，速度立翻几倍。**

@@idea 核心思路
conda 的所有配置存在 **.condarc** 文件里，换源就是改这个文件的 channels 配置。Windows 上不能直接手动新建 .condarc（可能不被识别），正确做法是**先让 conda 生成，再修改**：

```bash
conda config --set show_channel_urls yes    # 首次执行会生成 .condarc 文件
```

然后用编辑器打开用户目录下的 `.condarc`，把 channels 换成清华镜像（或手动执行添加命令）：

```text
# .condarc 关键配置
channels:
  - defaults

default_channels:                           # 官方三源指向清华
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2

custom_channels:                            # 常用社区源指向清华
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
```

也可以命令行添加（等价且更不容易写错路径）：

```bash
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用 `conda config set global.index-url ...` 换源 | 那是 pip 的命令风格，conda 不认；conda 要走 channels 配置 |
| 镜像地址写错（漏掉 /pkgs/ 或 /cloud/ 路径段） | 按上面完整路径抄；漏一级路径会 404 |
| 改完 .condarc 报 yaml 格式错误 | 缩进、冒号后空格要规范；格式错了 conda 直接报错 |

@@point ② pip 换源与环境目录搬家
@@need 要解决什么
pip 同样慢；另外虚拟环境和缓存包默认堆在 C 盘，**装几个环境 C 盘就红了。** 两件事一起解决。

@@idea 核心思路
pip 换源一条命令（走清华 PyPI 镜像）：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

**注意是 `global.index-url`**——这条与 conda 的 channels 配置风格完全不同，别搞混。

环境目录搬家：在 .condarc 里追加两个目录配置，把"虚拟环境"和"下载缓存"都挪到其他盘（示例路径，替换成你自己的盘符）：

```text
envs_dirs:                                  # 虚拟环境存放目录
  - D:\miniconda3\envs
pkgs_dirs:                                  # 包缓存目录
  - D:\miniconda\pkgs
```

如此 C 盘只留 conda 本体，大头都挪走。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| pip 换源后偶尔仍慢 | 个别包清华没有，会自动回源；也可再加阿里云镜像 `https://mirrors.aliyun.com/pypi/simple/` |
| envs_dirs 配置不生效 | 确认配置在 .condarc 且重开终端；新环境才会落到新目录 |
| 目录路径含特殊字符 | 与安装路径同理，可能引发隐蔽问题，尽量用纯字母数字路径 |

@@point ③ Jupyter Notebook 是什么：网页里的代码草稿本
@@need 要解决什么
数据分析"边写代码边写思路"是常态：纯脚本文件里，代码和解释割裂；用 Word 记笔记，代码又不验证。**需要一种"代码和说明混排、还能即时运行"的载体。**

@@idea 核心思路
Jupyter Notebook 是**基于网页的交互式计算应用**：在浏览器里直接写代码、运行代码，结果显示在代码块正下方。它天然适合数据分析，因为：

- **代码 + Markdown 说明混排**：一个单元格写代码、一个单元格写笔记，形成可复现的"代码报告"；
- **富媒体输出**：支持 HTML、LaTeX 数学公式、PNG/SVG 图片——画图结果直接内嵌；
- **交互式探索**：语法高亮、Tab 补全，一行一行跑，边跑边看中间结果。

注意：**Anaconda 完整版已内置 Jupyter，Miniconda 用户需自行安装**（见下一点）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用 Miniconda，网页里打开 Jupyter 报"找不到" | 没装；见第 ④ 点安装 |
| 以为 Jupyter 只能写 Python | 它支持多种内核（R、Julia 等），但本阶段只用 Python 内核就够了 |

@@point ④ 安装、启动与端口
@@need 要解决什么
装好 Jupyter 后怎么启动？浏览器地址 localhost:8888 是什么？关掉终端就白屏是为什么？

@@idea 核心思路
安装（Miniconda 用户）：

```bash
conda install jupyter notebook
```

老版本 pip 要先升级再装，否则依赖装不全：`pip install --upgrade pip`。

启动：

```bash
jupyter notebook
```

浏览器会自动打开 `http://localhost:8888`。这里 **localhost 是本机地址，8888 是端口**：

- 多开一个实例，端口自动 **+1**（8889、8890……），这是正常现象；
- 自定义端口：`jupyter notebook --port 9999`；
- **终端不能关**：关闭终端 = 断开与本地服务器的连接，网页立刻失效。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 关掉启动用的终端，浏览器页面打不开了 | 就是设计如此；Jupyter 服务跑在那个终端里，想一直用就别关 |
| 端口自己变 8889、8890 | 8888 被占用自动递增，不是出错 |

@@point ⑤ 修改主目录与文件操作
@@need 要解决什么
Jupyter 默认把文件放在用户主目录，你想把工作文件放 D 盘某个文件夹，**怎么改？**

@@idea 核心思路
改主目录两步：

```bash
jupyter notebook --generate-config       # 生成配置文件（只执行一次）
```

然后编辑配置文件，路径在 `用户目录\.jupyter\jupyter_notebook_config.py`，找到并修改：

```text
c.NotebookApp.notebook_dir = 'D:\\mywork'   # 改成你想作为工作目录的路径
```

保存后**重启 Jupyter** 才生效。文件操作方面：网页右上角可新建（Python 文件后缀是 **.ipynb**）、上传、下载、复制、移动、删除；改文件名需先关闭该文件。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 改了配置但启动还是在老目录 | 改完必须重启 Jupyter 验证；配置项拼写也容易错（c.NotebookApp.notebook_dir） |
| 新建文件后找不到在哪 | 后缀是 .ipynb 不是 .py；在 Jupyter 网页文件树里查看 |

@@point ⑥ 单元格类型与"命令/编辑"双模式
@@need 要解决什么
在 Notebook 里按键盘没反应、复制粘贴无效——**你是掉进了模式陷阱**。Jupyter 有四种单元格、两种模式，不搞清就会"鬼打墙"。

@@idea 核心思路
**四种单元格类型：**

| 类型 | 作用 | 说明 |
|---|---|---|
| Code | 写 Python 代码 | 运行时执行，显示输出 |
| Markdown | 写说明文字 | 支持排版、公式，常用 |
| Raw NBConvert | 原样保存文本 | 基本不用 |
| Heading | 标题 | 已废弃，别用 |

**两种模式：**

- **命令模式**：单元格被选中、不可编辑（左侧是粗蓝线，按 `Esc` 进入）。此时按键是"命令"：如 `A` 在上面插单元格、`DD` 删除；
- **编辑模式**：可在单元格内打字（左侧绿线，按 `Enter` 进入）。此时按键是"打字"。

快捷键不生效，九成是"以为在编辑模式，其实在命令模式"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 按 A/B/X/C/V 却是打字进单元格 | 说明你在编辑模式；按 Esc 切到命令模式再按 |
| 双击单元格没反应、无法编辑 | 按 Enter 或双击进入编辑模式（左侧显示绿线） |

@@point ⑦ 高频快捷键：先背这 10 个
@@need 要解决什么
Notebook 操作靠快捷键效率翻倍，但快捷键表一屏都放不下。**先背最常用的 10 个，够用 90% 的场景。**

@@idea 核心思路
命令模式（按过 Esc 后）：

```text
A / B        在上方 / 下方插入新单元格
DD           删除当前单元格
M / Y        切换为 Markdown / Code
X / C / V    剪切 / 复制 / 粘贴单元格
Shift+Enter  运行并选中下一个单元格
Ctrl+Enter   运行并停留在当前单元格
Ctrl+Shift+- 在光标处分割单元格
```

编辑模式下：

```text
Tab          代码补全
Ctrl+/       注释/取消注释（多行）
Ctrl+S       保存
```

完整表在菜单 **Help → Keyboard Shortcuts** 里。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 照 Mac 教程按 ⌘/⌥ 没反应 | Windows 对应 Ctrl/Alt；键位对照表在快捷键设置页里有标注 |
| DD 删不掉单元格 | 先 Esc 进命令模式；且确认光标没在编辑状态 |

@@point ⑧ VSCode 里的 Jupyter：不想开网页就用它
@@need 要解决什么
开浏览器烦、多窗口乱。**能不能在 VSCode 里直接跑 Notebook？** 能，但有三个前置条件。

@@idea 核心思路
VSCode 用 Jupyter 需要两步配置：

```text
第 1 步  装插件：Jupyter（必须装，VSCode 不是默认支持的）
第 2 步  选内核：打开 .ipynb 文件后，右下角选择 Python 环境
```

要点：

- **ipynb 与 py 两种形态**：.ipynb 是 Notebook 单元格式；.py 文件可点"运行交互式窗口"当 Notebook 用；
- 首次运行提示安装 **ipykernel** 时点安装（同一环境只需一次）；
- 选内核时记得选到**对应的 conda 虚拟环境**，别选成系统自带 Python。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 装了 Python 插件但打不开 ipynb | 缺 Jupyter 插件；两个插件分工不同都装 |
| 运行提示"没有可用内核" | 该环境缺 ipykernel，按提示安装一次即可 |

@@point ⑨ PyCharm 与 VSCode：数据分析的 IDE 怎么选
@@need 要解决什么
一个功能全但吃内存，一个轻量但要自己配插件——**第一天就纠结选哪个，不值得。给你一张决策表。**

@@idea 核心思路

| 维度 | PyCharm | VSCode |
|---|---|---|
| 出身 | JetBrains，专业 IDE | 微软，轻量编辑器 + 插件 |
| 上手 | 开箱即用，自动导包、调试方便 | 要装 Python 扩展、选解释器 |
| 内存 | 高（首次索引慢，占用可达 3G） | 低（启动快，无长索引） |
| 适合 | 重项目、不差内存 | 低配机器、轻量脚本、多语言 |

**低配 Windows 机器的推荐：VSCode。** 配置三步：插件面板搜 Python 安装 → 打开一个 .py 文件触发左下角解释器选择 → 选中你的 conda 虚拟环境。装完就有语法高亮、补全、运行调试。

PyCharm 侧记住两点：创建项目时或进入设置里都能配 Python 解释器；**Windows 上也别装 C 盘**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| VSCode 写 Python 没智能提示 | 没选解释器；新建 .py 文件会自动弹出选择框 |
| PyCharm 很卡 | 正常，它内存占用约 3G；低配机器直接换 VSCode |

@@point ⑩ requirements.txt 与 pyproject.toml：项目依赖管理
@@need 要解决什么
项目写完，别人克隆下来跑不起来——**因为你没告诉他装哪些包、什么版本。** 依赖清单就是"项目安装说明书"。

@@idea 核心思路
**requirements.txt（快速方案）：**

```bash
python -m venv .venv            # 建虚拟环境
pip install flask               # 装需要的包
pip freeze > requirements.txt   # 导出全部已装包清单
```

别人拿到项目后 `pip install -r requirements.txt` 一键装齐。**注意**：freeze 导出的是环境里的全部包，可能含你装卸残留的依赖。

**pyproject.toml（规范方案）：** 显式声明项目直接依赖，而不是整个环境快照：

```text
[project]
name = "my-project"
version = "0.1.0"
dependencies = [
    "flask",
]
```

安装命令 `pip install -e .`。**修改了 pyproject.toml 后需要重新执行安装命令才生效。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| requirements.txt 里有一堆你没直接用的包 | 卸载某包时它的依赖不会跟着卸（如卸 flask 不卸其依赖），freeze 会残留；用 pyproject.toml 只列直接依赖更干净 |
| 改了 pyproject.toml 忘了重装 | 不会自动生效，要重跑 `pip install -e .` |

@@point ⑪ uv：新一代"一条龙"环境工具
@@need 要解决什么
pip + venv + requirements 这套流程步骤多、还慢。**有没有一个工具把这些全包了？** 有——uv。

@@idea 核心思路
uv 的目标是**同时替代 pip 和 virtualenv**，主打速度与可重现性。对照传统流程看它怎么"一条龙"：

```text
传统三步：python -m venv .venv
          → 手动建/改 pyproject.toml
          → pip install -e .
uv 三步：  uv venv -p 3.9 .venv     # 建环境（-p 指定 Python 版本）
          uv init                   # 生成项目骨架 + pyproject.toml
          uv add 包名                # 装包并自动写入依赖声明
```

常用命令速查：

```bash
uv add "flask>=2.0,<3.0"      # 指定版本范围装包，自动写进 pyproject.toml
uv remove 包名                 # 卸载并同步更新声明
uv sync                       # 同步环境与声明一致
uv python pin 3.10            # 锁定项目 Python 版本
uv run script.py              # 在项目环境中运行脚本
```

可以配合 conda 环境使用：激活 conda 环境后直接用 uv 管理其中的包。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| uv add 的包没出现在 pyproject.toml | 新版 uv 默认自动写入；老版本需确认 `--add` 参数行为 |
| 与 conda 混用怕搞乱 | uv 只接管"Python 包"部分，conda 管解释器和系统依赖，分工不冲突 |

@@summary
这一章把环境从"能跑"调到了"好用"：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **换源**：conda channels + pip index-url 指向第三方镜像 | 下载装包速度从"分钟级超时"变成"秒级完成" |
| **目录搬家**：envs_dirs / pkgs_dirs 挪出 C 盘 | 虚拟环境和缓存不再蚕食系统盘 |
| **Jupyter 全流程**：安装、启动、端口、主目录、文件操作、单元格与模式、快捷键 | 数据分析的默认工作台，熟练操作省一半时间 |
| **VSCode 集成**：Jupyter 插件 + ipykernel + 解释器选择 | 低配机器上的轻量开发方案 |
| **IDE 选型**：PyCharm 重而全 vs VSCode 轻而省 | 按机器配置理性选择 |
| **依赖管理**：requirements.txt 快、pyproject.toml 规范、uv 全自动 | 项目可复现、可交付，不再"在你机器上能跑" |

一句话记住本章：**换国内源提速，用 Jupyter 当工作台，低配选 VSCode，依赖管理从 requirements.txt 升级到 pyproject.toml 和 uv——环境从此顺滑。**

@@quiz
1. conda 换源要改哪个配置文件？Windows 上正确生成该文件的第一步命令是什么？
2. pip 换源的命令是什么？它的配置键名与 conda 有什么不同？
3. Jupyter 默认端口是多少？多开实例时端口会怎样变化？关掉启动终端会发生什么？
4. 修改 Jupyter 主目录的两步操作是什么？
5. Jupyter 的四种单元格类型是什么？命令模式与编辑模式怎么切换？
6. 在命令模式下，插入单元格、删除单元格、切换 Markdown、运行并选中下一个的快捷键分别是什么？
7. VSCode 里跑 Jupyter 需要满足哪三个条件？
@@links
参考|Anaconda 开发环境（34 页）|#
工具|Jupyter 官网|https://jupyter.org/
工具|PyCharm 下载页|https://www.jetbrains.com/pycharm/
工具|VSCode 官网|https://code.visualstudio.com/
工具|uv 官方文档|https://docs.astral.sh/uv/