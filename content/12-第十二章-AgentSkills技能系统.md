@@h1 第十二章　Agent Skills 技能系统：让 Agent 拥有"职业能力"
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实战　|　难度 ★★★★

@@why 这一章在解决什么问题
前十一章把 Agent 的"骨架"（图/工具/记忆/协议）都搭好了。但每次要让 Agent 干一件新领域的专业活（做海报、做 PPT、处理文档），都要临时写一套流程+提示词+脚本——重复劳动，且换台电脑/换个人就丢失。

**Agent Skills（技能系统）** 解决这个问题：把"开发流程 + 参考文档 + 开发工具 + 静态资源"打包成一个标准文件夹（SKILL.md + references/ + scripts/ + assets/），即插即用——就像给 Agent 装配"职业技能包"。Claude Code 生态里这类技能已成标准（本套件的前端设计、PPT、文档、表格技能都是）。

@@map 这一章在整个知识库里的位置
上一章：A2A 协议——Agent 之间互联互通
**本章** ← 你在这里：Agent Skills 技能系统——可复用的技能包（阶段 8 收尾章）
覆盖：理解 Skill / 定制 Skill / 推荐 Skill 三件事

@@point ① Skill 到底是什么：一套结构化的能力模块
@@need 要解决什么
先说清概念：Skill 和"提示词"到底差在哪？为什么 Skill 是"小组干活"而不是"一句话指令"？

@@idea 核心思路
- **提示词**：单一的文本输入，用于引导模型——你给它一句话，它凭模型本事发挥
- **Skill**：一套**结构化的能力模块**——可能包含多个提示词、调用脚本、参考文档、静态资源，是"可执行的完整工作流"

类比：提示词 = 下达口头指令"帮我做个 PPT"；Skill = 你要求一个**工作小组**"帮我做关于黑洞的 10 页 PPT"——这个小组会：① 查资料（references）② 按流程推进（SKILL.md 工作流）③ 用工具干活（scripts）④ 参考样式（assets）。

```
~/Skill  # 技能
├── SKILL.md        # 主要说明（必填）
├── references/     # 附加文档
├── scripts/        # 可从 skill 调用的帮助程序脚本
└── assets/         # 静态资源（参考图等）
```

**只有 SKILL.md 是不可或缺的**，其余目录按需创建。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为 Skill 只是提示词文本 | Skill 是结构化模块：frontmatter+正文+可选脚本/资源 |
| 把整段大 prompt 塞进 SKILL.md 就算完事 | 可执行能力要落在 scripts/ 里，正文只写流程与规则 |

@@point ② Skill 目录结构的四件套
@@need 要解决什么
每个技能都有对应的规范——开发流程、参考文档、开发工具、静态资源。在 Agent Skill 术语里怎么一一对应、怎么组织？

@@idea 核心思路
对应关系一目了然：

| 你熟悉的开发要素 | Skill 术语 | 用途 |
|---|---|---|
| 开发流程 | SKILL.md | 主说明：角色、任务、步骤、输出格式 |
| 参考文档 | references/ | 附加文档，**避免臃肿的 SKILL.md** |
| 开发工具 | scripts/ | 可调用的帮助程序脚本（Python 等） |
| 静态资源 | assets/ | 参考图、模板等素材 |

标准目录结构（放在 `~/.claude/skills/<技能名>/`）：

```
~/.claude
└── skills/
    └── iwen-creative/
        ├── SKILL.md           # 主说明（必填）
        ├── references/        # 附加文档
        ├── scripts/           # 帮助程序脚本
        └── assets/            # 参考图等
```

要点：SKILL.md 只写"流程骨架"，细节文档放 references——**避免把 SKILL.md 写成一坨臃肿文件**；复杂业务逻辑写进 scripts（Python 脚本），Agent 按需调用。

@@point ③ SKILL.md 的结构：frontmatter + 正文
@@need 要解决什么
SKILL.md 长什么样？第一眼能看到什么？怎么让 Agent 和用户都快速理解这个技能是干嘛的？

@@idea 核心思路
SKILL.md = **frontmatter（元信息） + 正文（工作流）**：

```markdown
---
name: iwen-creative
description: 为iwen餐厅生成符合品牌调性的物料设计创意，当用户说要做
            某种物料(海报、易拉宝、工服、包装盒等)，你需要输出这个
            物料的设计创意。
---
# iwen-creative
为iwen餐厅生成符合品牌视觉规范的各类营销物料，输出创意方案

## 品牌核心元素
- 品牌名：iwen
- 网感 IP 形象：布偶猫
- 主色：薄荷绿 #5DDEB5
- Slogan：A FRESH, MODERN BITE / 健康轻食主义
- 风格：3D 卡通、清新时尚、年轻活力

## 你的任务
当用户说要做某种物料(海报、易拉宝、工服、包装盒等)，
你需要输出这个物料的设计创意描述。

## 输出格式
请按以下格式输出：
### 创意主题  （一句话概括核心概念）
### 视觉风格  （整体氛围、配色方向、质感）
### 画面构成  （主体元素、背景、装饰元素的布局描述）
### 细节建议
```

要点：
- **frontmatter 的 name + description 是"门面"**：Agent 靠它判断"何时该用这个技能"，写清楚触发场景
- 正文 = 该领域的"专家手册"：品牌信息、配色、任务定义、输出格式——让 Agent 一读就知道怎么做
- 用户说"帮我做 iwen 的慧灵顿牛排促销海报"→ Agent 命中 iwen-creative → 按品牌、风格、定位、目标客群维度输出设计

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| frontmatter 字段拼错/缺失导致技能加载失败 | name/description 必填，格式要严格遵守 YAML |
| 正文冗长无分节，Agent 难以遵循 | 结构化的分节指令更易执行，长文反而效率低 |

@@point ④ references / scripts / assets 各司其职
@@need 要解决什么
知道四件套，但具体怎么用？references 放什么、scripts 怎么被调用、assets 提供什么？

@@idea 核心思路
三个辅助目录的实战用法：

**references/ 附加文档**：品牌手册、设计规范、历史案例等长文档。Agent 在 SKILL.md 中按需引用加载——**避免把 SKILL.md 写臃肿**。

**scripts/ 帮助程序脚本**：可被 skill 调用的自动化程序。iwen 案例中即 `generate_image.py`：

```python
"""调用 DashScope Qwen-Image-2.0-Pro API 生成图片，支持参考图输入。"""
# 支持命令行参数：-t prompt文本、-r 参考图、-o 输出路径
# 输出路径：目录(-o images 自动生成文件名) 或 完整文件路径
```

规范：脚本要有清晰 usage（参数说明），输出路径支持目录/文件两种写法，**自动创建不存在的目录**。

**assets/ 静态资源**：提供参考图——品牌示例海报、风格参考图，Agent 生成时"看着参考图出图"。

要点：**脚本负责"真实计算"（调 API 出图），SKILL.md 负责"工作流描述"**——两者配合才是完整技能。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| SKILL.md 越来越长没人看 | 长文档塞进 SKILL.md，应放 references 按需加载 |
| 脚本无法被技能调用 | scripts 脚本没写清楚命令行用法/参数说明 |
| Agent 不触发技能 | frontmatter 的 description 没写清触发场景 |
| 技能目录结构错误 | 不是全部目录必需，但 SKILL.md 缺失则技能无效 |

@@point ⑤ 实战：从零编写一个简单 Skill
@@need 要解决什么
光看不练假把式。怎么把一个"给 iwen 餐厅做物料设计"的需求，落地成一个可用的技能包？

@@idea 核心思路
五步流程：

1. **建目录**：`~/.claude/skills/iwen-creative/` 下建 SKILL.md（必需）+ references/ scripts/ assets/（按需）
2. **写 frontmatter**：name=技能标识、description=触发场景说明（这是 Agent 判断的依据）
3. **写正文**：品牌核心元素（IP/主色/Slogan/风格）+ 你的任务 + 输出格式（四个小节固定结构）
4. **加脚本**：scripts/generate_image.py——调用图像 API 生成物料图，参数化设计（prompt/参考图/输出路径）
5. **调试运行**：打开终端输入 `claude` → 用"帮我做一张 iwen 的慧灵顿牛排促销海报"触发 → 看输出是否符合品牌风格 → 不满足就调 SKILL.md 描述与脚本

配齐工具链：VSCode 写代码 + Claude Code 跑 Agent + CC Switch 切换模型供应商（登录提示出现说明配置未生效，回到 Switch 重新切换）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 写完 Skill 不测试就直接用 | 先在隔离环境跑脚本验证，脚本异常/密钥泄漏都要提前暴露 |
| 脚本里硬编码 API Key | 密钥走环境变量/配置，Skill 文件里只放占位符 |

@@point ⑥ 好用的现成 Skills 推荐
@@need 要解决什么
"造轮子"前先看看生态——很多高频技能别人已经做好了，直接装。

@@idea 核心思路
课程推荐的必用技能：

| 技能 | 用途 |
|---|---|
| frontend-design | 做前端页面 |
| pptx | 做 PPT |
| docx | 处理文档 |
| xlsx | 处理表格 |

聚合平台：
- **SkillsMP**：聚合 GitHub 上 **11 万+ 开源技能**
- **Skills Directory**：Reddit 社区推荐的技能合集

选技能的方法：搜"子类关键词 + skills"（如"PPT skills github"）→ 看 stars/下载量/更新时间 → 装进 `~/.claude/skills/` → 测试触发。先找现成的，不够再自己写。

@@point ⑦ Skill 生态：为什么 Skill 是 Agent 应用的关键拼图
@@need 要解决什么
从"技能"回看整个 Agent 工程：Skills 在 Agent 技术栈里处于什么位置，为什么说它是"最后一公里"？

@@idea 核心思路
Agent 能力分层：

```
应用层    → 具体业务技能（Skills）：海报/PPT/文档/表格…职业能力包
编排层    → LangGraph：图编排、记忆、HITL、多 Agent
连接层    → MCP / A2A：接工具、接 Agent
模型层    → LLM：思考与生成
```

Skill 的意义：
- **沉淀与复用**：一次调好的"品牌+流程+脚本"打包，团队共享、跨项目复用
- **解耦模型**：换模型不用重写技能；能力在技能包里，不在模型权重里
- **生态价值**：SkillsMP 11 万+技能 = Agent 的"应用商店"——越来越多的专业工作流将标准化、可安装

一句话：**Agent 的"上限"由模型决定，Agent 的"下限"由技能决定**——技能越完善，Agent 越像"这个领域的老手"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为 Skills 只能自己从零写 | 生态已有大量现成技能（SkillsMP 11万+），先搜再用 |
| 把装的所有 Skill 全喂给 Agent | Skill 按需加载，堆太多挤占上下文 token |

@@point ⑧ 综合实战：你的第一个生产级技能包清单
@@need 要解决什么
收尾检查：一个"生产可用"的技能包，要满足哪些硬指标？怎么验收？

@@idea 核心思路
**技能包验收清单**：
1. frontmatter 规范：name 唯一、description 说清触发场景与边界
2. SKILL.md 正文：角色 + 步骤 + 输出格式 + 品牌/领域约束，可被独立执行
3. references 按需加载：长文档不进主文件
4. scripts 脚本化：参数化、有 usage 文档、错误可读
5. assets 素材完整：参考图/模板齐备
6. 端到端测试：用真实任务触发一次，输出符合预期再发布
7. 安全合规：**涉及真实 API Key 一律用环境变量占位**（如 `os.getenv("DASHSCOPE_API_KEY")`），严禁硬编码

记住：**技能不是"写出来"的，是"测出来"的**——每次真实任务都是技能质量的检验。

@@summary 这一章你学到了什么
- 区分 Skill 与提示词：Skill 是结构化能力模块（多提示词+脚本+文档+素材），提示词是单一文本
- 掌握四件套结构：SKILL.md 流程 / references 文档 / scripts 工具 / assets 素材，只有 SKILL.md 必填
- 会写 SKILL.md：frontmatter（name/description）+ 正文（品牌元素/任务/输出格式）
- 理解 references 的作用：避免 SKILL.md 臃肿，长文档按需加载
- 会用 scripts 封装真实计算（如图像生成脚本），参数化设计 + 输出目录自动创建
- 会从零编写技能：建目录→写元信息→写正文→加脚本→端到端测试
- 认识生态：SkillsMP（11 万+技能）、Skills Directory，先找现成再自造
- 生产验收清单：字段规范、端到端测试、API Key 一律占位符
- 理解了 Skills 在技术栈中的位置：应用层能力包，决定 Agent 的"领域下限"

到这里，阶段 8「AI Agent 智能体与多模态应用」十二个章节全部学完——从 Agent 理论基础、工具系统、LangChain/LCEL、LangGraph 编排、记忆、MCP、人机协作、实战与可观测、A2A 跨 Agent，到 Skills 技能系统。你现在掌握的是一条完整的 Agent 工程链路：**能用工具、能记上下文、能编排流程、能连外部系统、能人工把关、能互联互通、能沉淀技能**。

@@quiz
1. Skill 与提示词的本质区别是？
   A. 没区别　　B. Skill 是结构化能力模块（流程+脚本+文档+素材），提示词是单一文本　　C. 提示词更长　　D. Skill 只能用于前端
2. Skill 目录中唯一必需的文件是？
   A. scripts/　　B. assets/　　C. SKILL.md　　D. references/
3. SKILL.md 中 frontmatter 的作用是？
   A. 设置主题色　　B. name + description 元信息，Agent 据此判断何时触发技能　　C. 存放图片　　D. 记录版本
4. references/ 目录的主要用途是？
   A. 放脚本　　B. 放参考图　　C. 放附加长文档，避免 SKILL.md 臃肿　　D. 放日志
5. scripts/ 目录里的脚本应该？
   A. 硬编码 API Key　　B. 参数化设计、有 usage 说明、输出目录自动创建　　C. 每次手写　　D. 只能输出到桌面
6. 以下哪个是聚合开源 Skill 的平台？
   A. SkillsMP　　B. npm　　C. PyPI　　D. Docker Hub
7. 技能包验收时，真实 API Key 应该怎么处理？
   A. 直接写进脚本　　B. 用环境变量占位符（os.getenv）　　C. 写进 SKILL.md　　D. 无所谓

@@links
讲义|skills.pdf|#
官方|Claude Code Skills 文档|https://docs.anthropic.com/en/docs/claude-code/skills
聚合|SkillsMP（11万+技能）|https://skillsmp.com/
社区|Skills Directory|https://www.reddit.com/r/ClaudeAI/comments/1ll7yzq/