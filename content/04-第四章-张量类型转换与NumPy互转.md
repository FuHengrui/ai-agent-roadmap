@@h1 第四章　张量类型转换与 NumPy 互转
@@sub 阶段 21 · 深度学习框架与神经网络架构　|　PyTorch 入门　|　难度 ★☆☆

@@why 这一章在解决什么问题
训练数据常常以 NumPy 数组的形式存在（比如读文件、做数据分析得到的都是 ndarray），而模型只认张量；反过来，分析结果、可视化又想要 NumPy。这一章解决两个高频需求：**张量数据类型怎么换、张量和 NumPy 怎么互相倒腾**，并且讲清最容易踩的两个坑：转换精度损失和共享内存。

@@map 上一章→本章→下一章
上一章学了张量的创建与数据类型。**本章学类型转换（.to/.type/.type_as）和张量↔NumPy 互转**。下一章进入运算：四则运算、矩阵乘法、广播机制——神经元里计算的核心部件。

@@point ① 查看数据类型：.dtype
@@need 要解决什么
拿到一个张量，怎么知道它是什么类型？

@@idea 核心思路
每个张量都有 **`.dtype` 属性**，返回 torch.dtype 对象。常见的：

| 代码 | 实际类型 |
|---|---|
| torch.float32 / torch.float | 32 位浮点（默认） |
| torch.float64 / torch.double | 64 位浮点 |
| torch.float16 / torch.half | 16 位浮点（半精度） |
| torch.int32 / torch.int | 32 位整数 |
| torch.int64 / torch.long | 64 位整数 |
| torch.int16 / torch.short | 16 位整数 |
| torch.int8 / torch.uint8 | 8 位（无符号）整数 |
| torch.bool | 布尔 |

```python
float_tensor = torch.tensor([1.0, 2.0, 3.0])
print(float_tensor.dtype)   # torch.float32
```

**排查"dtype 不匹配"报错的第一步永远是打印 .dtype。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 想用 `.type` 当属性获取类型 | 属性是 `.dtype`；`.type()` 是**方法**，用来做转换（下一知识点） |
| float 全写 torch.float32 嫌长 | torch.float 就是 float32 的别名，二者等价 |

@@point ② 类型转换三兄弟：.to() / .type() / .type_as()
@@need 要解决什么
张量类型不对（比如损失函数要求 long 标签），怎么换？

@@idea 核心思路
三种常用方法：

| 方法 | 用法 | 特点 |
|---|---|---|
| `tensor.to(dtype)` | `t.to(torch.int32)` | **全能**：既能转换类型也能移动设备；仅想转类型可不给设备 |
| `tensor.type(dtype)` | `t.type(torch.double)` | 功能与 .to 类似，只负责类型转换 |
| `tensor.type_as(other)` | `t.type_as(ref)` | 把类型改成与另一张量一致 |

```python
f = torch.tensor([1.0, 2.0, 3.0])     # float32
i = f.to(torch.int32)                 # → int32（小数被截断）
d = i.type(torch.double)              # → float64
back = d.type_as(i)                   # → 跟随 i 变回 int32
```

注意：**这几个方法都返回新张量，不会原地修改原张量**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `.to()` 只用于转设备、`.type()` 只转类型 | .to() 既能转设备也能转类型；.type() 专注类型；二者在类型转换上等价 |
| 以为转换会原地生效 | 它们都**返回新张量**；需要原地改就重新赋值（t = t.to(...)） |
| 以为 .type_as 与 .type 一样 | type_as 的参照是"另一张量"而非目标类型名，写法不同 |

@@point ③ 转换的四个代价：精度、溢出、内存、性能
@@need 要解决什么
类型转换看起来很简单，实际转换时要注意什么？

@@idea 核心思路
四个必须记住的后果：

1. **精度损失**：从高精度（float64）转低精度（float32/int32），小数丢失。
2. **数值溢出**：浮点转整数，超出范围会溢出成奇怪的值。
3. **内存占用**：不同 dtype 字节数不同，float16 是 float32 的一半。
4. **计算性能**：GPU 上通常 float32 最佳；float16 还能进一步加速省显存。

**转换的本质是"换一种存储和解释方式"，必然伴随信息取舍。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| float64 转 int 数据全变 0/1 | 你没指定取舍规则，小数直接被截断；需要四舍五入先 round 再转 |
| 大数转 int 出现负数/乱值 | 溢出！int8 最大才 127，超出就翻转；转之前评估数值范围 |

@@point ④ 为什么需要张量 ↔ NumPy 转换
@@need 要解决什么
张量好好的，为什么还要转成 NumPy 数组？反过来又为什么要转回张量？

@@idea 核心思路
两边各有优势，转换是为了"用对方的长处"：

| 场景 | 为什么转 |
|---|---|
| 张量 → NumPy | 图像、音频数据在 NumPy 生态里处理更方便（如 OpenCV 图像库、数据分析工具），生态更成熟 |
| NumPy → 张量 | PyTorch 张量支持 GPU 快速计算，模型训练只认张量 |

**典型工作流**：数据用 NumPy 准备/分析 → 转成张量进模型 → 训练或推理结果再转回 NumPy 做可视化或业务处理。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 全程只用一种结构 | 可行但别扭；学转换是为了让数据在"分析生态"和"训练生态"之间顺畅流动 |
| 忘了 NumPy 主要是 CPU 计算 | 转回 NumPy 会脱离 GPU 加速；只在确需 NumPy 功能时才转 |

@@point ⑤ 张量 → NumPy：.numpy() 与共享内存
@@need 要解决什么
张量怎么变成 NumPy 数组？转换后两边是独立的吗？

@@idea 核心思路
**`tensor.numpy()`** 一行搞定，但两个前提要注意：
1. **张量必须在 CPU 上**：GPU 上的张量先 `.cpu()` 再转。
2. **共享内存**：转换后的 NumPy 数组与原张量**共享底层内存，改一个另一个同步变**；不想共享就 `.numpy().copy()`。

```python
tensor_cpu = tensor.cpu()               # GPU 先回 CPU
numpy_array = tensor_cpu.numpy().copy() # 拷贝隔离，互不影响
numpy_array[0][0] = 5                   # 此时原张量不受影响
```

**"共享内存"既是便利也是陷阱**：想要独立副本，务必 .copy()。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| GPU 张量直接 .numpy() 报错 | 先 `.cpu()`；只有 CPU 张量能转 NumPy |
| 改了 NumPy 发现张量也变了，怀疑 bug | 这是共享内存的预期行为；要隔离用 `.numpy().copy()` |
| 反复转换造成性能损耗 | 转换有拷贝/同步开销，别在训练循环里频繁互转 |

@@point ⑥ NumPy → 张量：from_numpy 与 torch.tensor
@@need 要解决什么
把 NumPy 数组喂给模型，怎么变成张量？两种方法有什么差别？

@@idea 核心思路
两种方式，**关键差异还是共享内存**：

| 方法 | 内存行为 |
|---|---|
| `torch.from_numpy(ndarray)` | **共享内存**：改张量会影响原数组 |
| `torch.tensor(ndarray)` | **不共享**：创建独立拷贝 |

```python
numpy_array = np.array([[1, 2, 3], [4, 5, 6]])
t1 = torch.from_numpy(numpy_array)  # 共享
t2 = torch.tensor(numpy_array)      # 拷贝，独立
```

需要"分析完直接进模型、改完两端同步"用 from_numpy；需要"保住原始数组不被模型弄脏"用 torch.tensor。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 数据预处理改了张量，NumPy 原数组跟着变 | from_numpy 共享内存；不想要就用 torch.tensor |
| 忘了 import numpy | 每个用到 np 的文件都要 `import numpy as np` |
| 用 torch.tensor 包裹大数组重复拷贝 | 大数据量大时 from_numpy 零拷贝更省内存；按需选 |

@@point ⑦ 转换场景实操：图像数据的两端倒腾
@@need 要解决什么
上面都是概念，真实项目里这套转换是怎么用的？

@@idea 核心思路
以图像处理为例，一套典型流程：

```python
import cv2  # NumPy 生态的图像库
img = cv2.imread('photo.jpg')            # 得到 NumPy 数组
tensor = torch.from_numpy(img).to(device)  # 转张量进模型
result = model(tensor)                    # 模型推理
result_np = result.cpu().numpy()          # 结果回 NumPy 可视化
```

**套路固定**：读入（NumPy）→ 入模（张量+GPU）→ 出模（回 CPU/NumPy），中间靠 .to/.cpu()/.numpy()/from_numpy 衔接。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 结果张量在 GPU 上直接转 NumPy | 报错；先 .cpu() 再 .numpy() |
| 数据类型、通道顺序没对齐 | 图像库多数是 HWC、模型常要 CHW；转换前后记得 .permute 换维度顺序（后面章节会讲） |

@@point ⑧ 本章记住的三条黄金法则
@@need 要解决什么
转换操作一大堆，怎么快速记住核心要点？

@@idea 核心思路
把这一章浓缩成三句话：
1. **查看类型看 .dtype，转换类型用 .to()/type()，对齐类型用 .type_as()。
2. **GPU 张量转 NumPy 前必须先 .cpu()**。
3. **想数据共享用 .numpy()/.from_numpy，想独立副本就 .copy()/torch.tensor()**。

这三条覆盖了 90% 的类型/生态转换场景，其余都是特例。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 规则记得住但代码里总漏 | 把这些写成小工具函数封装（如 to_numpy(t)），一劳永逸 |
| 遇到"奇怪报错"先怀疑转换 | 打印 .dtype 与 .device，10 秒定位问题根源 |

@@summary
本章打通了张量类型与 NumPy 生态的转换：

| 问题 | 答案 |
|---|---|
| 查看类型 | .dtype 属性 |
| 转换类型 | .to(dtype)（也管设备）、.type(dtype)，均返回新张量 |
| 对齐类型 | .type_as(参照张量) |
| 转换的代价 | 精度损失、数值溢出、内存变化、性能影响 |
| 为什么要互转 | NumPy 分析生态 vs 张量训练生态，各取所长 |
| 张量→NumPy | .numpy()，需先 .cpu()，共享内存可 .copy() 隔离 |
| NumPy→张量 | from_numpy 共享内存；torch.tensor 独立拷贝 |
| 实战套路 | 读入 NumPy → from_numpy 入模 → 推理 → .cpu().numpy() 出模 |

一句话记住本章：**看类型用 .dtype、换类型用 .to/.type/.type_as；张量与 NumPy 互转用 .numpy()/.from_numpy，看清"共享内存"决定要不要 .copy()。**

@@quiz
1. 打印一个张量的数据类型应该用哪个属性？常见浮点类型的别名有哪些？
2. .to()、.type()、.type_as() 三种方法各自最典型的用法是什么？它们会原地修改张量吗？
3. 类型转换可能带来哪四类后果？请各举一个例子。
4. GPU 上的张量为什么不能直接 .numpy()？正确步骤是什么？
5. tensor.numpy() 之后修改数组，原张量会变化吗？怎么避免？
6. torch.from_numpy 与 torch.tensor(ndarray) 在内存行为上有什么区别？各自适合什么场景？
7. 请写出"NumPy 数据 → GPU 张量 → 模型推理 → NumPy 结果"的完整代码骨架（含必要的 import）。

@@links
参考|PyTorch入门（张量类型转换与NumPy互转）|#
文档|NumPy 官方文档|https://numpy.org/doc/stable/
文档|PyTorch tensor 转换相关文档|https://pytorch.org/docs/stable/generated/torch.Tensor.numpy.html