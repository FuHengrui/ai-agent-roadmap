@@h1 第二章　PyTorch 核心库与 GPU 加速环境
@@sub 阶段 21 · 深度学习框架与神经网络架构　|　PyTorch 入门　|　难度 ★☆☆

@@why 这一章在解决什么问题
上一章认识了框架要解决什么问题，这一章就把它装到你的机器上。很多新手在这一步就卡住了：pip 装完还是报错、CPU/GPU 版本分不清、不知道 CUDA 和 cuDNN 是什么。这一章把 PyTorch 的**安装、核心库分工、GPU 加速原理**一次讲清楚——环境通了，后面所有代码才能跑起来。

@@prep 开始之前
要装一个 Python 虚拟环境，再装 PyTorch；没有 NVIDIA 显卡就装 CPU 版，一样能跟着跑。

@@goal 学到这儿就够了
能说清三个库各管什么，能自己装好环境并用 import torch 验证通过，这章就算过了。

@@map 上一章→本章→下一章
上一章讲"框架是干什么的"。**本章落地安装 PyTorch，搞清 torch / torchvision / torchaudio 三个库的分工和 GPU 加速原理**。环境就绪后，下一章开始学 PyTorch 最基本的数据结构——张量。

@@point ① PyTorch 是什么
@@need 要解决什么
PyTorch 在深度学习生态里到底扮演什么角色，为什么本书选它？

@@idea 核心思路
PyTorch 是一个**开源的机器学习库**，主要用于计算机视觉（CV）、自然语言处理（NLP）、语音识别等领域的研究和开发。它由 Facebook（Meta）的人工智能研究团队开发，在机器学习和深度学习社区中广泛使用。

它的两大卖点：
- **灵活性**：动态计算图，边运行边构建网络，调试直观，特别适合研究。
- **易用性**：API 设计贴近 Python 习惯，新手友好。

官网入口：https://pytorch.org/

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 PyTorch 只能做视觉 | 它覆盖 CV、NLP、语音、强化学习等所有主流方向 |
| 把 PyTorch 和 Python 库搞混 | PyTorch 是第三方框架，需要单独安装；且推荐在 conda 虚拟环境中安装，避免污染系统 Python |

@@point ② 三大核心库：torch / torchvision / torchaudio
@@need 要解决什么
PyTorch 装的时候经常看到 torch、torchvision、torchaudio 几个包，它们分别管什么？

@@idea 核心思路
三个库是"核心 + 领域扩展"的分工：

**torch —— 核心库（必装）**
- 张量（Tensor）操作：多维数组，深度学习的数据载体。
- 自动微分（autograd）系统：自动计算梯度，支撑反向传播。
- 优化器（optimizers）：SGD、Adam 等训练算法。
- 大量数学运算，是构建深度学习模型的基础。

**torchvision —— 图像扩展（做视觉任务时必装）**
- 预训练模型：ResNet、VGG 等，可直接用于图像分类、目标检测。
- 图像预处理和增强工具：torchvision 提供 datasets/transforms/models；DataLoader 在 torch.utils.data。

**torchaudio —— 音频扩展（做语音任务时安装）**
- 音频加载、保存、转换、处理，支持多种音频格式。
- 音频预处理、增强工具和相关深度学习模型。

一句话：**torch 打底，图像任务加 torchvision，音频任务加 torchaudio。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只装 torch、跑 torchvision 代码报错 | 每个扩展库要单独安装：`pip install torchvision`；缺少哪个装哪个 |
| 不知道自己的任务该装什么 | 本书主线是全连接网络做表格数据，装 torch 即可；涉及图像时再补 torchvision |

@@point ③ 安装方式：pip 与 conda
@@need 要解决什么
PyTorch 能装，但它到底该怎么装才不出错？

@@idea 核心思路
两种主流方式：

**方式一：pip**
```
pip install torch torchvision torchaudio
```
适合普通 Python 环境；纯 CPU 或按官网给的 CUDA 版本命令安装（GPU 版需要按官网首页选对应 CUDA 版本）。

**方式二：conda**
```
# 官方 conda 频道 2.5（2024-10）后停更，现在推荐用 pip 装 GPU 版
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```
conda 会自动处理依赖和 CUDA 配套库，环境隔离更省心，是教程里的常用推荐方式。

无论哪种方式，**一定要在虚拟环境中安装**（conda create -n 环境名），避免版本冲突污染全局环境。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接 pip 装到系统 Python，后续项目互相冲突 | 养成好习惯：每个项目一个独立虚拟环境（conda env / venv） |
| conda 下载慢或失败 | 用国内镜像源（清华 TUNA、中科大等）加速，或按官网命令配置 channel 优先级 |
| CPU 与 GPU 版本命令搞混 | 无 NVIDIA 显卡就装 CPU 版（更快更稳）；有显卡再按官网 CUDA 版命令装 |

@@point ④ 为什么 GPU 更快：CUDA 是什么
@@need 要解决什么
"GPU 版比 CPU 版快"几乎人人都知道，但更快的原理是什么？CUDA 到底是个啥？

@@idea 核心思路
**CUDA（Compute Unified Device Architecture）** 是显卡厂商 NVIDIA 推出的**通用并行计算架构**，是一个并行计算平台和编程模型。它让 GPU 不再只干图形渲染，还能解决复杂的通用计算问题。

为什么 GPU 适合深度学习：
- CPU 是"少数几个强核心"：擅长复杂逻辑的串行处理。
- GPU 是"成千上万个简单核心"：擅长大量相同运算的并行处理。

而深度学习正好就是**海量张量运算**——矩阵乘法、卷积，全是可并行的重复计算。GPU 把一次大计算拆成几万个小任务同时跑，自然快出一个数量级。

注意：显卡厂商是 NVIDIA 才支持 CUDA；AMD 等显卡用的不是这条路径。可以到 https://developer.nvidia.com/cuda-gpus 查自己的显卡是否支持。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为安装 CUDA 只是"装个驱动" | CUDA 是完整的并行计算平台（驱动 + 运行时 + 工具链）；装完还要配套 cuDNN |
| CPU 版 pytorch 也能跑，就以为 GPU 无所谓 | 效果一样但速度差距大；小 demo 无所谓，模型一大 CPU 训练时间会到不可接受的程度 |
| 装了 GPU 版但代码里没搬到 GPU | 默认数据在 CPU 上，要用 `.to('cuda')` / `.cuda()` 显式搬运，后面章节会教 |

@@point ⑤ cuDNN：为深度学习专门加速的库
@@need 要解决什么
有了 CUDA 还要装 cuDNN，是不是重复了？

@@idea 核心思路
不重复，是"平台 + 专用加速库"的关系：

- **CUDA** 是通用的并行计算平台，一开始并不带深度学习相关的加速库。
- **cuDNN（NVIDIA CUDA Deep Neural Network library）** 是 NVIDIA 专门针对深度神经网络基础操作设计的 **GPU 加速库**，把卷积、池化、归一化等常用操作都优化到极致。

场景对应：
- 只要用 NVIDIA GPU 做深度学习 → 需要 **CUDA + cuDNN** 配套（conda 装 PyTorch GPU 版通常会自动带上，手动装时注意版本匹配）。
- 只用 CPU → 无需 CUDA/cuDNN。

工作速度上 cuDNN 相较 CPU 快很多，是深度学习 GPU 加速的关键组件。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 手动装 CUDA/cuDNN 版本不匹配，运行时各种诡异崩溃 | 优先用 conda 装 PyTorch GPU 版自动配好；手动装配对时严格看官网版本对应表 |
| 以为 cuDNN 会随普通 CUDA 安装自动带 | 不一定；老版本需要单独下载安装，新版本常由框架自动打包，先跑 `torch.__version__` 和 `torch.cuda.is_available()` 验证 |

@@point ⑥ 验证安装：一句话确认环境可用
@@need 要解决什么
装完怎么快速确认"装对了"？总不至于一上来就写个完整模型吧。

@@idea 核心思路
用两行代码验证核心信息和 GPU 可用性：

```python
import torch
print(torch.__version__)          # 当前 PyTorch 版本
print(torch.cuda.is_available())  # CUDA 是否可用（有无 NVIDIA GPU）
```

- `torch.__version__`：能打印版本号 → torch 装好了。
- `torch.cuda.is_available()`：
  - `True` → GPU 可用，后面代码可以 `.to('cuda')` 加速。
  - `False` → CPU 模式，也可以正常学，只是慢一点。

这两行是未来排查环境问题最快的第一手诊断。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `import torch` 直接报错 | 没装成功或 python 解释器不对（装了另一个环境的包）；确认当前激活的环境 |
| 明明有 NVIDIA 显卡但 `is_available()` 是 False | 大概率装了 CPU 版 torch，或驱动/CUDA 不配套；按官网 GPU 版命令重装 |
| 不同环境反复装，版本混乱 | 每次换环境后都先跑这两行确认，再开始干活 |

@@point ⑦ CPU 版与 GPU 版怎么选
@@need 要解决什么
装之前纠结：自己这台机器到底该装 CPU 版还是 GPU 版？

@@idea 核心思路
一个非常实用的决策表：

| 情况 | 建议 |
|---|---|
| 无 NVIDIA 显卡 | 装 **CPU 版**，简单稳定，学习阶段足够了 |
| 有 NVIDIA 显卡 | 装 **GPU 版**（注意 CUDA 版本匹配），训练提速明显 |
| 云平台（如 ModelScope/AutoDL） | 一般是 GPU 环境，按平台教程装对应版本 |
| 只跑小型 demo / 表格数据 | CPU 版体验已经很好，不必纠结 |

记住：**CPU 版和 GPU 版功能完全一样（效果一致），只有速度差别**；先跑通再说性能。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 低配机器装了 GPU 版反而更卡 | 显卡太老或显存小，效果不如 CPU；勇气可嘉但先看显卡型号再决定 |
| "反正以后要 GPU，先装 GPU 版" | GPU 版在无 CUDA 环境会运行失败或回退 CPU，装之前先确认有没有 NVIDIA 显卡 |

@@summary
本章解决了"把 PyTorch 跑起来"的全部前置问题：

| 问题 | 答案 |
|---|---|
| PyTorch 是什么 | Meta 开源机器学习库，研究友好、动态计算图、灵活易用 |
| torch / torchvision / torchaudio | 核心库 + 图像扩展 + 音频扩展，按任务选装 |
| 怎么安装 | pip 或 conda，务必在独立虚拟环境里装 |
| CPU 为什么慢 | CPU 强核心少；GPU 成千上万小核心并行算张量，天然适配深度学习 |
| CUDA 是什么 | NVIDIA 的通用并行计算平台，让 GPU 做通用计算 |
| cuDNN 是什么 | NVIDIA 的深度神经网络专用加速库，卷积等操作更极致地加速 |
| 怎么验证 | `torch.__version__` + `torch.cuda.is_available()` |
| 版本怎么选 | 无 NVIDIA 显卡装 CPU 版；有则 GPU 版；功能一致只有速度差 |

@@point ⑧ 第一个最小示例：跑通就能开工
@@need 要解决什么
环境装完了，怎么确认"真的能用了"？从哪里开始写第一行代码？

@@idea 核心思路
装完环境先跑一个**最小可运行示例**，验证 import 与张量计算通畅：

```python
import torch
print(torch.__version__)            # 版本号，如 2.x.x
print(torch.cuda.is_available())    # GPU 可用性
x = torch.tensor([1.0, 2.0, 3.0])
print(x * 2)                        # 张量基本运算可用
```

只要版本号能打印、张量能算出结果，环境就算"通了"。之后再按"张量→自动微分→模型→训练"的顺序逐章深入（本阶段后续章节正是这个路线）。

**惯例**：把这段存成 hello_pytorch.py，换设备/换环境后先跑它确认可用，再继续干活。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| import torch 报 ModuleNotFoundError | 装到了别的解释器/环境；检查当前 python 与安装时是否同一个环境 |
| 版本号能打但 cuda.is_available() 为 False | 装的 CPU 版或者驱动缺失；画图/小数据 CPU 版也能跑，不必强求 GPU |
| 多个环境迷路 | 用 conda 专属环境隔离，每个项目一个环境，从根上避免 |

一句话记住本章：**PyTorch 由 torch（核心）+ torchvision/torchaudio（扩展）组成，GPU 靠 CUDA+cuDNN 加速，装完用两行代码验证即可开始。**

@@quiz
1. torch、torchvision、torchaudio 三个库的分工分别是什么？做表格数据分类需要装哪些？
2. pip 和 conda 安装 PyTorch 各自的优缺点是什么？为什么建议用虚拟环境？
3. 为什么 GPU 比 CPU 更适合深度学习训练？请从核心数量与任务类型角度解释。
4. CUDA 和 cuDNN 的关系是什么？只装 CUDA 不装 cuDNN 会怎样？
5. `torch.cuda.is_available()` 返回 False 的可能原因有哪些？逐一说明排查思路。
6. 你的机器没有 NVIDIA 显卡，应该装哪个版本？如果之后想用 GPU，可以怎么解决？

@@links
参考|PyTorch入门（PyTorch介绍与安装）|#
文档|PyTorch 官网安装页面|https://pytorch.org/get-started/locally/
文档|NVIDIA CUDA 支持显卡列表|https://developer.nvidia.com/cuda-gpus
工具|CUDA 官网（驱动与工具包）|https://developer.nvidia.com/cuda-downloads