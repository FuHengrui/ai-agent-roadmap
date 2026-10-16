@@h1 第七章　自动微分：PyTorch 的核心魔法
@@sub 阶段 21 · 深度学习框架与神经网络架构　|　PyTorch 入门　|　难度 ★★☆

@@why 这一章在解决什么问题
训练神经网络靠的是梯度下降，而梯度就是"损失函数对每个参数的偏导数"。真实模型动辄几百万个参数，手推偏导根本不现实。这一章讲 PyTorch **自动微分（Autograd）**：它是怎么自动算出所有梯度的、`requires_grad` 和 `backward` 怎么用、手动推导和自动计算的结果为什么一致——并以一个**房价预测模型**为案例跑通完整闭环。

@@map 上一章→本章→下一章
上一章学完张量的索引与形状变换。**本章进入框架最核心的自动微分：用 PyTorch 自动算梯度，并用房价回归实战把"数据→模型→损失→梯度"跑通**。下一章补全训练另一半：优化器与完整训练循环（线性回归案例）。

@@point ① 训练神经网络到底要算什么
@@need 要解决什么
"训练"这个词背后，计算机到底在做什么重复动作？

@@idea 核心思路
训练 = **反复调整参数，让损失变小**。要调参数，就得知道"每个参数该往哪个方向变、变多少"。这个信息正是**损失函数对该参数的偏导数（梯度）**：

- 梯度为负 → 参数增大能降低损失 → 参数应该增大。
- 梯度为正 → 参数应该减小。

于是训练的核心循环就三件事：**前向算损失 → 反向算梯度 → 更新参数**。反向算梯度这一步，就是自动微分要解决的。

**关键点：模型参数越多，手动求导越不可行**。两个手推还行，几百万个参数必须自动化。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为训练是"找公式求最优解" | 深度学习没有解析解，只有**迭代逼近**：无数轮"算损失→算梯度→更新" |
| 梯度方向理解反 | 梯度指向损失**增大**的方向，所以更新参数要往**反方向**走（梯度下降） |

@@point ② 自动微分是什么：不用手推公式
@@need 要解决什么
PyTorch 的自动微分模块 Autograd 到底帮我做了什么？

@@idea 核心思路
**Autograd 是 PyTorch 的核心组件**，基于**动态计算图**自动计算梯度：

1. 前向计算时，PyTorch 会**记录每一步运算**，形成一张"计算图"（数据怎么从输入流到损失）。
2. 调用 `backward()` 时，利用**链式法则**从损失反向一路算出每个参数的梯度。
3. 我们**无需手动推导和编写求导代码**，模型参数再多也能自动算。

计算图里：输入经过乘法、加法等运算得到预测，再与真实标签算损失；其中的参数（如 w、b）就是"需要梯度的节点"。

**动态图**意味着"边运行边建图"，调试直观、写起来像普通 Python——这是 PyTorch 相对静态图框架的最大优势。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为自动微分会"记住结果" | 它记住的是**运算关系（计算图）**，不是数值结果；图在 backward 后可释放 |
| 把反向传播理解成玄学 | 本质是**链式法则的自动实现**：逐层把输出误差往回传 |
| 以为 autograd 只属于 PyTorch | 所有主流框架都有自动微分；PyTorch 的卖点是动态图更灵活 |

@@point ③ requires_grad：给参数打上"要梯度"标记
@@need 要解决什么
怎么告诉 PyTorch"这个张量是参数，需要算它的梯度"？

@@idea 核心思路
创建张量时设置 **`requires_grad=True`**，或事后 `.requires_grad_(True)`：

```python
w = torch.tensor([1.5], requires_grad=True)  # 参数：要梯度
b = torch.tensor([10.0], requires_grad=True) # 参数：要梯度
x = torch.tensor([50.0])                     # 输入：不要梯度
```

- **模型参数**（权重、偏置）都必须 requires_grad=True。
- **输入数据/标签**通常不需要梯度。

只有"从需要梯度的张量经过运算得到的结果"才能 backward 出梯度。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| backward 报 "does not require grad" | 沿计算路径上没有 requires_grad=True 的张量；检查参数是否标记 |
| 数据张量也设了 requires_grad | 白白多算梯度、拖慢训练；数据默认不需要 |
| 之后想关闭梯度（推理时） | `with torch.no_grad():` 包住推理代码，省内存省时间 |

@@point ④ loss.backward()：一条命令拿到所有梯度
@@need 要解决什么
损失算出来了，怎么一次性算出所有参数的梯度？

@@idea 核心思路
**`loss.backward()`** 一行完成对整个计算图的反向传播。之后梯度会**自动填充到参数张量的 .grad 属性**里：

```python
predicted = house_size * w + b          # 前向
loss = torch.nn.MSELoss()(predicted, real_price)  # 损失
loss.backward()                          # 反向，自动算梯度
print(w.grad, b.grad)                    # 梯度在这里！
```

关键在于：**你只写前向代码，反向的链式求导全交给框架**。这就是自动微分最直接的价值体现。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| backward 只能在标量损失上调用 | 损失必须是标量（0 维）；若损失是向量，先 .sum() 或 .mean() |
| 忘了 .grad 从哪来 | .grad 是 backward 的"产物"，且与参数一一对应 |
| 梯度为 None | 说明该张量不参与计算图（可能被 detach 或未设 requires_grad） |

@@point ⑤ 梯度累积与清零：为什么 optimizer.zero_grad()
@@need 要解决什么
每次 backward 都会把梯度"加"到 .grad 上，重复训练时不清理会怎样？

@@idea 核心思路
**PyTorch 默认累加梯度**：第二次 backward 会把新梯度加到已有梯度上（这种设计支持梯度累积技巧）。

所以标准训练循环里必须**每轮先清零**：

```python
optimizer.zero_grad()   # 把参数 .grad 清零
loss.backward()         # 算本轮的梯度
optimizer.step()        # 用梯度更新参数
```

**忘记 zero_grad 是新手最经典的 bug**：梯度越滚越大，训练直接发散。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 损失曲线跳来跳去或越来越大 | 先查是否漏了 optimizer.zero_grad() |
| 想手动累积梯度（如小 batch 模拟大 batch） | 这是梯度累积技巧：故意不清零连续 backward 数次再 step 一次 |
| zero_grad 放在哪一步 | 每轮训练：**zero_grad → forward → loss → backward → step** |

@@point ⑥ 手动推导 vs 自动微分：房价模型对比
@@need 要解决什么
自动微分结果可信吗？怎么验证它算对了？

@@idea 核心思路
用一个简单房价模型做**对照实验**——同样的参数，手动推公式 vs 自动微分，结果应该完全一致：

```python
house_size, real_price = 50.0, 100.0
w, b = 1.5, 10.0
err = house_size * w + b - real_price     # 预测误差 = -15
dL_dw = 2 * err * house_size   # 手推：L=(pred-real)² 对 w 求导
dL_db = 2 * err                # 手推：对 b 求导
```

PyTorch 侧用 requires_grad + MSELoss + backward 算出相同数值。**手推与自动结果一致，证明框架没算错**——这也是理解自动微分原理的最好方式：它就是把你手推的链式法则自动化了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 手推结果和框架不一致就怀疑框架 | 先检查你是否漏掉链条中间层（如激活函数也是计算图节点） |
| 手推只适用于 toy 模型 | 理解手推是为了**信任和理解**框架；千万参数必用自动微分 |

@@point ⑦ 多特征多样本：张量化的房价预测
@@need 要解决什么
只有面积一个特征太简单，实际房价还受房龄、楼层、经纬度影响，怎么办？

@@idea 核心思路
把模型扩展成**多特征线性回归**，每个特征一个权重：

```python
def predict_advanced(size, age, floor, loc_x, loc_y, w1..w5, b):
    return size*w1 + age*w2 + floor*w3 + loc_x*w4 + loc_y*w5 + b
```

更重要的是**一次算一批房子的梯度**——把 4 套房打包成张量，PyTorch 一步算完：

```python
sizes   = torch.tensor([[100.], [80.], [120.], [90.]])  # 4 套房
prices  = torch.tensor([[200.], [150.], [250.], [180.]])# 真实价
w = torch.tensor([1.5], requires_grad=True)
b = torch.tensor([10.0], requires_grad=True)
pred = sizes * w + b                # 广播：4 套房一次算
loss = torch.nn.MSELoss()(pred, prices)
loss.backward()
print(w.grad, b.grad)               # 张量化求梯度
```

**张量化 = 高效**：GPU 并行处理一个 batch，而不是逐个样本循环。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 特征数多时忘记给每个特征配权重 | w 个数必须等于特征数（此处 5 个特征 5 个 w） |
| 张量形状不匹配 | 特征矩阵 (N, D) 与权重向量 (D,) 经广播相乘，先打印 shape 验证 |
| 没意识到 4 套房本来就是 batch 的雏形 | batch 训练 = 一次前向算一批样本；这正是 DataLoader 存在的原因（下章细讲） |

@@point ⑧ 自动微分的应用边界
@@need 要解决什么
自动微分什么都能算吗？有什么注意点？

@@idea 核心思路
能算的范围很广（任意可微复合函数），但有几点注意：
1. **只对数可微的运算有意义**：含不可微点（如绝对值在 0 处）的损失，梯度按子梯度处理。
2. **整数张量不能作为带梯度节点**：要求浮点，且 requires_grad 需在浮点张量上。
3. **推理阶段要关梯度**：`with torch.no_grad():` 避免多余计算图，省显存。
4. **反向传播一次，图结构默认释放**（动态图特性）。

理解边界能避免大量"为什么报错/为什么这么慢"的困惑。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 整数张量设 requires_grad 报错 | 先 .float() 再设；只有浮点支持梯度 |
| 预测阶段内存爆掉 | 忘了 no_grad 上下文；推理不需要梯度，包上 `with torch.no_grad():` |
| 调试时想偷看中间梯度 | 用 .grad 或 register_hook 观察，但别在生产代码里滥用 |

@@summary
本章揭开了自动微分的面纱：

| 问题 | 答案 |
|---|---|
| 训练在算什么 | 反复"前向算损失→反向算梯度→更新参数" |
| 自动微分是什么 | 基于动态计算图 + 链式法则自动算梯度 |
| how 标记参数 | requires_grad=True（参数设、数据不设） |
| how 算梯度 | loss.backward()，梯度进参数 .grad |
| 梯度累积 | PyTorch 默认累加，训练每轮要 optimizer.zero_grad() |
| 怎么信任框架 | 手推 vs 自动对照，结果一致 |
| 多特征多样本 | 全张量化：一个 batch 一次前向、一次 backward |
| 应用边界 | 只算可微函数；整数不能带梯度；推理用 no_grad |

一句话记住本章：**自动微分 = 动态计算图 + 链式法则的自动化；给参数打上 requires_grad，调一次 loss.backward()，所有参数的梯度就到手，别忘了每轮 optimizer.zero_grad() 防梯度爆炸。**

@@quiz
1. 训练循环中"算梯度"这一步为什么必须自动化？真实模型有几百万参数意味着什么？
2. requires_grad=True 应该打在哪些张量上？数据张量需要吗？为什么？
3. loss.backward() 执行后，参数的梯度存储在哪里？
4. 为什么标准训练循环里需要 optimizer.zero_grad()？忘记它会导致什么？
5. 对于 y = x*w + b、L = (y - y_true)²，手动推导 dL/dw 和 dL/db 的表达式。
6. 多特征、多样本时，一次计算梯度的张量化写法有什么好处？
7. 推理阶段为什么要用 with torch.no_grad()？不用的代价是什么？

@@links
讲义|PyTorch入门讲义（自动微分与房价预测）|#
文档|PyTorch Autograd 官方教程|https://pytorch.org/tutorials/beginner/blitz/autograd_tutorial.html
文档|PyTorch autograd 机制说明|https://pytorch.org/docs/stable/notes/autograd.html