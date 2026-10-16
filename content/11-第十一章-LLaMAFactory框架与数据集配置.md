@@h1 第十一章　LLaMA-Factory 框架：训练方法与数据集注册
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　2 课时　|　难度 ★★★

@@why 这一章在解决什么问题
到目前你练过"手写 LoRA"和"Unsloth 提速"两套方案，但每次还要搭环境、写代码。**LLaMA-Factory** 是"微调界的全家桶"：一个框架覆盖全参数/高效/量化三大类十几种子方法，WebUI / 命令行 / API 三套入口，把微调从"写代码"变成"配配置+点按钮"。

这一章回答：
1. LLaMA-Factory 是什么、支持哪些训练方法、你的项目该选哪个；
2. 环境怎么装（软硬件清单 + 一键安装）；
3. 最重要的是：**数据集注册**——自己收集的指令数据怎么变成这个框架认得的格式（dataset_info.json 登场）。

目标不是"换库"，而是理解"框架帮你封装了什么、你仍需负责什么"。

@@map 这一章在整个知识库里的位置
前五章：手写 + Unsloth 两套微调路线（原理与工具加速）
**本章** ← 你在这里：LLaMA-Factory 认识 → 环境安装 → 数据集格式与注册（dataset_info.json）
下一章：WebUI 微调 + SwanLab 监控——点按钮训练，全过程可视化（阶段 12 收官）
再往后：整个阶段结束，你能在三种技术路线间按需选择
阶段终点：手写懂原理 → Unsloth 提速 → LLaMA-Factory 提效

@@point ① LLaMA-Factory 是什么：一个框架管全部
@@need 要解决什么
微调方法太多了：全参数、LoRA、QLoRA、Freeze、DoRA……再叠加不同轮术，排列组合十几套。LLaMA-Factory 的核心价值就是：**一套框架、统一入口，切换方法只改一个参数**。这一节建立全局认知。

@@idea 核心思路
LLaMA-Factory 定位（讲义表述整理）：

| 维度 | 说明 |
|---|---|
| 训练方法 | 全参数微调 / LoRA / QLoRA / DoRA / Freeze / GaLore / BAdam / Adam-mini 等 |
| 研究+场景 | 指令微调、偏好对齐（DPO/ORPO/PPO）、多模态、评估 |
| 入口 | WebUI（浏览器界面）、命令行 CLI、Python API |
| 支持模型 | Llama、Qwen、DeepSeek、Mistral、Gemma 等主流开源阵容 |

为什么它"一个顶三"：
- 你的手写 LoRA 相当于只实现"LoRA"一种方法；
- 换方法/换模型时，你手写要改代码，LLaMA-Factory 只改 YAML 配置或界面下拉框。

但注意边界——**它封装了 LoRA 的训练执行，不等于你不需要懂原理**（第 4~7 章此时继续回本）：换数据、排查 loss、判断效果，靠的还是你已经掌握的底层知识。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| "用框架就不用学原理了" | 框架把复杂藏起来，一出问题反而更难排查。**原理是排错的地图**——本阶段顺序（先手写后框架）就是为此设计 |
| 十几种子方法吓退 | 主线只重点用 **LoRA/QLoRA**（效率和原理你已通）；其他方法了解即可。**先精两个，再广了解** |
| 把 LLaMA-Factory 当"只支持中文模型" | 主流开源模型都支持，只是中文生态好。**按任务语言选模型**，不是按框架限制 |

@@point ② 训练方法速查：全参数 vs LoRA/QLoRA vs Freeze
@@need 要解决什么
框架里第一个要填的选择就是"训练方法"。四个候选（全参数、LoRA、QLoRA、Freeze）分别花多少显存、训多快、效果多好？这一节用一张表说清，帮你按电脑配置选。

@@idea 核心思路
| 方法 | 可训练参数 | 显存 | 速度 | 效果 | 适用 |
|---|---|---|---|---|---|
| 全参数 | 全部 | 最高 | 慢 | 最好 | 显存充裕、要做深度对齐 |
| Freeze | 后若干层 | 中 | 中 | 中 | 想过渡试试 |
| LoRA | 补丁（~1%） | 低 | 快 | 接近全参 | **默认首选** |
| QLoRA | 补丁 + 4bit | 最低 | 快 | 稍降 | **低显存首选** |

选择决策树：
1. 显存 < 12GB → **QLoRA**；
2. 显存 12~24GB、任务简单 → **LoRA**；
3. 显存 24GB+、任务复杂（深度指令/对齐） → 全参数；
4. 只想快速试水 → Freeze 或直接 LoRA。

呼应前文：**QLoRA / LoRA 就是你已掌握的 LoRA+量化组合**，只是现在一个下拉框搞定。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 显存 8GB 硬选全参数 | 必 OOM。**按决策树先算显存**，8GB 走 QLoRA |
| 以为全参数一定"最值" | 效果最好但成本最高；LoRA 在许多任务上 90%+ 效果、10% 成本。**按任务复杂度选**，别无脑全参 |
| Freeze 和 LoRA 选不明白 | 其实就是"冻层训层"vs"加补丁"。**默认 LoRA/QLoRA**，Freeze 只在想对照实验时用 |

@@point ③ 环境安装：软硬件要求 + 一键装
@@need 要解决什么
框架有了，装之前先看它的软硬件要求——版本不匹配（python3.9 环境、torch2.0、transformers4.49、peft0.14、trl0.8.6）全是踩雷区。这一节给清单+安装命令+验证。

@@idea 核心思路
软硬件依赖（讲义明确细项）：

| 组件 | 建议版本 |
|---|---|
| Python | 3.9+（讲义示例环境） |
| PyTorch | 2.0+（CUDA 版） |
| transformers | 4.49.0（LLaMA-Factory 对此版本有绑定） |
| peft | 0.14.0 |
| trl | 0.8.6 |
| 显卡 | NVIDIA，显存按上节决策树 |

安装（Python 环境内一键）：

```bash
pip install -U pip
pip install llama-factory         # 核心包
# 或源码开发版：git clone https://github.com/hiyouga/LLaMA-Factory.git
```

验证：

```python
import llama_factory
print(llama_factory.__version__)
```

版本纪律（再次强调）：**transformers/peft/trl 版本和 LLaMA-Factory 强绑定**——它只测过特定组合。乱升版本 = 把已验证的链路炸掉。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| python 3.13 装 llama-factory 依赖报错 | 部分依赖（如 flash-attn）对新 Python 支持滞后。**用 3.9~3.11** 建独立环境 |
| transformers 升到 4.50+ 后 WebUI 报错 | 版本被框架绑定。**按官方 requirements 锁版本**（transformers 4.49 / peft 0.14 / trl 0.8.6） |
| 在已有的 lora_env（torch 版本不同）里装 | 依赖冲突难缠。**独立环境 factory_env**，同前两套分开各自验证 |

@@point ④ 数据集格式：Alpaca 与 ShareGPT 两种模板
@@need 要解决什么
框架统一用 JSON 文件管理数据，但字段名有讲究：**Alpaca**（单轮 instruction/input/output）与 **ShareGPT**（多轮 conversations 数组）。这块写错，数据加载直接失败——这一节把两种格式切开看。

@@idea 核心思路
Alpaca 格式（单轮，第 9 章已见，重复以示对比）：

```json
[
  {
    "instruction": "解释什么是神经网络",
    "input": "",
    "output": "神经网络是由多层神经元组成的计算模型……"
  }
]
```

ShareGPT 格式（多轮对话）：

```json
[
  {
    "conversations": [
      {"from": "human", "value": "介绍下你自己"},
      {"from": "gpt", "value": "我是基于……的 AI 助手"},
      {"from": "human", "value": "你会什么？"},
      {"from": "gpt", "value": "我会……"}
    ]
  }
]
```

| 维度 | Alpaca | ShareGPT |
|---|---|---|
| 形态 | 单轮指令-回答 | 多轮对话 |
| 字段 | instruction/input/output | conversations[from/value] |
| 适用 | 指令数据集 | 对话/助手数据 |

**选定一种，全文件保持一致**；混用会导致框架解析错乱。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 单轮数据硬套 ShareGPT | 缺 from/value 结构报错。**单轮用 Alpaca，多轮用 ShareGPT**，别混 |
| conversations 里 from 值填错了（如写 "user" 而非 "human"） | 字段值有约定。**human/gpt 是示例约定，按框架文档写对**；写错角色对调，训练出来的模型会"反着说话" |
| JSON 少个逗号/括号 | 框架解析失败是最常见错误。**先 `python -m json.tool 文件.json` 校验**再喂给框架 |

@@point ⑤ dataset_info.json：数据集的"注册表"
@@need 要解决什么
数据文件备好了，框架还"不认"。要让 LLaMA-Factory 认识它，得在 **dataset_info.json** 里登记：文件路径 + 字段映射（columns）+ 标签（tags）。这是框架数据侧的"户籍系统"。

@@idea 核心思路
先看框架默认的 `data/dataset_info.json`，注册一条自己的数据集（义形式）：

```json
{
  "my_training_data": {
    "file_name": "my_data.json",
    "columns": {
      "prompt": "instruction",
      "query": "input",
      "response": "output"
    },
    "tags": {
      "role_tag": "from",
      "content_tag": "value"
    }
  }
}
```

逐字段翻译：
- `file_name`：数据文件（和 dataset_info.json 同目录）；
- `columns`：把框架标准字段（prompt/query/response）映射到**你的文件字段**（instruction/input/output）；
- `tags`：ShareGPT 多轮格式里角色/内容字段名（from/value）。

登记后，WebUI 数据集下拉框里就会出现 `my_training_data`——选中即用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘登记，WebUI 里找不到自己的数据 | 只放文件不登记 = 没户口。**改 dataset_info.json 加一条**（或用 WebUI 上传按钮自动登记） |
| columns 字段名和你文件对不上 | 框架按映射取字段。**逐字段核对**：prompt↔instruction / response↔output |
| 文件路径不对（放错目录） | file_name 是相对 data/ 的路径。**确认文件在 data/ 下**，否则报 file not found |

@@point ⑥ 注册中文医疗数据：一个完整案例
@@need 要解决什么
讲义用**中文医疗数据集**做了完整注册示范——这是本阶段"数据集注册"的标准例题。照它走一遍，你就掌握了"任意垂直领域数据进框架"的通用流程。

@@idea 核心思路
流程四步（讲义案例提炼）：
1. **备数据**：`chinese_medical.json`（Alpaca 结构，instruction/input/output）；
2. **放位置**：拷进 `data/` 目录；
3. **注册**：dataset_info.json 加条目：

```json
{
  "chinese_medical": {
    "file_name": "chinese_medical.json",
    "columns": {
      "prompt": "instruction",
      "query": "input",
      "response": "output"
    }
  }
}
```

4. **验证**：WebUI 里训练页的数据集下拉框能找到 `chinese_medical`，能预览前几条。

验证时不点训练，先看"预览样本"对不对——包括 system 提示是否自动拼接（LLaMA-Factory 会按模板拼），这一步能提前暴露字段错位。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 医疗数据里 input 字段全空 | 空 input 合法（query 可无）；但要和模板一致。**预览确认拼接后的文本完整**，别只盯原始 JSON |
| 预览内容乱/错位 | 字段映射错了。**回 dataset_info.json 核对 columns**；再不行用 python 打印一条样本看字段 |
| 数据集太大，WebUI 预览卡 | 只取 query 示例即可，预览本身只载前几条。**响应慢不代表错**，耐心等 |

@@point ⑦ 数据质量管理：喂给框架前先过筛
@@need 要解决什么
框架不校验数据质量，烂数据照样开训——然后你收获一个"拉胯模型"。上线前必须过质量关：去空、去重、查短长、查标签对错。这一节的检查项与第 5 章呼应，但按框架的数据形态再走一遍。

@@idea 核心思路
四道筛子（可写成脚本跑）：

| # | 检查 | 说明 |
|---|---|---|
| 1 | 空 content | output/response 为空的剔除 |
| 2 | 重复样本 | 去重（同 instruction+output） |
| 3 | 超长/超短 | 长度异常的剔（token 量化后再看，或先按字符粗筛） |
| 4 | 角色标签对 | ShareGPT 里 from 值规范（human/gpt 交替合法） |

示例（Python 粗筛思路）：

```python
import json
with open("data/chinese_medical.json", encoding="utf-8") as f:
    data = json.load(f)

clean = [d for d in data
         if d.get("output") and len(d.get("output", "")) > 10]
print("原始:", len(data), "清洗后:", len(clean))
```

再对接第 12 章的患病监控思路：清洗比例、条目数记录进文档，训练前心里有数。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 跳过清洗直接训 | 空样本让 loss 抖动、重复样本让模型学说车轱辘话。**清洗是 10 分钟，返工是 2 小时** |
| 清洗脚本和训练数据分开，忘了同步 | 清洗结果另存 `_clean.json` 并在 dataset_info.json 指向清洗版。**文件名里带 clean 标记**，避免误用旧版 |
| 清洗过头（把所有长答案都删了） | 长度阈值别拍脑袋。**看一眼数据长度分布**（print 前 50 条长度），设合理阈值 |

@@point ⑧ 本章验收：数据侧就绪
@@need 要解决什么
爬过环境、格式、注册、清洗四关后，验收三件事：环境版本对、注册能预览、数据干净。全过，第 12 章点开 WebUI 就能开训。

@@idea 核心思路
验收清单：

| # | 检查项 | 方法 | 标准 |
|---|---|---|---|
| 1 | 环境版本合规 | 对照第 ③ 节清单 pip show | transformers/peft/trl 与框架绑定版本一致 |
| 2 | llama_factory 可导入 | import 验证 | 无错有版本号 |
| 3 | 数据集已注册 | WebUI 数据集下拉框 | 出现你的数据集且能预览前几条 |
| 4 | 数据已清洗 | 清洗脚本跑过 + 条目数对比 | 空/重复/超常长度已剔除 |
| 5 | 格式统一 | json.tool 校验 + 抽查字段 | 合法 JSON、字段映射正确 |

顺手把数据集的来源、清洗规则、条目数写进 README——第 12 章训练时的"数据集选择"就有据可查。

全过 = 数据侧工程完成。下一章进入 WebUI 操作：选模型、选数据、配超参、点开始，并接入 SwanLab 做训练可视化监控。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 验收只看"能 import"不看版本 | import 成功 ≠ 版本匹配。**版本号逐项核对**，这是框架兼容性的第一道线 |
| 注册成功但预览不出数据 | file_name 路径/each 编码问题。**确认文件 UTF-8、路径对**，再用 json.tool 自查 |
| 觉得"数据差不多就行" | 数据决定模型下限。**最后一道质量闸再严也不为过**，阶段 12 训练效果直接受它制约 |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **框架全景认知** | LLaMA-Factory 一个入口管 10+ 训练方法，LoRA/QLoRA 是主线 |
| **环境安装技能** | 软硬件清单 + 版本绑定纪律，避开升级雷区 |
| **数据集注册能力** | Alpaca/ShareGPT 两种格式、dataset_info.json 映射、中文数据完整案例 |
| **数据质量闸门** | 清洗四筛 + 验收五查，训练前数据心里有数 |

下一章收官之章：WebUI 里选模型/数据/参数、点开始训练，SwanLab 全程可视化监控与评估——阶段 12 全流程画上句号。

@@quiz
1. LLaMA-Factory 的三类入口分别是什么？切换训练方法要改什么？
2. 显存 8GB 的电脑，按决策树该选哪种训练方法？为什么？
3. 环境安装的关键版本绑定是哪些？（至少两个库与版本号）
4. Alpaca 与 ShareGPT 格式的区别是什么？各字段名是什么？
5. dataset_info.json 里 columns 的作用是什么？tags 呢？
6. 数据清洗四道筛子分别查什么？
7. 注册新的中文数据集，完整四步流程是什么？

@@links
讲义|人工智能（副本）：LLaMA-Factory 框架、训练方法与数据集格式|#
官网|LLaMA-Factory 官方仓库（文档/数据集说明）|https://github.com/hiyouga/LLaMA-Factory
官网|LLaMA-Factory 数据集格式文档|https://github.com/hiyouga/LLaMA-Factory/blob/main/data/README.md