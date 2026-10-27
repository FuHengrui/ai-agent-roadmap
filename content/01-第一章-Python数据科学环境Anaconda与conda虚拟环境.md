@@h1 第一章　Python 数据科学环境：Anaconda 与 conda 虚拟环境
@@sub 阶段 17 · 数据科学与智能分析基础　|　环境搭建　|　难度 ★☆☆

@@why 这一章在解决什么问题
**你是不是也有这样的经历：想用 Python 做数据分析，第一步就卡在"装环境"上——pip 装个 numpy 报错说要编译器；项目 A 要 pandas 老版本、项目 B 要新版，装一个坏一个；网上教程让你装 Anaconda，又说 Miniconda 更轻量，你根本不知道该选哪个。**

这些坑的根源是同一个：**Python 的包管理与环境隔离，生态经历过好几代演变，教程各讲各的，你拼不出一张完整地图。** 这一章就把地图画全：讲清 pip / wheel / conda / Anaconda / Miniconda 到底是什么关系，然后手把手带你装好 Anaconda、建出第一个 conda 虚拟环境。

学完这一章，你能回答：**为什么装库曾经那么难、conda 比 pip 强在哪、Anaconda 和 Miniconda 怎么选、怎么一步步装好并验证、虚拟环境的全部基本命令、PowerShell 激活失败的三种修法。**

@@map 这一章在整个知识库里的位置
**上一阶段（阶段 16 · Vibe Coding 实践）**：你学会了用 Trae、Cursor 等 AI 编程工具写代码——那是"让 AI 帮你写程序"。
**本章** ← 你在这里：开启阶段 17 数据科学与智能分析，第一件事是把 Python 科学计算环境搭好，后面所有库（matplotlib、numpy、Pandas、MySQL 连接）都跑在它上面
**下一章**：Jupyter Notebook、镜像配置与开发工具链——把"能跑"升级为"好用"：换国内源、用上 Jupyter、配好 IDE
**再往后**：matplotlib 可视化 → Seaborn 统计绘图 → NumPy 数值计算 → Pandas 数据分析 → MySQL 数据库
**阶段终点**：你能用 Python 完成"读数据 → 清洗 → 计算 → 可视化 → 入库"的完整数据分析链路

@@note info 学习提示
本章是三件事的合体：**懂生态（为什么有这些东西）→ 会安装（Anaconda 装好装对）→ 会用（conda 虚拟环境命令）**。安装部分按步骤走即可，别纠结每个勾选项；重点是第 ⑥ 点之后的虚拟环境命令——后面每一个章节的练习环境都从这里来。

@@point ① Python 科学计算生态："装库难"曾经是真的
@@need 要解决什么
先回答一个你迟早会问的问题：**为什么大家都在说"装 numpy 很麻烦"？** 不懂这段历史，你就无法理解 wheel、conda 这些概念是为什么存在的。

@@idea 核心思路
Python 语言本身很简洁，但早期的第三方库安装体验极差。原因是：**很多科学计算库（numpy、scipy、pandas）内部含有 C/C++ 扩展代码**，早期只有源码包，`pip install` 拿到源码后必须在你本机现场编译——Windows 上缺编译器（MKL、OpenBLAS）就直接报错，装一个库折腾半天。

转折点是 **wheel 二进制格式**（PEP 427 标准）：把编译好的成品打成 .whl 文件，`pip install` 直接解压即用，不再需要本机编译。从此 Python 依靠 numpy/scipy/pandas 等库进入科学计算领域，实现了"**语法简洁 + 性能高效**"的组合。

一句话记住：**wheel = 预编译好的二进制包，解决了"现场编译装不上"的历史难题**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 装含 C 扩展的包报"缺少编译器 / failed building wheel" | 优先确认有没有可用的 wheel 版本；实在没有才需要装编译器（如 Visual Studio Build Tools） |
| 以为 pip 只能装"纯 Python 库" | pip 也能装二进制 wheel，只是"能不能装成"取决于作者有没有发布 wheel 版本 |

@@point ② 认识 conda：跨语言包与环境管理器
@@need 要解决什么
pip 只能管 Python 包。但数据分析牵扯到 **编译器、CUDA、R 语言、FFmpeg** 这些跨语言依赖，pip 管不了——谁管？答案是 conda。

@@idea 核心思路
conda 于 2012 年随 Anaconda 一同发布，定位是**跨语言的包管理器 + 环境管理器**：

- **跨语言管包**：不局限于 Python，还能管理 C/C++ 库、编译器、CUDA、R 包等二进制依赖；
- **自带环境隔离**：`conda create -n myenv python=3.9` 一键建出互不干扰的独立环境；
- **严格依赖解析**：安装前预先检查所有依赖的版本冲突，而不是装了再炸。

核心命令先混个脸熟（本章第 ⑦ 点会展开）：

```bash
conda create -n myenv python=3.9   # 创建环境
conda install numpy                # 装包
conda uninstall numpy              # 卸包（注意是 uninstall，不是 remove）
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 conda 命令和 pip 命令记混 | conda 卸包是 `conda remove`；pip 卸包才是 `pip uninstall`——两套命名不同，别混记 |
| 以为 conda 只是"大号 pip" | conda 连解释器、CUDA、编译器都能装能管，这是 pip 做不到的 |

@@point ③ 发行版选型：Anaconda / Miniconda / Miniforge / Mamba
@@need 要解决什么
下载一个东西，官网给了好几个版本：Anaconda？Miniconda？还有社区推荐的 Miniforge 和 Mamba？**到底装哪个？** 这一节给你一张决策表。

@@idea 核心思路
先分清两个概念：**conda 是工具，各发行版是"预装好的 conda 全家桶"**。channel（数据源）与发行版的关系见下表：

| 发行版 | 含什么 | 默认数据源 | 适合谁 |
|---|---|---|---|
| Anaconda | conda + Python + 180 多个科学包 | defaults 官方源 | 新手、图省事、内存磁盘不紧张 |
| Miniconda | 仅 conda + Python（约 100MB） | defaults 官方源 | 想按需装包、追求轻量 |
| Miniforge | 同 Miniconda，但默认源是 conda-forge | conda-forge 社区源 | 被官方源商业条款/速度困扰的人 |
| Mamba | conda 的加速替代（内置于 Miniforge） | 跟随所在发行版 | 装包慢、依赖解析卡顿的人 |

两个关键背景知识：

- **channel 就是软件源**。Anaconda 官方仓库 defaults 分三类：main（主流 Python 包）、r（R 语言包）、msys2（Windows 类 Unix 工具链）。2020 年起 defaults 部分包对企业级用途开始限免费，大组织纷纷转向社区源 **conda-forge**——它更新快、数量多、现已是事实标准。
- **Mamba 用 C++ 重写了 conda 的依赖解析**，多线程解析通常快 5-10 倍，命令完全兼容（`mamba install` 等同 `conda install`），Miniforge 自带，无需另装。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 选了 Anaconda 后发现太大、开机变慢 | 没毛病，它就是全家桶；嫌重换 Miniconda，按需 `conda install` |
| 想用 conda-forge 却每次都要敲 `-c conda-forge` | 换 Miniforge，默认源就是 conda-forge |
| 以为 Mamba 要单独安装 | Miniforge 已内置；单独配在 Anaconda 里才需要手动装 |

@@point ④ Anaconda 安装全流程：五个关键点
@@need 要解决什么
下载页全英文，安装向导一堆勾选框——**哪些能一路下一步，哪些必须仔细？** 装错两处，后面处处爆炸。

@@idea 核心思路
Anaconda 安装整体流程（Windows）：

```text
第 1 步  运行安装包，Next → I Agree
第 2 步  选择安装用户（任意用户即可）
第 3 步  修改安装路径（避开 C 盘，且路径无特殊字符）
第 4 步  勾选"添加 Anaconda 到系统环境变量"（Add to PATH）
第 5 步  安装完成页：不勾选附加的 VS Code 等推荐项，Finish
```

三个必须注意的坑位：

- **路径别带特殊字符**：安装路径含空格/中文以外的特殊符号，后期创建虚拟环境会莫名报错；
- **必须勾选 Add to PATH**：漏勾的话，开终端敲 `conda` 会提示"找不到命令"；
- **别装 C 盘**：Windows 系统盘空间紧张会拖慢整机，装 D 盘等数据盘。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 安装完敲 conda 提示"不是内部或外部命令" | 大概率是漏勾 Add to PATH，见第 ⑤ 点补配环境变量 |
| 后来创建虚拟环境总报奇怪错误 | 检查安装路径是否含特殊字符，含则重装到干净路径 |
| 安装页推荐装 VS Code 顺手点了 | 不冲突，但会造成"C 盘又胖一块"，可取消勾选 |

@@point ⑤ 安装验证：两步确认装好了
@@need 要解决什么
装完心里没底：到底成没成？以后怎么确认环境是好的？

@@idea 核心思路
打开 PowerShell（或 CMD），依次执行下面两条命令，能出现版本号就是成功：

```bash
conda --version        # 显示 conda 版本号，如 conda 24.x.x
python --version       # 显示 Python 版本号
```

如果 `conda --version` 报"不是内部或外部命令"，而上一步确认勾选过 Add to PATH，可能是 PATH 未刷新——**关掉终端重开**，或重启电脑。仍不行就手动补配环境变量，把 Anaconda 的安装目录和 `Scripts` 目录加进系统 PATH。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `python --version` 有输出但 `conda --version` 没有 | conda 的可执行目录没进 PATH；检查 `安装目录\condabin` 与 `安装目录\Scripts` |
| 重开终端后正常了 | 环境变量只在会话启动时读取一次，属正常现象 |

@@point ⑥ 虚拟环境：为什么一个项目一个环境
@@need 要解决什么
项目 A 依赖 pandas 1.x，项目 B 要 pandas 2.x——**全球装一份，装谁都会坏。** 这就是"环境冲突"。

@@idea 核心思路
虚拟环境 = **独立的 Python 解释器 + 独立的一套软件包**，彼此互不干扰：

- 每个项目一份环境，装什么都不会污染其他项目；
- 环境里只装本项目需要的包，环境更小、部署更快；
- 环境坏了直接删掉重建，不影响机器上的其他东西。

多项目开发的通用约定：**一个项目一个虚拟环境**。conda 在创建虚拟环境时还可以直接指定 Python 版本（`python=3.9`），连"不同项目用不同 Python 版本"也能解决——这是 pip 生态里 venv 做不到的开箱体验。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 所有项目共用一个 base 环境 | 短期省事、长期必炸；库版本冲突只是时间问题 |
| 以为虚拟环境很占空间 | 环境间未共用的包会重复存储，但换来的是绝对的隔离，值得 |

@@point ⑦ conda 虚拟环境基本命令：增删查活用
@@need 要解决什么
环境怎么建、怎么进、怎么退、怎么删？**命令清单必须一次记全。**

@@idea 核心思路
五条命令覆盖整个生命周期：

```bash
conda info --envs                          # 查看已有环境列表（带 * 的是当前环境）
conda create -n myenv python=3.9           # 创建环境，指定 Python 版本
activate myenv                             # 激活/进入环境（Linux/macOS 用 conda activate myenv）
deactivate                                # 退出当前环境
conda remove -n myenv --all                # 删除环境（连同其中所有包）
```

注意两点：

- 新环境默认只装 pip 等必需包，**不是** Anaconda 全家桶；想要全家桶，创建命令末尾加 `anaconda`（`conda create -n myenv python=3.9 anaconda`）；
- 创建的环境默认存放在 Anaconda 安装目录的 `envs` 子目录下。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 激活后终端前缀没变化、命令无效 | 见第 ⑧ 点，PowerShell 有三步修法 |
| 删除环境时提示占用 | 先 `deactivate` 退出该环境再删 |

@@point ⑧ PowerShell 无法激活虚拟环境：三步修
@@need 要解决什么
同样的命令，CMD 里能激活，PowerShell 里却提示"无法加载，因为在此系统上禁止运行脚本"或干脆没反应。**这是 Windows 新手最高频的卡点。**

@@idea 核心思路
PowerShell 激活环境需要满足三个条件，按顺序排查：

```text
第 1 步  放开脚本执行策略（管理员身份开 PowerShell）
        Set-ExecutionPolicy RemoteSigned   然后输入 Y 确认

第 2 步  让 conda 初始化 PowerShell（管理员身份）
        conda init powershell

第 3 步  注意命令版本差异
        conda < 4.6 版本：activate myenv
        conda >= 4.6 版本：conda activate myenv
```

三步做完，**重开一个 PowerShell** 再试。另外如果嫌每次开终端都自动进 base 环境啰嗦，可以关掉自动激活：

```bash
conda config --set auto_activate_base false   # 关闭自动进 base
conda config --set auto_activate_base true    # 恢复
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 提示"禁止运行脚本" | 第 1 步执行策略没设置，或没重开终端 |
| `conda activate` 报"不是内部命令" | 第 2 步 init 没执行，或版本在 4.6 以下应改用 `activate` |
| 终端前缀一直挂着 (base) | 是默认自动激活，无碍；想清爽按上文关掉 auto_activate_base |

@@point ⑨ conda 与 pip 装包管理：两套命令别混
@@need 要解决什么
"装包、查包、卸包"三件事，conda 和 pip 各有一套语法，**记混了就是报错现场**。

@@idea 核心思路
把两套命令并排看，差异一目了然：

| 操作 | conda（推荐数据分析场景） | pip |
|---|---|---|
| 安装 | `conda install 包名` | `pip install 包名` |
| 卸载 | `conda remove 包名` | `pip uninstall 包名` |
| 查看已装 | `conda list` | `pip list` |

为什么数据分析首选 conda？因为 conda 安装时会**同时处理所有依赖**——Python 解释器、C/C++ 库、CUDA 等硬件相关组件、其他语言依赖，都用严格依赖解析器预先检查冲突；而 pip 只管 Python 包、不管理系统级依赖。用 pip 装 GPU 相关或带系统级依赖的包，经常"装得上、跑不起来"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `pip remove xxx` 报错 | 这是错误命令；pip 卸载要用 `pip uninstall` |
| conda 装时提示依赖冲突 | 别硬装，用 `conda install` 让解析器帮你选兼容版本 |

@@summary
这一章你搭好了阶段 17 的第一块地基：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **生态认知**：wheel 解决"现场编译"，conda 解决"跨语言依赖 + 环境隔离" | 弄懂来龙去脉，后面选工具、看报错都有方向 |
| **发行版决策**：Anaconda 全家桶 / Miniconda 轻量 / Miniforge 社区源 / Mamba 加速 | 按自己机器和网络条件选，不盲目跟风 |
| **安装全流程**：路径无特殊字符、勾选 Add to PATH、别装 C 盘 | 三个坑位避开，安装一次到位 |
| **验证方法**：`conda --version` / `python --version` | 确认装好的标准动作 |
| **虚拟环境命令**：create / activate / deactivate / info --envs / remove | 一个项目一个环境，从此告别依赖冲突 |
| **PowerShell 修复术**：执行策略 + conda init + 版本差异 | Windows 上最常卡的一步，三步可解 |

一句话记住本章：**conda 是跨语言的环境与包管理器，Anaconda 是它的全家桶发行版；装好后用虚拟环境隔离每个项目，这就是数据分析最稳的起点。**

@@quiz
1. 早期 `pip install numpy` 经常失败的历史原因是什么？wheel 格式解决了什么？
2. conda 与 pip 最大的两个区别是什么？
3. Anaconda、Miniconda、Miniforge 三者的核心差别是什么？Mamba 是什么？
4. Windows 安装 Anaconda 时，与路径和 PATH 相关的两个坑是什么？
5. 创建 Python 3.9 虚拟环境、进入环境、退出环境、删除环境的命令分别是什么？
6. PowerShell 无法激活虚拟环境，按顺序要检查哪三件事？
7. conda 卸载包和 pip 卸载包的命令分别是什么？`pip remove` 对不对？

@@links
参考|Anaconda 开发环境（34 页）|#
工具|Anaconda 官网|https://www.anaconda.com/
工具|Miniconda（清华镜像）|https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/
文档|conda 官方文档|https://docs.conda.io/