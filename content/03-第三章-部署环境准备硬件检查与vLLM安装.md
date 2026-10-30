@@h1 第三章　部署环境准备：硬件检查与 vLLM 安装
@@sub 阶段 24 · 大模型时代的模型运维与部署　|　环境搭建　|　难度 ★★☆

@@why 这一章在解决什么问题
选型定了 vLLM，接下来就是**环境**：跑大模型服务器不是随便一台机器都行——GPU 型号、显存大小、CUDA 版本都有硬门槛；装库也有讲究（venv 隔离、pip 安装）。本章给出**可照抄的部署环境清单与安装步骤**，让环境这一步不踩坑。

@@prep 开始之前
要有 NVIDIA 显卡、24GB 显存，驱动支持的 **CUDA ≥ 所装 wheel 的 cuXXX**（当前默认 cu128，见下面的表），Windows 建议走 WSL2 或云 GPU。

@@goal 学到这儿就够了
能用 nvidia-smi 判断机器够不够、能建好虚拟环境并装通 vLLM，这一章就算过了。

@@map 上一章→本章→下一章
上一章完成了 vLLM 特性与选型对比。**本章进入实操第一步：硬件要求核对、Python 虚拟环境准备、vLLM 安装**。下一章讲模型下载与启动部署参数。

@@point ① NVIDIA GPU 与显存门槛：先查硬件再谈部署
@@need 要解决什么
装 vLLM 之前，机器应该满足什么硬件条件？

@@idea 核心思路
硬件底线：

| 硬件项 | 要求 |
|---|---|
| GPU | NVIDIA（CUDA 生态） |
| 显存 | ≥ 24GB（7B 跑 FP16；13B 要 INT4 量化才塞得下） |
| CUDA | 跟 wheel 走：装 cu128 就要 CUDA 12.8 的驱动，装 cu124 就要 12.4（别把 12.1 当统一门槛） |

为什么 24GB：7B 模型 FP16 权重≈14GB，再算上 KV 缓存与激活，"刚好塞进 24GB"是能流畅服务的最低线。**显存是部署的第一约束**，模型/位宽/并发全围绕它设计。

补充常识：

```
预估显存 ≈ 权重大小(参数量×精度字节) + KV缓存 + 激活
例: 7B × FP16(2字节) ≈ 14GB → 24GB 卡勉强
    7B × INT4(0.5字节) ≈ 3.5GB → 量化后小卡也能跑
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只看 GPU 型号不看显存 | 同代卡显存差异巨大，显存才是决定性指标 |
| 用 INT4 权重占用来预估 FP16 | 精度不同权重占用差 4 倍，估算前先定精度 |
| 无视 CUDA 版本 | 版本过低装不上/跑不动新内核，先 `nvidia-smi` 查 CUDA |

@@point ② 用 nvidia-smi 检查 GPU 与驱动
@@need 要解决什么
第一步动手：怎么确认机器 GPU/CUDA 达标？

@@idea 核心思路
在终端执行：

```
nvidia-smi
```

输出应包含：

- **Name**：GPU 型号（如 RTX 4090、A100）。
- **Memory-Usage**：总显存/已用显存（验证 ≥24GB）。
- **CUDA Version**：驱动**能支持的最高** CUDA 版本；它必须 ≥ 你要装的那个 cuXXX wheel 的版本。

如果 `nvidia-smi` 找不到：说明没有 NVIDIA 驱动/显卡，vLLM 无法工作，需要先装驱动或用 CPU 替代方案（vLLM 基本不适用）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把驱动 CUDA 当运行库 CUDA | nvidia-smi 显示的是驱动支持上限，容器内还要装对应 CUDA 运行库 |
| 显存被其他进程占满 | 部署前 `nvidia-smi` 看已用显存，避免"显存够但被占"的假象 |

@@point ③ CUDA 版本门槛到底怎么算
@@need 要解决什么
为什么 vLLM 对 CUDA 版本有硬要求？

@@idea 核心思路
**CUDA 是 NVIDIA GPU 的编程接口**，vLLM 的高性能内核（PagedAttention 等）依赖它编译/运行：

- **版本太低**：无法调用新算子/新指令，甚至编译失败。
- **版本匹配**：驱动**支持的最高 CUDA 版本** ≥ 运行库 CUDA 版本 ≥ 框架编译版本（驱动版本号是 5xx.xx，和 CUDA 版本号不是一个量纲，别直接比大小）（驱动向下兼容，运行库要求写在 vLLM 文档里）。

官方预编译 wheel 现在默认配 cu128（较老的版本是 cu124 / cu121，11.8 只存在于更老的版本）。所以核对时按 **≥ 你装的那个 cuXXX** 看，驱动比运行库新一点没关系——越新对新一代 GPU 与算子的支持越好。注意分清三层：**驱动（driver）≥ 运行库（runtime）≥ PyTorch/vLLM 编译版本**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只装驱动不装 CUDA 工具包 | vLLM 通过 PyTorch 依赖 CUDA 运行库，容器镜像（如 NVIDIA NGC）能省不少事 |
| 版本号记混 | 记住"驱动>运行库>框架"的版本金字塔，从上往下兼容 |

@@point ④ Python 虚拟环境（venv）：隔离是惯例
@@need 要解决什么
为什么安装前要建虚拟环境？怎么建？

@@idea 核心思路
vLLM 依赖的 PyTorch 等包版本敏感，**直接装进系统 Python 容易与其他项目冲突**（依赖地狱）。标准做法：为 vLLM 单独建虚拟环境。

```
python -m venv vllm_env        # 创建
source vllm_env/bin/activate   # 激活（Windows PowerShell: .\vllm_env\Scripts\Activate.ps1（cmd 用 activate.bat））
```

之后所有 `pip install` 都只影响该环境，互不污染。用 conda 也行，顺序不一样：`conda create -n vllm_env python=3.11` 建，再 `conda activate vllm_env` 激活。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 跳过 venv 直接装 | 升级其他包时可能把 vLLM 依赖冲垮，生产环境必须隔离 |
| 激活后忘了在当前终端 | 换个终端窗口要重新 activate，否则 pip 还装进旧环境 |

@@point ⑤ 安装 vLLM：一条命令
@@need 要解决什么
虚拟环境就绪后，装 vLLM 的命令是什么？

@@idea 核心思路
核心命令：

```
pip install vllm
```

装完验证：

```
python -c "import vllm; print(vllm.__version__)"
```

注意事项：

- 首次安装会拉取 PyTorch、CUDA 相关大包，**体积大、耗时长**，耐心等待。
- 网络不稳可换国内镜像源（如清华源）加速。
- 遇到 Python 版本不匹配时，按 vLLM 文档要求选对应 Python（通常 3.10~3.12）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 安装超时直接重试 | 改用国内镜像/加长超时更有效，别原地反复重试 |
| 用错 Python 版本 | 过高或过低的 Python 往往装不上最新 vLLM，查官方支持矩阵 |

@@point ⑥ 常见安装报错与对策
@@need 要解决什么
装 vLLM 时最常遇到的坑是什么？怎么破？

@@idea 核心思路
高频问题清单：

| 报错现象 | 原因 | 对策 |
|---|---|---|
| 找不到 CUDA 相关依赖 | 缺运行库 | 装 CUDA 工具包或用 NGC 容器 |
| PyTorch 版本冲突 | vLLM 要求特定 torch | `pip install vllm` 会自动解析，避免手动先装 torch |
| 内存不足/编译失败 | 构建过程吃资源 | 用官方预编译 wheel（默认），别走源码编译 |
| Python 版本过旧 | 超出支持范围 | 升到 3.10~3.12 区间（3.13 还没跟上） |

总体原则：**优先用官方预编译包**，生产环境考虑 Docker/NGC 镜像，能避开 90% 的环境问题。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 一报错就清环境重装 | 先读报错定位（缺库/版本/资源），对症下药才快 |
| 用源码编译尝鲜 | 编译 vLLM 内核很慢且依赖复杂，无特殊需求一律用官方 wheel |

@@point ⑦ Windows 上的特别提醒
@@need 要解决什么
在 Windows 机器上装 vLLM 有什么要注意的？

@@idea 核心思路
vLLM 生态主要在 Linux：官方预编译与容器镜像都以 Linux 为准。Windows 注意事项：

1. **官方支持有限**：Windows 上 vLLM 需要手动编译或借助 WSL2/Linux 容器，不推荐直接装。
2. **推荐路线**：Windows → WSL2（Ubuntu）→ vLLM；或直接 Linux 服务器/NGC 容器。
3. 本书默认 **Linux 服务器/云 GPU 环境**，请按对应 shell 命令执行。

如果坚持 Windows 直装：需满足 CUDA 环境与编译器，按官方 issue/文档折腾，成本高。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 默认 Windows 直接 pip 就能跑 | vLLM 对 Windows 支持弱，先确定目标平台再决定安装路径 |
| 混用 WSL 与 Windows 路径 | WSL 内是独立 Linux 文件系统与 Python，别把两者环境混记 |

@@point ⑧ 本章小结：环境三步走
@@need 要解决什么
把环境准备阶段浓缩成可执行清单。

@@idea 核心思路
环境三步走：

```
① 硬件核对
   nvidia-smi → GPU型号 / 显存≥24GB / CUDA≥所装 wheel 的 cuXXX（默认 cu128）
② 环境隔离
   python -m venv vllm_env → activate
③ 安装验证
   pip install vllm → python -c "import vllm"
```

这三步完成即具备跑 vLLM 的前提。Windows 用户走 WSL2/容器；Linux/云 GPU 用户直接执行。下一步：下载模型、启动服务。

@@summary
这一章把部署环境讲成了可照抄的清单：

| 步骤 | 动作 | 达标线 |
|---|---|---|
| 硬件核对 | nvidia-smi | NVIDIA GPU、显存≥24GB、CUDA≥所装 wheel 的 cuXXX |
| 环境隔离 | python -m venv + activate | 独立环境 |
| 安装 | pip install vllm | import vllm 成功 |

平台提醒：Linux/云 GPU 首选；Windows 建议 WSL2 或容器。

一句话记住本章：**部署环境三步走：①nvidia-smi 核对硬件——NVIDIA GPU、显存≥24GB（7B FP16 权重就占 14GB 再加 KV 缓存）、CUDA≥12.1（记住驱动>运行库>框架的版本金字塔）；②建 Python 虚拟环境隔离依赖（python -m venv + activate）；③pip install vllm 后 import 验证；Windows 用户建议走 WSL2/容器，Linux/云 GPU 直装最顺——环境对了，后面部署才谈得上。**

@@quiz
1. vLLM 部署的硬件底线是什么？24GB 显存能跑多大的模型、再大要怎么办？
2. 预估模型部署显存占用的大致公式是什么？7B 模型 FP16 权重约占多少？
3. nvidia-smi 输出中要核对哪三个信息？
4. CUDA 版本门槛到底看什么？"驱动、运行库、框架"三者的关系是什么？
5. 为什么要建 Python 虚拟环境？创建与激活的命令分别是什么？
6. 安装 vLLM 的核心命令是什么？遇到网络慢怎么处理？
7. Windows 上装 vLLM 的正确姿势是什么？为什么？

@@links
参考|部署（章节1-2）|#
站点|vLLM 官方安装文档|https://docs.vllm.ai/en/latest/getting_started/installation.html