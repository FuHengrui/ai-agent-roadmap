@@h1 第二章　ModelScope Notebook 环境配置与 Conda 管理
@@sub 阶段 19 · 大模型开发工具平台　|　云端环境　|　难度 ★★☆

@@why 这一章在解决什么问题
第一章领到了云端 GPU，但打开 Notebook 只是个空壳：界面长什么样？怎么新建文件、开终端？更关键的是——**云平台的 Python 环境是"公用"的，你装一个包可能影响所有项目；装错版本可能把环境搞崩**。本章解决两个问题：**① 熟练操作 Notebook 界面（新建文件/终端/Web-IDE 切换）；② 用 Conda 建立自己独立的开发环境**，做到"环境隔离、互不干扰、持久保存"。

本章是操作型章节（点界面为主），**代码只在一个场景出现**：安装 Conda 时需要贴 3 条命令。建议开着浏览器边看边点。

@@prep 开始之前
上一章的 Notebook 能开就能开始，这章在实例 Terminal 里装 Miniconda，不用动自己电脑。

@@goal 学到这儿就够了
能在 Web-IDE 和 Terminal 里干活，能装好 Conda、建出独立环境并在里面装包，这章就算过了。

@@map 上一章→本章→下一章
上一章解决了"有没有 GPU"（ModelScope 云端算力平台：登录、绑定、授权、领额度）。**本章接着解决"环境好不好用"：先带你熟悉 Notebook 的两个界面（Jupyter + VS Code Web-IDE），再教你用 Conda 建自己的隔离环境**。环境建好后，下一章将切换到 AutoDL 平台，讲"怎么按任务选 GPU、怎么远程开发"——两章合起来，你就有了一整套稳定的云端开发姿势。

@@point ① Notebook 实例界面构成
@@need 要解决什么
第一次打开 Notebook，满屏的按钮和区域不知道哪块是干嘛的，容易点错，也不知道文件在哪、终端在哪开。

@@idea 核心思路
从模型详情页或个人中心启动实例后，进入 Notebook 实例界面。虽然不同版本的界面布局略有差异，但核心区域就三块，认准它们就够用：

| 区域 | 位置 | 作用 |
|---|---|---|
| 文件树 | 左侧 | 浏览 /mnt/workspace/ 下的文件与目录 |
| 工作区 | 中间 | 打开笔记本/代码文件，写代码看结果的主要区域 |
| 顶部工具栏 | 上方 | 新建文件、保存、切换 Kernel、打开终端 |

启动后如果左侧没有文件树，点左上角"文件/资源管理器"图标展开即可。记住一个原则：**你在界面看到的一切，最终都落在 `/mnt/workspace/` 这个持久化目录里**——所以放文件时跟着文件树走，别乱建路径。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 打开的页面和文档截图长得不一样 | 平台界面会随版本更新微调，但"文件树+工作区+工具栏"三块结构不变，按功能找位置 |
| 左侧看不到自己上传的数据 | 刷新文件树（右键→刷新），或确认文件确实传到了这个实例的 /mnt/workspace/ 下 |

@@point ② 从 Launcher 新建 Notebook 文件
@@need 要解决什么
进了界面第一件事就是"开个新 Python 文件开始写代码"，但入口藏得不好找，点错就建了个空文件夹或者别的类型文件。

@@idea 核心思路
在 **Launcher 页（启动页）** 用鼠标点选主工作区的不同文件选项来新建文件。通常你只需要两个：

- **Python 3（ipykernel）**：新建一个 Jupyter Notebook（.ipynb），边写边跑，适合练手、数据探索。
- **Text File / Markdown File**：新建脚本或说明文档，适合保存整理好的代码。

别手动敲文件名带 .py 还是 .ipynb——在 Launcher 里**点对应的图标**，系统自动帮你建好正确类型。每次进入界面，如果 Launcher 被关了，点左上角"+"号或"文件→新建 Launcher"重新打开。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 新建的文件找不到 | 新文件默认建在当前工作目录，看文件树里是不是多了个未命名文件；给每个文件起个有意义的名字 |
| 点开 Launcher 没反应 | 等界面加载完成再点；实例刚启动时后端还在初始化 Kernel |

@@point ③ 用 Terminal 跑命令行任务
@@need 要解决什么
有些操作必须在命令行完成：装 pip 包、跑训练脚本、执行 shell 命令。但很多同学在 Notebook 里找不到"命令行窗口"在哪。

@@idea 核心思路
在 Launcher 页点击下方带红框标识的 **Terminal** 图标，就打开了终端页面——它就是一个 Bash 命令行，可以执行 `pip install xxx`、`python train.py` 等任何命令。

**什么时候用 Terminal？**
- 安装 Python 包（pip install）
- 跑训练/推理脚本（python xxx.py）
- 环境配置（conda create、编译等）
- 查看磁盘占用（df -h）

和 Jupyter 单元区别：Jupyter 适合"边写边看每一步结果"，Terminal 适合"执行一整条命令链路"。长任务推荐在 Terminal 里跑，能一直看到标准输出日志。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 在 Jupyter 里用 !pip 装包和 Terminal 里装效果不一样 | 两者用的可能是**不同 Python 环境**；先 `which python` 确认，统一用同一个环境装包 |
| Terminal 输入命令没反应 | 终端在等待输入密码/确认（如 sudo、ssh）；回车或按提示输入即可 |

@@point ④ Web-IDE：切换成 VS Code
@@need 要解决什么
Jupyter 适合数据分析，但写大型项目（多个 .py 文件、目录结构、版本控制）时，Jupyter 的工作方式很别扭。不想在云端和本地两套工具间来回切。

@@idea 核心思路
ModelScope Notebook 基于同样的算力和存储，提供了 **Web-IDE（VS Code Online）入口**：你可以在 Jupyter 和 VS Code 之间自由切换，界面就是熟悉的 VS Code。

操作：在 Notebook 页面找 **Web-IDE 入口**（通常标识为 VS Code/开发环境），点击进入。进入后就是经典 VS Code 布局，右上角会出现"返回 Jupyter Notebook"的图标，方便随时切回。

**两者共用一个环境**：文件、已装包、运行中的服务都共享。VS Code 模式最适合：多文件工程开发、用代码补全/重构、调试（Debug）复杂逻辑。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 切换后 VS Code 里看不到 Notebook 文件 | 刷新文件资源管理器；两层 Web 界面共用同一文件系统，只是视图缓存 |
| Web-IDE 打不开/白屏 | 实例可能因低配资源卡顿；等 1-2 分钟刷新，或切回 Jupyter 用 |

@@point ⑤ 为什么需要 Conda：环境隔离
@@need 要解决什么
云平台给的是"公共环境"，所有项目共用一个 Python。项目 A 需要 tensorflow 2.x，项目 B 需要 1.x，装来装去必然冲突，甚至把系统环境搞崩。

@@idea 核心思路
**Conda 是一个开源的软件包管理和环境管理系统**，核心能力是**创建和管理多个相互独立的开发环境**。每个环境有自己的 Python 版本和包集合，A 项目在 env-a 里装什么，完全不影响 B 项目的 env-b。

```
系统 Python（公共，别动）
├── env-a：Python 3.10 + torch 2.x  ← 项目 A
└── env-b：Python 3.8  + tf 1.15    ← 项目 B
```

在 Python 开发里，用 Conda 做环境隔离是**标准操作**（也是面试常问的考点）。它解决的痛点非常日常："我昨天还好好的，今天装了个包全崩了"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接在公共环境 pip install 常用包 | 短期能用，但一旦版本冲突无法回滚；规范做法是每次项目开一个新 Conda 环境 |
| 确定不了当前在哪个环境 | 终端执行 `conda env list` 或看命令行前缀括号（(env-a) 表示在 env-a 里） |

@@point ⑥ 下载并安装 Miniconda 到 /mnt/workspace
@@need 要解决什么
云平台的 Linux 环境默认可能没装 Conda；就算装了，安装位置也未必是持久化目录——关机就丢，白装。自己装一遍，还要装对地方。

@@idea 核心思路
ModelScope Notebook 是 Linux 环境，所以要去 Miniconda 官网下载 **Linux 版**安装包：`Miniconda3-latest-Linux-x86_64.sh`（x86_64 对应主流 x86 服务器；ARM 机型另选）。

**关键：安装目录必须指定到持久化路径 `/mnt/workspace/` 下**，因为只有这个目录在实例重启后仍然保留。安装命令：

```bash
# 下载（链接为范例，实际以官方站点安装脚本链接为准）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
# 赋予可执行权限
chmod +x Miniconda3-latest-Linux-x86_64.sh
# 安装到 /mnt/workspace/miniconda3，-b 表示批处理、免交互
bash Miniconda3-latest-Linux-x86_64.sh -b -p /mnt/workspace/miniconda3
```

参数拆解：
- `-p /mnt/workspace/miniconda3`：指定完整安装路径（**必须放 /mnt/workspace 下才会持久化**）。
- `-b`：批处理模式，安装过程不弹交互提示，适合脚本化执行。

装的时候用 `!` 前缀在 Jupyter 里执行也一样（`!bash xxx.sh -b -p ...`），本质都是跑 Bash。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 安装到默认路径（如 /root/miniconda3） | 实例重建后环境丢失，要重装；**务必 -p 指定到 /mnt/workspace** |
| 下载太慢或连不上 repo.anaconda.com | 用国内镜像源（如清华 TUNA 的 miniconda 镜像）替换 wget 链接 |
| 报 "Permission denied" | 缺执行权限，先 `chmod +x` 或 `bash Miniconda3-latest-Linux-x86_64.sh` 直接交给 bash 解释执行 |

@@point ⑦ 初始化 Conda 让命令生效
@@need 要解决什么
装完 conda，输入 `conda --version` 却提示"command not found"——因为安装到自定义路径后，shell 还不知道去哪找 conda 命令。

@@idea 核心思路
手工指定安装路径时，安装完成后需要**显式调用 conda 的二进制做初始化**，让 shell 把 conda 加进 PATH：

```bash
/mnt/workspace/miniconda3/bin/conda init
```

执行后它会往 shell 配置文件（~/.bashrc）里写入初始化代码。**重新打开终端（或 `source ~/.bashrc`）** 后，`conda --version` 就能正常输出版本号了。

如果 `conda init` 之后还是找不到命令，可以直接用全路径调用 `/mnt/workspace/miniconda3/bin/conda ...`——全路径永远有效，不依赖 PATH 配置。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 执行 conda init 报 "command not found" | 用的是短命令 `conda`，但还没初始化；先换成全路径 `/mnt/workspace/miniconda3/bin/conda init` |
| init 后当前终端还是不行 | init 只对**新开的终端**生效；执行 `source ~/.bashrc` 或重开 Terminal |
| 重启实例后 conda 又找不到 | 确认 .bashrc 是否被重置；稳妥做法是习惯用全路径调用 conda |

@@point ⑧ 用 Conda 建专属环境并装包
@@need 要解决什么
环境装好、命令能用了，最后一步是实际"建一个自己的环境"，并且以后每次项目都从这里开始。

@@idea 核心思路
最常用的三条 Conda 命令覆盖了"建环境→进环境→装包"全流程：

```bash
# 创建独立环境（指定 Python 版本），如创建 py310 环境
conda create -n py310 python=3.10 -y
# 激活进入该环境
conda activate py310
# 在环境里装包（不再污染公共环境）
pip install numpy torch
```

要点：
- `-n py310` 给环境起名，`python=3.10` 指定版本，`-y` 跳过确认。
- 激活后终端前缀出现 `(py310)`，表示你已在本环境内，此时 pip 安装的包都归属于它。
- 每天开工流程：打开 Terminal → `conda activate py310` → 开始写代码。

**规范心法**：一个项目一个环境；环境名一眼能看出用途（如项目名或 Python 版本）；环境建好后用 `conda env list` 随时查看。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| activate 后 pip 装的包别的环境也能用 | 不可能——pip 装到当前激活环境的 site-packages；检查终端前缀确认在哪个环境 |
| conda create 特别慢 | 首次建环境要下载 Python 包；可配置 conda 国内镜像加速（channels 配清华源） |
| 建错了环境想删 | `conda remove -n 环境名 --all`；别在公共环境乱删，只删自己建的 |

@@summary
本章把 ModelScope Notebook 从"能打开"推进到"好用"：

| 问题 | 答案 |
|---|---|
| Notebook 界面分几块 | 文件树 + 工作区 + 顶栏，位置随版本微调但结构不变 |
| 怎么新建文件 | Launcher 页点图标，Python3 建 Notebook、Text 建脚本 |
| 怎么跑命令行 | 打开 Terminal 执行 pip/python/conda，长任务优先在 Terminal 跑 |
| 想要 VS Code 界面 | 走 Web-IDE 入口，随时切回 Jupyter，共用环境 |
| 为什么用 Conda | 多项目环境隔离，互不干扰，标准操作 |
| 装哪才不丢 | Miniconda 必须 -p 装到 /mnt/workspace/miniconda3 |
| 装完怎么生效 | /mnt/workspace/miniconda3/bin/conda init，重开终端 |
| 日常开工三连 | conda create -n 名字 → conda activate → pip install |

一句话记住本章：**Notebook 界面认三块（文件树/工作区/顶栏），命令行跑 Terminal，想要 VS Code 走 Web-IDE；Conda 环境必须装进 /mnt/workspace 才持久，conda create→activate→pip install 三连开工。**

@@quiz
1. ModelScope Notebook 界面主要包含哪三个区域？各干什么用？
2. 想新建一个 Jupyter Notebook 文件，应该在哪里操作？
3. Terminal 和 Jupyter 单元分别适合什么场景？
4. 从 Jupyter 切换到 VS Code（Web-IDE）后，环境和文件是独立的还是共享的？
5. 为什么要用 Conda 而不直接在公共环境装包？
6. 安装 Miniconda 时 `-p /mnt/workspace/miniconda3` 和 `-b` 分别表示什么？为什么必须装到 /mnt/workspace？
7. 装完 Conda 后 conda 命令找不到，应该怎么解决？
8. 写出创建名为 py310、Python 3.10 环境的命令并激活它。

@@links
参考|大模型开发工具平台（ModelScope Notebook 部分，9 页）|#
工具|Miniconda 官方下载|https://docs.conda.io/en/latest/miniconda.html
文档|Conda 用户手册（创建环境）|https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html