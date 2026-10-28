@@h1 第九章　用 nn.Module 构建模型与前向传播
@@sub 阶段 21 · 深度学习框架与神经网络架构　|　神经网络基础　|　难度 ★★★

@@why 这一章在解决什么问题
手写权重矩阵再自己管理参数更新，工程上太痛苦。PyTorch 提供了 **nn 模块**（torch.nn）把"搭模型"变成搭积木：`nn.Linear` 一行建好线性层并自动登记参数，`nn.Module` 负责组织层与参数、实现前向传播。这一章教你用官方写法构建可训练模型，并理解参数初始化的门道。

@@prep 开始之前
沿用前面的 PyTorch，这章不用装新东西；上一章的激活函数要能说出来，不然搭模型时不知道往哪加。

@@goal 学到这儿就够了
能用 nn.Module 和 nn.Linear 搭出可训练模型，能说清参数是怎么自动登记的，这章就算过了。

@@map 上一章→本章→下一章
上一章理解了神经元与激活函数。**本章把概念落地为代码：用 nn.Module + nn.Linear 搭真实模型，学会管理参数与初始化**。下一章讲损失函数——训练模型的"裁判标准"。

@@point ① nn.Linear：一行代码建一个线性层
@@need 要解决什么
不想手写 `x @ W + b` 和手动维护 W、b，怎么办？

@@idea 核心思路
**`nn.Linear(in_features, out_features)`** 封装了"线性层"的全部：自动创建权重 `fc.weight`（形状 **[out, in]**，前向是 `x @ W.T`）和偏置 `fc.bias`（形状 [out]），并**自动登记为模型参数**：

```python
import torch
import torch.nn as nn

fc = nn.Linear(4, 3)     # 输入 4 维，输出 3 维
x = torch.randn(2, 4)    # batch=2，特征=4
y = fc(x)                # 等价于 x @ W.T + b → (2, 3)
print(fc.weight.shape)   # (3, 4)
print(fc.bias.shape)     # (3,)
```

要点：
- 调用 `fc(x)` 时**自动执行前向**（线性变换），无需手动算矩阵乘。
- 权重自动随机初始化（默认 kaiming_uniform），后续可自定义。
- `bias` 默认 True；不需要时可 `bias=False`（如 BatchNorm 前的层常如此）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 输入特征数写错 | in_features 必须等于输入数据的最后一维；否则前向直接报维度错误 |
| 以为 fc(x) 和 fc.forward(x) 不同 | 官方推荐直接 `fc(x)`，内部还会触发钩子机制；不要手动调 forward（除非特殊场景） |
| 忘记 batch 维 | nn.Linear 自动处理 batch：输入 (N, in) 输出 (N, out)，插入特征维前即可 |

@@point ② nn.Module：所有模型的父类
@@need 要解决什么
多个层怎么组织成一个"完整模型"？参数怎么统一管理、整体迁移到 GPU？

@@idea 核心思路
**所有网络都继承 `nn.Module`**，标准写法四件套：

```python
class MyNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(4, 8)     # 隐藏层
        self.fc2 = nn.Linear(8, 3)     # 输出层

    def forward(self, x):
        h = torch.relu(self.fc1(x))    # 前向：层1 + ReLU
        return self.fc2(h)             # 层2 → 输出
```

`nn.Module` 带来的能力：
- **自动登记参数**：`model.parameters()` 返回全部可学习参数（含所有子模块的）。
- **自动注册子模块**：`self.fc1 = nn.Linear(...)` 后，fc1 的权重自动属于模型。
- 统一的设备管理：`model.to(device)` 一键把全部参数搬到 GPU。
- 自动切换模式：`model.train() / model.eval()`（影响 Dropout/BN 行为）。

**前向逻辑写在 forward 里，反向传播由框架完成**——你只需定义"怎么算"，不用管"怎么更新"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了调用 super().__init__() | 子类无法正常注册参数，各种魔法失效 |
| 在 __init__ 里做张量运算存为普通属性 | 用 nn.Parameter 包装或挂到子模块，否则**不会被 parameters() 收录**、训练不更新 |
| forward 里用非 nn 模块的临时计算 | 没问题，但记得它会参与计算图（需 requires_grad 的部分仍会被反向） |
| 手动遍历参数更新 | 有 optimizer 兜底；自己写的循环容易漏掉 zero_grad/step 顺序 |

@@point ③ nn.Sequential：极简模型组织方式
@@need 要解决什么
层很浅、就是线性堆叠，有没有更简洁的写法？

@@idea 核心思路
**`nn.Sequential`** 把层按顺序串起来，前向自动依次执行：

```python
model = nn.Sequential(
    nn.Linear(4, 8),
    nn.ReLU(),
    nn.Linear(8, 3),
)
y = model(x)   # 自动：Linear → ReLU → Linear
```

适用：**层之间无分支、严格串联**的网络（如简单 MLP、浅层 CNN 主干）。

限制：复杂结构（残差连接、多输入多输出、共享权重）必须用 nn.Module 手写 forward。**顺序模型够用就用 Sequential，复杂就继承 nn.Module**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Sequential 里想加分支/跳跃连接 | 做不到；改用继承 nn.Module 手写 forward |
| 想给 Sequential 中间层单独命名访问 | 用 nn.Sequential 内的 OrderedDict 传名字，或用 module 列表索引 |
| 层顺序写反 | Sequential 严格按定义顺序执行，写反形状就报错 |

@@point ④ 参数查看与统计：模型到底有多大
@@need 要解决什么
搭完模型想看看：有几个参数？在哪定义的？梯度有没有？

@@idea 核心思路
经典三问用三个 API 回答：

```python
for name, p in model.named_parameters():
    print(name, p.shape, p.requires_grad)
# 输出示例：
# fc1.weight (8, 4) True
# fc1.bias   (8,)   True
# fc2.weight (3, 8) True
# fc2.bias   (3,)   True

total = sum(p.numel() for p in model.parameters())
print("总参数量:", total)   # 4*8+8 + 8*3+3 = 67
```

- `named_parameters()`：带名字的参数迭代器。
- `parameters()`：全部参数。
- `numel()`：单个参数的元素个数。
- `named_modules()`：看子模块。

**"总参数量"是判断模型规模、估算显存的第一指标**（显存≈参数量×字节数×优化器状态系数）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 参数名字和预期对不上 | 名字 = 属性路径，如 self.net[0].weight；按嵌套层级理解 |
| 统计参数量想当然 | 手算核对更稳：Linear(in,out) 参数 = in*out + out |
| 分不清参数和缓冲区 | requires_grad=True 的是参数；无需更新的（如 BN 的 running_mean）是 buffer，走 state_dict() 一起保存 |

@@point ⑤ 参数初始化：好的开始是成功的一半
@@need 要解决什么
权重全初始为 0 或全一样会怎样？怎么初始化才不容易卡死或爆炸？

@@idea 核心思路
**对称性问题**：如果同一层所有权重初值相同，反向传播梯度也相同，神经元永远学不成差异化——网络智力被浪费。所以初始化必须**打破对称**且**控制数值范围**。

PyTorch 默认已对 Linear/Conv 用合理初始化（kaiming），也可手动精调：

```python
def init_weights(m):
    if isinstance(m, nn.Linear):
        nn.init.xavier_uniform_(m.weight)   # Xavier：适合 Tanh 类对称激活
        # nn.init.kaiming_uniform_(m.weight) # Kaiming：适合 ReLU 族
        nn.init.zeros_(m.bias)

model.apply(init_weights)
```

两种主流初始化：
- **Xavier（Glorot）**：按输入输出维度均衡放缩，配合 Tanh/Sigmoid 效果好。
- **Kaiming（He）**：考虑 ReLU 负半轴砍半的影响，配 ReLU 效果好。

**原则：激活类型决定初始化方案**；最终层和 bias 常初始化为 0。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 全零/全等初始化 | 对称性问题，网络退化；必须随机且打破对称 |
| 初始化数值太大 | 前向输出炸、梯度爆炸；选对缩放（Xavier/Kaiming）即解决 |
| 激活与初始化不匹配 | ReLU 配 Xavier 偏弱；ReLU 系配 Kaiming、Tanh 配 Xavier |
| 忘了 .apply 或传参写错 | apply 对所有子模块执行回调；isinstance 判类型再初始化对应层 |

@@point ⑥ train 与 eval：模式切换影响什么
@@need 要解决什么
模型训练完拿去预测，为什么结果可能"不一样"？

@@idea 核心思路
同一个模型有**两种模式**，直接影响部分层的行为：

```python
model.train()   # 训练模式：Dropout 生效（随机丢弃）、BN 用当前 batch 统计
model.eval()    # 评估模式：Dropout 停用、BN 用累计的 running 统计
```

- **Dropout**：训练时随机丢弃部分神经元防过拟合；评估时必须关闭，否则预测变成随机噪声。
- **BatchNorm**：训练时用 batch 均值方差；评估时用训练期间累计的全局统计。

**惯例**：train 前调 model.train()，验证/测试/推理前调 model.eval()。别忘了，否则预测结果漂移且不稳定。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 推理忘记 .eval() | Dropout 还在随机丢弃，两次预测结果不同——**这是排查"预测不稳定"的第一嫌疑** |
| train 之后没切 eval 就测试 | 同上；规范流程：训练循环内 train，评估循环前 eval |
| 以为 eval 等于 no_grad | 两者独立：eval 管层的模式，no_grad 管是否建计算图；推理常用 eval + no_grad 组合 |

@@summary
用 nn.Module 构建模型的要点：

| 问题 | 答案 |
|---|---|
| nn.Linear | 一行线性层：自动建 W/b、自动登记参数、fc(x) 自动前向 |
| nn.Module | 所有模型的父类：自动管理子模块与参数，统一 .to(device)/train()/eval() |
| 标准写法 | __init__ 定义层 + super().__init__()，forward 定义前向 |
| Sequential | 纯串联网络的最简写法；复杂结构用继承手写 forward |
| 查参数 | named_parameters()/parameters()/numel()；总参数量 ≈ 显存估算基准 |
| 初始化 | 打破对称 + 控制范围：ReLU 配 Kaiming、Tanh 配 Xavier |
| train/eval | train 开 Dropout、BN 用 batch 统计；eval 关 Dropout、用全局统计 |

@@point ⑦ 设备管理：model.to(device) 与 CPU/GPU 无缝切换
@@need 要解决什么
代码想先在 CPU 上跑通、再上 GPU 加速，怎么不写两套代码？

@@idea 核心思路
用 **`model.to(device)` + `tensor.to(device)`**，一套代码两个平台跑：

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = MyNet().to(device)     # 模型全部参数搬到设备
x = x.to(device)               # 数据也搬到同一设备
y = model(x)                   # 前向自动在设备上执行
```

关键规则：
- **模型参数和输入张量必须在同一设备**，否则前向报 "Expected all tensors to be on the same device"。
- `model.to(device)` 会把所有子模块参数、buffer 一次性搬走（nn.Module 自动管理）。
- CUDA 上训练前先跑通 CPU 版本，逐段加 `.to(device)`，便于定位设备不一致的报错位置。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| device mismatch 报错 | 模型或某个张量漏了 .to(device)；统一在数据入口处转换 |
| 标签也要搬 | 计算损失时 pred 与 y 也须同设备；标签同样 .to(device) |
| 搬完还用旧引用 | .to() 返回**新**对象，要赋值接收：model = model.to(device) |

@@point ⑧ 模型保存与加载：state_dict 的正确打开方式
@@need 要解决什么
训练了几个小时，怎么把成果存下来、下次接着用？

@@idea 核心思路
**只存参数（state_dict）** 是推荐做法：

```python
torch.save(model.state_dict(), "model.pt")        # 保存参数

model = MyNet()                                    # 先重建结构
model.load_state_dict(torch.load("model.pt"))      # 再灌参数
model.eval()                                       # 推理前切评估模式
```

- `state_dict()` 是"参数名 → 参数值"的映射，不包含网络结构。
- 加载时必须**先有相同的模型结构**，再 load 参数。
- 推理前 `model.eval()`（关 Dropout/BN 用全局统计，第⑥点讲过）。

若还想存训练进度（epoch、优化器状态、损失历史），打包成一个字典：

```python
torch.save({"epoch": 10, "model": model.state_dict(),
            "optim": optimizer.state_dict()}, "ckpt.pt")
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| load_state_dict 报 key 不匹配 | 结构不一致（层数/名字不同）；确保重建结构与保存时完全一致 |
| 直接 torch.save(model) 存整个对象 | 不推荐：结构耦合死板，换环境易碎；存 state_dict 更通用 |
| 加载后忘了 eval() | 推理结果漂移；加载完训练就 train()、推理就 eval() |

一句话记住本章：**继承 nn.Module、在 __init__ 里用 super().__init__() 登记层、在 forward 里写前向；层用 nn.Linear/nn.Sequential，参数靠 model.parameters() 统一管理；初始化打破对称按激活选 Xavier/Kaiming，训练和评估记得切 train()/eval()。**

@@quiz
1. nn.Linear(4, 3) 创建了哪些参数？形状分别是什么？前向时输入 (N,4) 输出是什么形状？
2. 自定义模型继承 nn.Module 时，为什么必须调用 super().__init__()？
3. 在 __init__ 里用一个普通 Tensor 存参数会有什么问题？怎么正确声明可学习参数？
4. nn.Sequential 适合什么结构？什么场景必须改用继承 nn.Module 手写 forward？
5. 如何统计一个模型的全部参数量？Linear(in,out) 的参数量公式是？
6. Xavier 与 Kaiming 初始化分别适合什么激活函数？为什么？
7. model.train() 与 model.eval() 分别影响哪些层？预测前忘记 eval() 会观察到什么现象？

@@links
参考|神经网络基础(1)（模型构建与初始化部分）|#
文档|PyTorch nn.Module 官方文档|https://pytorch.org/docs/stable/generated/torch.nn.Module.html
文档|PyTorch 参数初始化函数集合|https://pytorch.org/docs/stable/nn.init.html