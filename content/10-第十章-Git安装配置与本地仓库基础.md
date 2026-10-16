@@h1 第十章　Git 安装配置与本地仓库基础
@@sub 阶段 18 · 云原生开发环境与 DevOps 工具链　|　版本控制　|　难度 ★★★

@@why 这一章在解决什么问题
上一章讲完了"版本控制是什么"，这一章开始动手：装 Git、登记身份、把第一个目录变成仓库，然后走通"改文件 → add → commit"的第一条流水线。

学完你会发现，Git 的第一步不是复杂，是**琐碎**——很多新手死在装完不知道先干嘛，或者提交时报错"作者身份没配置"，或者误入 vim 编辑器退不出来。这一章把这些坎全部提前踩平。

@@map 这一章在整个知识库里的位置
**上一章**：Git 的世界观——分布式、四大区域、快照存储
**本章** ← 你在这里：装好工具、配好身份、初始化第一个本地仓库、提交第一个版本
**下一章**：基于本地仓库玩日志、diff 和版本还原——包括写代码最需要的"后悔药"（reset）

@@point ① 安装 Git：Windows 一个包，Linux 一条命令
@@need 要解决什么
要让 Git 管你的代码，先得让电脑上有 `git` 这个命令。装错了版本、装完找不到入口，是本章第一道坎。

@@idea 核心思路
- **Windows**：打开官网 https://git-scm.com/download/win 下载 64 位安装包，整体是"下一步式"安装，唯一要留神的是**附加任务勾选项**（是否把 Git 加入 PATH、是否添加右键菜单）。安装完成后，开始菜单里会出现 **Git Bash**（一个 Linux 风格命令行），后面所有命令都在里面敲。
- **Linux（Ubuntu/Debian）**：

```bash
sudo apt update            # 先更新软件源
sudo apt install git       # 安装 git
git --version              # 验证安装成功，会打印版本号
```

装完统一用一条命令验证：`git --version`。能打印出版本号，说明装好了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Windows 装完在终端里敲 git 没反应 | 安装时没勾选"加入 PATH"，或终端没重开；**重启终端**再试，还不行就重新安装，注意勾选 Add to PATH |
| 下载安装包特别慢 | 官网走不动时国内可换镜像；Linux 用 apt 源基本不会慢 |
| 装了 Git 但找不到"Git Bash" | 在任意项目文件夹右键选 "Git Bash Here"，或从开始菜单搜索打开 |

@@point ② 先登记身份：user.name 和 user.email
@@need 要解决什么
Git 每次提交都会记录"**谁**在什么时候提交了什么"。如果没登记身份就提交，Git 会直接报错拒绝，或者留下一些无名记录——团队里根本没法追责、没法回溯。

@@idea 核心思路
装完 Git **第一件事**就是设置用户名和邮箱（这只是**署名信息**，不是账号密码）：

```bash
git config --global user.name "yourname"          # 填你的名字（这里是占位符，别照抄）
git config --global user.email "your@example.com" # 填你的邮箱（同上）
```

- `--global` 表示**这台机器上所有仓库**都默认用这个身份，配一次就行；
- 邮箱通常填你注册代码托管平台的那个邮箱，提交记录里会显示它。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 提交时报错 "Please tell me who you are" | 没配 user.name/user.email；按上面两条命令配置后重新提交 |
| 提交记录里作者是别人的名字 | 这台电脑的 `--global` 配置被共用过；用 `--local` 在当前仓库覆盖成自己的（见下一点） |
| 以为这里填的是登录密码 | 不是！这是**显示在提交记录里的署名**；真正保密的身份凭证是 Token/SSH Key（第十二章讲） |

@@point ③ 配置的三个作用域：system / global / local
@@need 要解决什么
在公司电脑配了自己的名字，回家想用另一个邮箱；或者 A 项目用公司身份、B 项目用个人身份——如果只有一个"全局配置"，这些场景全乱套。

@@idea 核心思路
Git 配置分三个层级，**越往下优先级越高**：

| 层级 | 命令 | 存在哪 | 生效范围 |
|---|---|---|---|
| 系统级 | `git config --system ...` | Git 安装目录 | 这台电脑所有用户 |
| 全局级 | `git config --global ...` | `~/.gitconfig` 文件 | 当前用户的**所有**仓库 |
| 仓库级 | `git config --local ...` | 当前仓库的 `.git/config` | **只对当前仓库**生效 |

同名配置冲突时，**local 覆盖 global，global 覆盖 system**。想单独给某个仓库改身份：

```bash
git config --local user.name "yourname2"   # 只改当前仓库的署名
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 改了 --global 但当前仓库还是旧身份 | 该仓库有 `--local` 配置，local 优先级更高；用 `git config --local --unset user.name` 删掉它 |
| 配置文件在哪个路径找不到 | Windows 上在 `~/.gitconfig`（用户主目录）；`git config --list --show-origin` 能告诉你每条配置来自哪个文件 |
| 以为 --system 是"系统自动的"，不用管 | 它是给多用户电脑用的；普通个人机直接忽略 --system 即可 |

@@point ④ 查看配置：确认自己"是谁"
@@need 要解决什么
配过身份后，过几天忘了自己配没配、配成什么了怎么办？提交记录身份不对，怎么排查？

@@idea 核心思路

```bash
git config --list            # 列出当前生效的所有配置（三个层级合并后的结果）
git config user.name         # 只查某一个配置项，比如当前名字
git config user.email        # 查当前邮箱
```

`--list` 会把 global、local 等所有配置**合并打印**，一眼看全。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `--list` 输出里同一个 key 出现两次 | 不同作用域各配了一次，**后面的（local）覆盖前面的（global）**——这本身也是排查线索 |
| 查出来邮箱是空的 | 之前没配过 email；补上 `git config --global user.email ...` |

@@point ⑤ git init：把普通文件夹变成仓库
@@need 要解决什么
装好 Git 之后，你不会魔法——你的项目文件夹还是普通文件夹，**Git 不会自动开始管它**。要让 Git 接管，得执行"初始化"。

@@idea 核心思路

```bash
mkdir my-project     # 创建一个项目目录（也可以直接进已有目录）
cd my-project        # 进入该目录
git init             # 初始化：让 Git 开始对这个目录做版本控制
```

执行后目录里会多出一个隐藏的 `.git` 文件夹——**整个 Git 的精华（全部历史记录、暂存区、配置）全在这个文件夹里**。以后这个目录的所有版本历史都存在 `.git` 中，移动/备份项目时整个文件夹一起搬。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 目录里看不到 `.git` | 它是隐藏文件夹；在文件资源管理器里开启"显示隐藏项目"，或在 Git Bash 里用 `ls -al` |
| 把 `.git` 删了 | **历史全没了**，已提交的文件也救不回（第十一章会强调） |
| 在错误目录（比如用户主目录）执行了 git init | 会把整个目录纳入管理范围；确认没东西要留时，删掉该 `.git` 即可撤销初始化 |

@@point ⑥ git status：随时知道文件处于什么状态
@@need 要解决什么
"该提交的没提交、不该提交的却提交了"——这种翻车几乎是每个新手必经。Git 给了解药：一个命令告诉你**每个文件现在处于什么状态**。

@@idea 核心思路

```bash
git status                    # 查看当前工作区/暂存区的状态
git status -s                 # -s：简洁输出，一行一个文件
```

典型输出（未提交任何内容时）：

```bash
$ git status
On branch master
No commits yet
Untracked files:
  (use "git add <file>..." to include in what will be committed)
        a.txt
```

`Untracked files`（未跟踪）的意思是：这个文件在文件夹里，但**还没交给 Git 管理**。养成习惯：**提交前先 `git status` 看一眼**，确认清单里没有不该提交的东西。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| status 显示某个文件是 Untracked，但你觉得自己提交过 | 提交的是另一份副本或另一个文件名；认真看路径 |
| 输出里文件太多，一个个看不过来 | 用 `-s` 简洁模式，或按需 `git status 某个文件` |

@@point ⑦ 文件的四种状态：untracked / unmodified / modified / staged
@@need 要解决什么
`git status` 输出里的英文单词到底什么意思？"已跟踪"又是什么鬼？

不理解状态机，你就永远靠猜——这里一共只有四种状态，搞懂一次，终身受用。

@@idea 核心思路
| 状态 | 含义 | 怎么进入 | 下一步去哪 |
|---|---|---|---|
| **untracked（未跟踪）** | 文件在文件夹里，但 Git 不认识它 | 新建文件 | `git add` → staged |
| **unmodified（未修改）** | 已入库，内容与版本库一致 | `git commit` 之后 | 改它 → modified；`git rm` 移出 → untracked |
| **modified（已修改）** | 改过了但还没 add | 修改 unmodified 文件 | `git add` → staged；`git checkout --` → 丢弃修改 |
| **staged（已暂存）** | 改动已放入暂存区，等提交 | `git add` 之后 | `git commit` → unmodified；`git reset HEAD` → modified |

生命周期绕一圈：**新建 → untracked → add → staged → commit → unmodified → 修改 → modified → add → staged → commit……** 状态会随着你执行的命令不断变化。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 提交后文件又变成 modified，但你没改过 | 可能是行尾符/编码被工具自动改过（CRLF/LF）；属正常现象，用 diff 确认内容 |
| 以为 staged 就是"已保存" | staged 只是**暂存**，异常情况下可能丢；`git commit` 之后才真正进版本库 |

@@point ⑧ git add 与 git reset：进出暂存区
@@need 要解决什么
暂存区是"待提交清单"。把文件加进清单用 `git add`；加错了想撤回来？用 `git reset`。这一进一出，是本地操作最高频的两个命令。

@@idea 核心思路

```bash
git add a.txt             # 把 a.txt 加入暂存区
git add .                 # 把当前目录所有改动加入暂存区（常用）
git add src/              # 加入某个目录的全部改动

git reset a.txt           # 把 a.txt 移出暂存区（文件改动还在，只是取消暂存）
git reset                 # 把暂存区全部清空回退
```

注意：`git reset 文件名` **只取消暂存，不丢失你的修改**——文件里的改动都还在，只是不排队提交了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `git add .` 把一堆编译产物也加进去了 | 见第十一章 `.gitignore`，先把要忽略的文件列出来再 add |
| reset 后以为"文件不见了" | reset 只动暂存区，**工作区的改动还在**；真会丢文件的是后面的 `reset --hard` |
| 以为 reset 是"撤销修改" | 不是！reset 只是**取消暂存**；丢弃修改用的是 `git checkout -- 文件` |

@@point ⑨ git commit：正式存档
@@need 要解决什么
`git add` 只是把改动登记到暂存区，**还没真正存档**。要让这个版本永久留在历史里，必须 `git commit`——并且要**写清楚这次干了什么**。

@@idea 核心思路

```bash
git commit -m "完成用户登录功能"     # -m 后面跟提交说明，简短清楚即可
```

- 提交时**不加 `-m`** 会进入"先写说明再提交"的编辑器模式（默认 vi/vim），新手常常卡在里面出不来；
- 提交说明写"做了什么、为什么"，中英文都行，关键是**别人（和未来的你）能看懂**；
- commit 之后，暂存区清空，文件回到 unmodified 状态——这次改动正式成为历史里的一个版本，被**永久保存**下来。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 误入 vim 编辑器退不出来 | 按 `Esc`，输入 `:q!` 回车放弃退出；或 `:wq` 保存退出后再补提交 |
| 提交后发现说明写错了 | 见下一个知识点 `--amend`，它只改最后一条提交 |
| 以为 commit 就是"保存到云端" | commit 只进**本地仓库**，远程仓库要靠 push（第十二章） |

@@point ⑩ 改错的提交信息：--amend 救急
@@need 要解决什么
提交信息写错字、或者漏了一个文件进去——已经 commit 了，怎么办？办法不是删库跑路，而是用一个参数**改写最后一条提交**。

@@idea 核心思路

```bash
git commit --amend -m "修正后的提交说明"   # 改写最后一条提交的说明
git commit --amend                          # 配合 git add 可以顺便补提交漏掉的文件
```

`--amend` 的本质是"**用一个新提交替换最后一条**"——提交号会变，但内容整合成一条，历史看起来干干净净。注意它只能改**最后一次**提交；更早的历史改写要用 `git rebase`（进阶内容，本阶段不展开）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 对已经 push 到远程的提交用 --amend | 会产生"本地和远程历史不一致"，下次 push 被拒；**已推送的提交尽量别 amend**，除非你清楚后果 |
| amend 后提交号变了，以为代码丢了 | 没丢，只是换了个新提交顶替旧提交，文件内容都在 |

@@summary
| 问题 | 答案 |
|---|---|
| 怎么安装 Git | Windows 官网下载安装包（留意 PATH 勾选）；Linux 用 apt 等包管理器；`git --version` 验证 |
| 装完第一件事 | 配 `user.name` / `user.email`，否则无法提交 |
| 配置有几个作用域 | system / global / local，local 优先级最高；global 存在 `~/.gitconfig` |
| 怎么把目录变成仓库 | `git init`，生成 `.git` 隐藏文件夹 |
| 怎么知道文件状态 | `git status`；四种状态 untracked / unmodified / modified / staged |
| 怎么提交 | `git add` 进暂存区 → `git commit -m "说明"` 落库；`git reset` 取消暂存 |
| 提交信息写错了 | `git commit --amend -m "新说明"` 改写最后一条 |

一句话记住本章：**装好 Git 先配身份（--global 署名），git init 开张，add 进清单、commit 落库，随时 git status 看状态——这一套"改 → add → commit"就是本地仓库的日常循环，也是后面所有 Git 操作的地基。**

@@quiz
1. 为什么装完 Git 必须先配置 user.name 和 user.email？不配会怎样？
2. `--global` 和 `--local` 配置的区别是什么？同时存在时谁生效？
3. 文件的四种状态是什么？从"新建文件"到"版本入库"依次经过哪些状态？
4. `git add` 做错了想取消，用什么命令？文件里的修改会不会丢？
5. commit 时误入 vim 编辑器，怎么退出？
6. `git commit --amend` 能改哪一次提交？对已推送的提交使用会有什么后果？

@@links
讲义|Git版本控制管理讲义（86 页）|#
文档|Git 安装|https://git-scm.com/book/zh/v2/起步-安装-Git
文档|Git 初次运行前的配置|https://git-scm.com/book/zh/v2/起步-初次运行-Git-前的配置
文档|Git 官方文档|https://git-scm.com/doc