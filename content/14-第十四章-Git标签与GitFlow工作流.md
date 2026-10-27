@@h1 第十四章　Git 标签与 Git Flow 工作流
@@sub 阶段 18 · 云原生开发环境与 DevOps 工具链　|　版本控制　|　难度 ★★★

@@why 这一章在解决什么问题
项目干到 v1.0 发布、v2.0 发布——以后别人问"1.0 到底是哪个版本"，你总不能去翻提交历史数吧？**标签（tag）就是给重要节点贴永久记号**。

而团队人多以后，光有分支还不够，还得有**规矩**：谁的分支基于谁、合并到哪、什么时候打标签——这就是 Git Flow。这一章学完，你的 Git 技能包正式"毕业"：能打版本、能按规范协作，还能在 IDEA 里顺手完成日常操作。

@@map 这一章在整个知识库里的位置
**上一章**：分支管理——贴纸模型、合并、误删找回
**本章** ← 你在这里：收官两件套——标签（给版本打记号）+ Git Flow（团队分支规范）+ IDEA 集成
**下一章**：走出版本控制这一站，进入阶段 18 后续章节——持续集成与更多 DevOps 工具链

@@point ① 标签是什么：给重要的提交贴"永久名牌"
@@need 要解决什么
发布 v1.0 后代码继续开发，几百个提交过去了——客户说"线上 1.0 那个版本的代码我想看看"。你不可能记住"那天那个提交号"。**标签 = 给某个提交起一个有意义的名字（如 v1.0.0），以后一句话就能切过去。**

@@idea 核心思路
- 标签（tag）用来标记历史里**某个特定提交**，通常用于**发布节点**：`v1.0.0`、`v2.0.0`、`beta-release`；
- 本质和分支一样是"贴纸"，但**它不随提交移动**——贴上去就永远留在那个位置；
- 常用场景：软件里程碑（版本发布）、重要试验节点、需要长期引用的基线。

```bash
git tag                  # 列出所有标签
git tag v1.0.0           # 给当前提交打标签 v1.0.0
git show v1.0.0          # 查看这个标签指向的提交详情
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 没打标签，三个月后找不到发布版本 | **发布即打 tag**是团队规范（Git Flow 里是硬性步骤）；别等事后找 |
| 以为 tag 会跟着代码走 | 标签**永远钉住**当初那个提交；代码再前进一万步，tag 还指向那个位置——这正是它的用途 |

@@point ② 标签和分支的区别：贴纸动不动
@@need 要解决什么
"分支也是贴纸，标签也是贴纸，到底差在哪？"——差在一个字：**动**。分支会随 commit 前进，标签不会。这一条想清楚，两个概念都不再含糊。

@@idea 核心思路
| | 分支（branch） | 标签（tag） |
|---|---|---|
| 本质 | 贴在 commit 上的指针 | 贴在 commit 上的指针 |
| 是否移动 | **会**：新 commit 后自动前进 | **不会**：永远留在原地 |
| 用途 | 持续开发的工作线 | 标记固定节点（版本发布） |
| 删除影响 | 不影响 commit 对象 | 不影响 commit 对象 |

一句话：**分支是"会移动的标签"，标签是"钉死的分支"。** 两者被删除时，都不会影响被指到的那个提交对象。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用分支名代替版本号来"发布" | 分支会动，三个月后分支早已不是当时的代码；**版本引用必须用 tag** |
| 以为删 tag 会删掉代码 | 不会，commit 还在；删 tag 只是撕掉命名贴纸 |

@@point ③ 创建标签的两种方式：轻量 vs 附注
@@need 要解决什么
`git tag v1.0` 和 `git tag -a v1.0 -m "..."` 都是打标签，差别在哪？一个"裸标签"，一个"带完整说明的标签"——大项目里后者是标准做法。

@@idea 核心思路

```bash
git tag v1.0.0                     # 轻量标签：只是个名字，直接钉在当前提交
git tag -a v1.0.0 -m "首个稳定版发布"   # 附注标签：带作者、日期、说明（推荐）
git tag v1.0.0 提交号              # 给【指定的旧提交】打标签（不一定是当前提交）
git tag -d 标签名                  # 删除本地标签
```

| 类型 | 信息 | 适用 |
|---|---|---|
| 轻量标签 | 只有一个名字 | 临时标记、个人使用 |
| 附注标签 | 名字 + 作者/日期/说明 | **发布版本**，团队可追溯 ✅ |

用 `git show 标签名` 查看时：附注标签能看到完整说明，轻量标签只能看到提交信息——这就是差距。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 给错误的提交打了标签 | 删掉重打：`git tag -d 标签名`，再对正确的提交号打 |
| 以为 `git tag v1.0.0` 会带作者和说明 | 默认是轻量标签，**没有作者和说明**；要带说明必须 `-a -m` |
| 打标签前还没 commit | 标签钉的是"当前提交"，连最后一次改动都没提交，打出来的标签就是"旧代码"；**先 commit 再 tag** |

@@point ④ 检出标签：在旧版本上开新分支
@@need 要解决什么
"线上 v1.0 出 bug 了，我要在那时的代码基础上修"——直接 checkout 一个标签会进入"游离 HEAD"状态，改的东西没有分支可挂。正确姿势：**基于标签开一条新分支**。

@@idea 核心思路

```bash
git checkout -b fix-v1.0 v1.0.0    # 基于 v1.0.0 标签创建一个新分支并切换
```

这条命令 = 用 v1.0.0 的代码作起点，开一条叫 `fix-v1.0` 的分支继续开发。有了新分支，后续 commit 有"家"可依，不会丢在游离状态。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接 `git checkout v1.0.0` 后改代码，切走再回来发现改动"丢了" | 你当时处于**游离 HEAD**，改动没挂任何分支；**基于标签先用 -b 建分支**再动手 |
| 标签能改吗 | 标签本身不可移动；发现打错就删掉重打 |

@@point ⑤ 标签的远程同步：推送个别的、删除靠固定写法
@@need 要解决什么
本地打好的标签，队友怎么看到？直接 `git push` 可**不会**自动带上标签——标签必须单独推送。删除也一样，得单独操作。

@@idea 核心思路

```bash
git push origin v1.0.0          # 推送单个标签到远程
git push origin --tags          # 一次性推送所有本地标签
git push origin :refs/tags/v1.0.0   # 删除远程标签（:refs/tags/ 是固定写法，别改）
```

- 推送：`git push <remote> <标签名>`，或 `--tags` 全推；
- 删除远程标签：`git push origin :refs/tags/<标签名>`——`:` 前面留空表示"什么都不推 = 删除"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| push 了代码，但去远程仓库看不到标签 | **push 默认不带标签**；需要显式 `git push origin 标签名` 或 `--tags` |
| 远程标签删不掉 | 用的就是 `:refs/tags/` 固定写法；格式拼错可能把"某个分支"推上去，注意别写错 |
| 本地删除和远程删除是两回事 | 本地 `git tag -d`，远程 `git push origin :refs/tags/名`，别只做一半 |

@@point ⑥ Git Flow 是什么：给"分支怎么用"立规矩
@@need 要解决什么
人少的时候随意 commit、随意合并问题不大；人一多，**每个人都按自己的习惯折腾分支**，master 上什么妖魔鬼怪都有，发布随时翻车。Git Flow 就是一套**分支管理的行为规范**：谁是主干、谁基于谁、合并到哪、何时打标签，都有明确规定。

@@idea 核心思路
Git Flow 的核心收益：
- 开发（develop）、发布（release）、修补（hotfix）**各走各的通道**，互不踩踏；
- master 上永远是**可以直接上线的版本**，每个 master 提交都打标签；
- 大项目的结构清晰：新人在哪个分支工作、东西合并去哪，一目了然。

它不是 Git 的功能，而是**团队约定**——用 Git 的普通命令，配合一套纪律。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Git Flow 是"必须安装的插件" | 它是**工作流规范**，用原生命令即可实现；也有辅助插件，但核心是纪律 |
| 小项目硬套完整 Git Flow | 一两个人的项目全量 Git Flow 反而累赘；**它适合多人、有版本发布节奏的项目**，小项目用"一条 master + 一条 dev"的简化版就够 |
| 以为只有一种工作流 | Git Flow 之外还有 GitHub Flow 等轻量流派；团队一致即可，没有绝对最优 |

@@point ⑦ Git Flow 五大分支：各司其职
@@need 要解决什么
Git Flow 规范到底长什么样？先记住这五张"角色卡"，后面走流程才有地图。

@@idea 核心思路
| 分支 | 职责 | 基于 | 合并到 | 生命周期 |
|---|---|---|---|---|
| **master（main）** | 线上正式版，只放可发布代码 | — | — | 常驻 |
| **develop** | 开发集成线，日常所有功能汇总处 | master 初始创建 | — | 常驻 |
| **feature/** | 开发具体功能 | develop | develop | 功能完成即删 |
| **release/** | 发布前测试、修 bug、准备版本号 | develop | master + develop | 发布即删 |
| **hotfix/** | 线上紧急 bug 修补 | master | master + develop | 修补上线即删 |

补充规则：
- **master 上的每个提交都打标签**（v1.0.0、v1.0.1…）；
- 一般**不在 master 上直接开发**，master 只收从 release / hotfix 合并进来的提交；
- develop 常驻，是日常开发的"主战场"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 在 master 上直接改代码 | 违反规范；master 只接收 release/hotfix 的合入，直接改会让"线上版"失控 |
| 忘记给 master 提交打标签 | Git Flow 的铁规矩：**master 每收一次合入就是一次发布，必须打标签** |
| feature 分支拖了一周不合并 | 分支越老越难合并；**功能完成立刻合并回 develop 并删除** |

@@point ⑧ Git Flow 的分支生命周期：谁生谁死
@@need 要解决什么
五大分支之间不是随便生随便死——谁基于谁创建、合并到谁、何时删除，有严格规矩。这里把"血缘关系"理清。

@@idea 核心思路
```
              master: m0 --- m1(合入测试通过的 release) --- m2(合入 hotfix)
                      \                          \                    \
  develop: ----------- d1 --- d2 --- d3 -------- d4 ---------------- d5
                      \            \
  feature/登录:         f1 --- f2    \           (feature 合入 develop 后删除)
                                     \
  release/0.1.0:                      r1 --- r2 (测试修 bug，合入 master+develop 后删除)
  hotfix/0.1.1:       (基于 master 开)     h1 (合入 master+develop 后删除)
```

规矩速记：
- **feature 基于 develop 生，合回 develop 后删**；
- **release 基于 develop 生**，测试完**同时合 master 和 develop**，master 上打 tag，**删 release**；
- **hotfix 基于 master 生**，修完**同时合 master 和 develop**，master 打 tag，**删 hotfix**；
- 一旦打出 release 分支，**不要再把 develop 的新改动合进 release**（防止测试内容漂移）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| release 期间把 develop 新功能合进 release | release 是"冻结集"：只修 bug 不加功能，否则测试永远测不完 |
| hotfix 只合 master 忘记合 develop | develop 会一直缺这个修复，下个版本发布的还是旧 bug；**hotfix 必须 master + develop 双合一** |
| feature 从 master 直接拉 | 功能基于 develop 才有完整的集成环境；从 master 拉会导致功能与队友的功能脱节 |

@@point ⑨ Git Flow 命令走一遍：从开发到发布到修补
@@need 要解决什么
规矩背完了，现在**用命令把完整生命周期跑一遍**：建 develop → 开 feature → 完成合入 → 发 release → 上线打 tag → 紧急 hotfix。

@@idea 核心思路

```bash
# 0. 建常驻分支
git branch develop && git push -u origin develop

# 1. 功能分支：从 develop 开、合回 develop
git checkout -b feature_login develop
git add . && git commit -m "完成登录模块"
git checkout develop && git merge feature_login
git push origin develop

# 2. 发布：从 develop 开 release，测试后合入 master
git checkout -b release-0.1.0 develop
git checkout master && git merge --no-ff release-0.1.0

# 3. 打标签并推送
git tag v0.1.0
git push && git push origin v0.1.0
```

```bash
# 4. 紧急修补：从 master 开 hotfix
git checkout -b hotfix-0.1.1 master
git add . && git commit -m "修复线上 bug"

# 5. 合回 master 和 develop，并打标签
git checkout master && git merge --no-ff hotfix-0.1.1
git checkout develop && git merge hotfix-0.1.1
git push origin master develop
git tag v0.1.1 && git push origin v0.1.1
```

每一步对应 Git Flow 的一张"角色卡"：功能合 develop、release 双合、master 必打标签、hotfix 双向补。这套流程跑顺了，团队协作就稳了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `merge --no-ff` 是什么 | 强制生成一个"合并提交"，把分支历史保留得清清楚楚；发布这类关键节点建议用 |
| 标签推送的顺序 | 标签指向的提交必须先存在于远程；**先 push 代码，再 push 对应标签** |
| 忘推 develop | develop 是团队共享的开发基线，只改不推，队友还在旧基础上开发 |

@@point ⑩ IDEA 集成 Git：IDE 里完成日常 80% 操作
@@need 要解决什么
命令行很酷，但日常更多时候是在 IDE 里写代码。**IDEA 内置完整的 Git 支持**：提交、推送、拉取、分支、冲突解决都有图形界面，效率和容错率更高。这一条带你串一遍 IDEA 里的 Git 日常。

@@idea 核心思路
**开局配置**：
1. `File → Settings → Version Control → Git`，确认 Git 可执行文件路径正确（默认装完 Git 后 IDEA 会自动找到；改过安装路径要手动指过去）；
2. 首次使用会要求填 user.name / user.email（沿用命令行配置即可）。

**日常四件套**：

| 操作 | 在哪点 | 说明 |
|---|---|---|
| 添加/提交 | 右键文件 → Git → Add / Commit | Commit 面板可勾选文件、写说明，还能看 diff |
| 推送 | 工具栏 Git → Push | 相当于 `git push` |
| 拉取 | 工具栏 Git → Pull | 相当于 `git pull`（Git → Fetch 则只拉取） |
| 克隆 | 欢迎页 Get from VCS，粘贴仓库 URL | 相当于 `git clone` |

**分支与冲突**：IDEA 右下角有分支名称下拉框，可新建/切换/合并分支；冲突时弹出 Merge Revisions 面板，左右两栏对照，手动选择保留或合并，比命令行直观得多。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| IDEA 提示 Git 未安装/找不到 | 确认命令行 `git --version` 能用；然后在 Settings → Version Control → Git 里把 Path 指到 git.exe |
| 在 IDEA 里 Commit 了却 Push 不上去 | Commit 只是本地 commit，**Push 是另一个动作**；先 Pull 解决分歧再 Push |
| 冲突面板里点"Accept Yours / Accept Theirs" | 慎用"全部接受某一边"；复杂冲突用左右 Merge 面板逐段确认（和命令行同理） |

@@summary
| 问题 | 答案 |
|---|---|
| 标签是什么 | 钉在某个 commit 上的永久记号，用于标记发布版本（v1.0.0） |
| 标签和分支区别 | 分支随提交移动，标签不动；都是"贴纸"，删了不影响 commit |
| 创建标签 | 轻量 `git tag 名`；发布用附注 `git tag -a 名 -m 说明`；可指定旧提交 |
| 标签远程操作 | `git push origin 标签名`；删远程 `git push origin :refs/tags/标签名` |
| Git Flow 是什么 | 一套分支管理规范：谁基于谁、合并到哪、何时打标签 |
| 五大分支 | master 线上 / develop 开发 / feature 功能 / release 发布 / hotfix 修补 |
| master 铁律 | 不直接开发，只收合并，每个合入打标签 |
| IDEA 集成 | 配置 Git 路径；Commit / Push / Pull / Clone / 分支 / 冲突处理全有图形界面 |

一句话记住本章：**标签 = 钉死的版本记号（发布打 tag、push 要单独带）；Git Flow = 分支的行为规范——feature 从 develop 开、进 develop；release 测试后双合 master+develop；hotfix 从 master 开、修完双向补，master 每次合入必打标签；日常用 IDEA 的 Commit / Push 面板就能走完这套流程。**

@@quiz
1. 标签和分支的区别是什么？为什么"发布版本必须用标签而不能用分支名"？
2. 轻量标签和附注标签的区别？发布版本推荐哪一种？
3. 怎么把本地标签推送到远程？怎么删除远程标签（固定写法）？
4. 直接 `git checkout v1.0.0` 修改代码有什么风险？正确姿势是什么？
5. Git Flow 的五个分支分别干什么？feature、release、hotfix 各自从哪创建、合并到哪？
6. 为什么 hotfix 要同时合并到 master 和 develop？
7. IDEA 里"Commit"和"Push"是两个动作，什么时候需要用 Push？

@@links
参考|Git版本控制管理（86 页）|#
文档|Git 基础 · 打标签|https://git-scm.com/book/zh/v2/Git-基础-打标签
文档|Git Flow 成功分支模型（原文）|https://nvie.com/posts/a-successful-git-branching-model/
文档|Git 官方文档|https://git-scm.com/doc