@@h1 第十八章　Dockerfile 镜像定制
@@sub 阶段 18 · 云原生开发环境与 DevOps 工具链　|　容器化　|　难度 ★★★★

@@why 这一章在解决什么问题
`docker pull` 的现成镜像，经常"差点意思"：你想跑 Tomcat 9 + JDK 8 + 自己的环境变量，仓库里没有一个完全对味的。
难道每次都要：拉镜像 → run 容器 → 手动装东西 → commit 固化？太原始了，也不可复现——你同事照着做一遍，结果可能完全不同。
**Dockerfile 就是"镜像的配方文件"**：用几行指令把"怎么拼装这个环境"写清楚，`docker build` 一键产出可复现的镜像。
版本、依赖、指令全在文件里，能和代码一起进 Git——**环境从此可版本管理**。

@@map 这一章在整个知识库里的位置
**上一章**：容器数据卷——让数据活下来
**本章** ← 你在这里：从"用别人的镜像"到"造自己的镜像"
**下一章**：容器网络与联动——容器之间怎么互相访问
**阶段终点**：会自造镜像，才握有"环境即代码"的钥匙

@@point ① 为什么自定义镜像：现成的总是不对味
@@need 要解决什么
仓库里光 Tomcat 相关镜像就有一堆，为什么还要自己构建？先把你被"逼到"自己动手的理由理清。

@@idea 核心思路
用仓库里的镜像可以解决"能跑"，但解决不了"正好"：

| 需求 | 现成镜像的问题 |
|---|---|
| 项目要 Tomcat 9.0.x 特定版本 | 仓库里往往是默认最新版，版本不是你说了算 |
| 项目要特定的 JDK | 有的镜像绑死了 JDK 8，和你想要的组合不一致 |
| 环境变量、启动参数定制 | 现成镜像的启动命令是它自带的，你不好改 |
| 环境要"可复现、可分享" | 手动改过的容器没法给团队复制成一致环境 |

`docker search tomcat | wc -l` 一看就是几十上百个 tomcat 镜像——但这些**都不是"你的版本"**。
所以生产环境讲究自建镜像：**从基础镜像出发，按自己的配方精确拼装**。

@@point ② Dockerfile 四部分结构：一张配方表
@@need 要解决什么
"配方"长什么样？有没有固定套路？——有，Dockerfile 就是**一行行指令的文本文件**，分四部分，照着写不会乱。

@@idea 核心思路
Dockerfile 只是一个文本文件（名字就叫 `Dockerfile`，无扩展名），每条指令一行，`#` 开头是注释。结构固定四段：

| 部分 | 关键字 | 必须吗 | 干什么 |
|---|---|---|---|
| ① 基础镜像 | FROM | **必须**（第一行） | 站在谁的肩上 |
| ② 维护者信息 | MAINTAINER | 可选 | 这镜像谁做的 |
| ③ 镜像操作指令 | RUN / COPY / ADD / ENV 等 | 按需 | 往镜像里装东西、改配置 |
| ④ 容器启动指令 | CMD / ENTRYPOINT | 按需 | 容器 run 起来时执行什么 |

```dockerfile
# 第一行必须指定基础镜像
FROM java:8

# 维护者信息（写占位信息即可，别写真名真邮箱）
MAINTAINER yourname yourname@gmail.com

# 镜像操作指令：构建时执行
RUN echo "开始安装 Tomcat..."

# 容器启动执行指令：run 时执行
CMD /usr/local/tomcat/bin/catalina.sh
```

**核心区别**：第 ③ 段是**构建时**执行（做镜像时跑一次），第 ④ 段是**运行时**执行（每次启动容器都跑）——这个区别是本章最重要的认知，很多坑都源于搞混它。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Dockerfile 第一行不是 FROM 直接报错 | FROM 必须第一行（注释除外），它决定了整个构建的基座 |
| 把 CMD 当"构建时命令"用 | CMD 只影响容器启动；构建时的安装动作要写 RUN |
| 忘了 MAINTAINER | 不写也能构建，但"这镜像谁维护的"无从追溯；团队协作建议写占位名 |

@@point ③ FROM：站在巨人的肩膀上
@@need 要解决什么
自己从零拼一个 Linux + JDK + Tomcat？那不叫自制，叫造轮子。FROM 让你从别人做好的基础镜像开始。

@@idea 核心思路
```dockerfile
FROM centos              # 从 centos 最新版开始（不写 tag=latest）
FROM java:8              # 从 java 8 标签开始（更可控）
FROM ubuntu:22.04        # 指定具体版本
```

选基础镜像的原则：**够用就选官方精简的**（如 openjdk、centos、alpine），体积小、漏洞少；越底层，你后面要装的越多。
tag 建议写死，避免"今天构建和三个月后构建出两个环境"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| FROM 不写 tag 能构建但心里没底 | 会用 latest，环境不可复现；**写死 tag 是生产铁律** |
| 基础镜像选得太重 | centos 默认几百 MB，alpine 才几 MB；按需选，别盲目上"全家桶" |

@@point ④ RUN：构建时执行命令，每一条加一层
@@need 要解决什么
往镜像里装 wget、解压文件、写配置——"装东西"的活全交给 RUN。但它有个大坑：**每写一条 RUN，镜像就多一层**。

@@idea 核心思路
RUN 有两种写法：

```dockerfile
# 1. shell 格式：直接写命令
RUN yum install -y wget

# 2. exec 格式：写成 JSON 数组（可执行文件 + 参数）
RUN ["yum", "install", "-y", "wget"]
```

**"每执行一条 RUN 命令，镜像就会添加新的一层"**——层数越多镜像越大、构建越慢。优化办法是**把多条 RUN 用 && 连成一条**（本章最后一个知识点专讲）。
RUN 的中间结果会被**缓存**：下次构建时，如果这条 RUN 没变，直接复用缓存层，构建飞快；想强制重来，加 `docker build --no-cache`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 改了后面的 RUN，构建却还是很慢 | 前面的层被缓存复用了；整套重建用 `docker build --no-cache` |
| 一条 RUN 一条 RUN 堆了 20 层 | 镜像又大又慢；用 `&&` 合并（见本章末） |
| RUN yum install 报"没有可用的软件包" | 基础镜像太精简没配源/源失效；先配置 yum 源或换基础镜像 |

@@point ⑤ WORKDIR：设工作目录，之后的命令都在这干活
@@need 要解决什么
后面的 RUN、CMD、COPY 等命令默认在根目录执行，路径全得写绝对路径，烦且容易错。能不能"先 cd 过去"？

@@idea 核心思路
```dockerfile
WORKDIR /usr/local      # 之后所有命令默认在这个目录下执行
RUN mkdir docker        # 等价于 mkdir /usr/local/docker

WORKDIR /a
WORKDIR b               # 相对上一个：/a/b
WORKDIR c               # 再相对：/a/b/c
```

- WORKDIR 类似 `cd`，但**它是写进镜像的"默认目录"**，影响其后的 RUN、CMD、ENTRYPOINT、ADD、COPY；
- `docker run` 时可用 `-w` 参数临时覆盖镜像里设的工作目录（本次运行有效，不改镜像）。
选择建议：给应用建一个专属目录（如 `/opt/myapp`）作 WORKDIR，别全堆根目录。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| WORKDIR 写相对路径结果莫名嵌套 | 相对路径是**相对上一个 WORKDIR** 的；想从根开始就写 `/a` 这种绝对路径 |
| 进入容器后发现不在预期目录 | 检查 CMD 是否被 docker run 参数覆盖了（覆盖后可能换目录），或镜像里 WORKDIR 没设成你以为的路径 |

@@point ⑥ COPY 与 ADD：把文件搬进镜像
@@need 要解决什么
镜像里要有你的代码、配置、压缩包——这些宿主机文件怎么"灌"进镜像？两个命令看着像，坑点不同。

@@idea 核心思路
```dockerfile
# COPY：单纯拷贝，不做任何加工
COPY ./start.sh /start.sh          # 相对路径 → 工作目录
COPY ./conf/ /etc/myapp/           # 整个目录拷过去

# ADD：COPY 增强版（会自动解压 tar 包，支持远程 URL）
ADD ./apache-tomcat-9.0.50.tar.gz /usr/local/   # tar 会自动解压
ADD hom* /mydir/                   # 通配符，所有 hom 开头的文件
ADD test /absoluteDir/             # 拷到绝对路径
ADD test relativeDir               # 拷到 WORKDIR/relativeDir
```

区别一句话：

| | COPY | ADD |
|---|---|---|
| 拷贝文件 | ✅ | ✅ |
| tar 包自动解压 | ❌ | ✅ |
| 支持网络 URL（类似 wget） | ❌ | ✅（远程压缩包**不解压**） |

**推荐：只要不是解压 tar、拉 URL，一律用 COPY**——ADD 的"智能"行为有时反而是意外来源（莫名解压、默默下载）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| ADD 一个远程 .tar.gz 没被解压 | 网络资源 ADD 只下载不解压，这是设计使然；先 ADD 到镜像再 RUN 手动解压 |
| 以为 COPY 也自动解压 | COPY 纯拷贝，不会解压；要解压用 ADD 或 RUN tar 命令 |
| 构建时找不到 ./xxx 文件 | 文件必须存在于"构建上下文"（执行 docker build 的目录）里；不在会直接报错 |

@@point ⑦ ENV：塞环境变量，一次设置处处可用
@@need 要解决什么
Java 项目要 JAVA_HOME，程序要读数据库连接串——环境变量从哪来？用 ENV 在镜像里预埋。

@@idea 核心思路
```dockerfile
ENV JAVA_HOME=/usr/local/jdk1.7.0_79
ENV PATH=$JAVA_HOME/bin:$PATH
```

- 设置后，**构建期**后续指令（RUN 等）和**运行期**容器内程序都能直接读到；
- `$JAVA_HOME` 这种引用上一个 ENV 的写法成立（按顺序赋值）；
- 运行容器时还可以用 `-e 键=值` 临时追加/覆盖（不写进镜像，只本次运行有效）；
- 把 PATH 带上 `$JAVA_HOME/bin` 是最常用套路，命令直接就能用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 容器里 echo $JAVA_HOME 是空的 | 检查 ENV 是否真写进了镜像（docker inspect 看 Config.Env）；或你换用户/终端了，环境变量没继承全 |
| 把数据库密码写进 ENV 再推到仓库 | 致命：ENV 会打进镜像，别人 pull 就能看到；敏感信息用运行时 -e 或密钥注入，**绝不写进镜像** |

@@point ⑧ EXPOSE：声明端口（但不会自动打开！）
@@need 要解决什么
你的镜像里跑的是 Tomcat，外界要访问 8080。很多人以为写了 EXPOSE 8080 就通了——大错，这一步只是"声明"。

@@idea 核心思路
```dockerfile
EXPOSE 8080   # 告诉使用者：我这个镜像的容器默认监听 8080
```

- EXPOSE 只做**文档化声明**，让 `docker ps` 和 `docker run -P`（自动映射）知道该暴露哪些端口；
- **它不会真的把端口对外开放**；
- 想真正访问，必须 `docker run -p 宿主机端口:8080` 映射发布（第 16 章讲过），或用 `-P` 一次发布所有 EXPOSE 端口。

```
镜像(EXPOSE 8080) ──光声明不开门──► docker run -p 9090:8080 ──► 宿主机 9090 ──► 浏览器可访问
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 写了 EXPOSE 8080 但外面还是连不上 | EXPOSE 不是开门，-p/-P 才是；这是 Dockerfile 新手最常见的认知坑 |
| EXPOSE 和 -p 的数字不一致导致连不上 | EXPOSE 只是"提示"，真正流量走的是 -p 指定的映射；-p 的"容器内端口"必须对得上应用真实监听的端口 |

@@point ⑨ CMD：容器启动时要执行的命令
@@need 要解决什么
镜像造好了，容器 run 起来那一刻要跑什么程序？总得给它一个"开机自启"的入口——这就是 CMD。

@@idea 核心思路
```dockerfile
# 两种格式
CMD echo "hello Dockerfile"       # shell 格式
CMD ["java", "-version"]          # exec 格式（推荐，无多余 shell 层）

# 第三种写法：作为 ENTRYPOINT 的默认参数（下一点讲）
CMD ["-b"]
```

CMD 的三大性质（全是考点）：
1. **晚于 RUN**：RUN 构建时跑，CMD **容器启动时**跑；
2. **只有一个生效**：写多条 CMD，只有最后一条生效；
3. **可被替换**：`docker run 镜像 自定义命令` 会把 Dockerfile 里的 CMD 整个顶掉。

```cmd
# 镜像里写的是 CMD ["java","-version"]，但你这样 run：
docker run 我的镜像 ls /       # 实际执行 ls /，CMD 被替换了
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Dockerfile 写了三条 CMD 只跑了一条 | CMD 只有最后一条生效，前面的是"死代码"；要串行执行用 RUN 或 `&&` 连起来 |
| docker run 传了参数，发现启动命令"变"了 | CMD 设计上就可被 run 参数替换；不想让启动命令被替换 → 用 ENTRYPOINT（下一点） |
| exec 格式漏了引号/逗号 | JSON 数组格式要用双引号，写错会构建失败；shell 格式则无此问题 |

@@point ⑩ ENTRYPOINT vs CMD：一个可被替换，一个打不死
@@need 要解决什么
有些容器的"主程序"（比如 top 监控、Tomcat）你不希望被 run 参数误替换；但又想允许附加参数。CMD 和 ENTRYPOINT 的分工就是为这个设计的。

@@idea 核心思路
```dockerfile
# 镜像1：只用 CMD
FROM centos
CMD ["ls", "-a"]

# 镜像2：ENTRYPOINT 配 CMD（CMD 变成"默认参数"）
FROM centos
ENTRYPOINT ["ls"]       # 主命令，打不死
CMD ["-a"]              # 默认参数，可被替换
```

行为对比：

| 场景 | 只有 CMD | ENTRYPOINT + CMD |
|---|---|---|
| docker run 镜像 | 执行 ls -a | 执行 ls -a |
| docker run 镜像 -l | **整个 CMD 被替换**，执行 -l（报错！） | **ENTRYPOINT 不动**，-l 追加为参数 → 执行 ls -l ✅ |

核心结论：
- **CMD：可被替换**（run 的参数会直接替换整个 CMD）；
- **ENTRYPOINT：可追加**（run 的参数会"追加"到 ENTRYPOINT 后面）；
- Dockerfile 里 ENTRYPOINT 也**只有最后一条生效**。

常用套路：ENTRYPOINT 写死主程序，CMD 给默认参数，使用者可换参数不改程序。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| ENTRYPOINT 写了多条也只执行最后一条 | 和 CMD 一样，只有最后一条生效，别写多条 |
| 想替换 ENTRYPOINT 却换不掉 | 默认设计就是"打不死"；docker run 加 `--entrypoint` 参数可临时覆盖（高级用法） |
| 以为 ENTRYPOINT 和 CMD 随便换着用 | 定位不同：CMD 管"默认动作"，ENTRYPOINT 管"固定主程序"；面试就爱问这个 |

@@point ⑪ 三个配角：VOLUME / USER / ONBUILD
@@need 要解决什么
13 种指令里还有三个不常出镜但面试爱提的：持久化目录、运行用户、给"别人的镜像"埋钩子。

@@idea 核心思路
```dockerfile
# VOLUME：在镜像里声明"这里要挂卷"（容器没挂也自动生成匿名卷）
VOLUME ["/data"]
VOLUME ["/var/www", "/var/log/apache2"]     # 可声明多个

# USER：之后 RUN/CMD/ENTRYPOINT 用什么用户跑（默认 root）
USER 你的用户名          # 只写用户
USER 用户:用户组         # 用户+组
#    run 时可用 -u 临时覆盖

# ONBUILD：给"别人的镜像"埋的触发器
ONBUILD RUN mkdir test    # 别人 FROM 你这个镜像时，这条 RUN 才会执行
```

要点：
- VOLUME 声明后，**run 时就算不写 -v，Docker 也会生成匿名卷**（这解释了第 17 章"没挂卷为什么有卷"的疑问）；卷的特性：可跨容器共享、修改立即生效、不影响镜像本身、没容器用了才消失；
- USER 之后所有指令都以该用户运行，**权限相关的坑**都出在这；
- ONBUILD 常用于发布"基础镜像"让别人继承时，埋初始化动作。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 容器里写文件报 permission denied | 镜像里 USER 已切到非 root，而目标目录属主是 root；调整目录权限或视情况用 root 用户 |
| ONBUILD 写了没触发 | ONBUILD 只在**被别人 FROM** 时才触发；你自己 build 这个镜像不会执行它 |
| 声明了 VOLUME 数据却"找不到" | 没显式挂卷时它进了匿名卷（/var/lib/docker/volumes/xxxx/_data），用 docker inspect 找 |

@@point ⑫ docker build：把 Dockerfile 变成镜像
@@need 要解决什么
配方写好只是文本，怎么变成能 run 的镜像？——`docker build` 就是"烘焙机"。

@@idea 核心思路
```cmd
# -t 给镜像起名（名字:版本）；末尾的 . 指"Dockerfile 在当前目录"
docker build -t 镜像名字:版本 .

# 例：构建名为 test04、版本 v1 的镜像
docker build -t test04:v1 .

# 例：带名字的 Tomcat 镜像
docker build -t tomcat:1.0 .
```

两个关键点：
- `-t`：镜像名:tag，好记好引用；不写版本会落到 latest；
- **最后一个 `.`（构建上下文）**：Docker 会把当前目录打包发给引擎，Dockerfile 里的 COPY/ADD 只能引用这个目录里的文件。

**通用三步走**：编写 Dockerfile → `docker build -t 名字:版本 .` → `docker run 名字:版本`。
构建日志里能看到每条指令的"以 shell 形式运行"提示，确认每步都干成了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 报 "unable to prepare context: path not found" | 当前目录没有 Dockerfile；或文件名写成了 dockerfile.txt。文件名必须叫 `Dockerfile`（或 build 时用 `-f` 指定） |
| COPY 的文件明明在却说找不到 | 文件必须在**构建上下文目录**里（build 命令那个 `.`），上下文外的一律不可见 |
| 构建整天卡在下载 | 基础镜像拉取慢：先配镜像加速，或先 `docker pull` 基础镜像让缓存生效 |

@@point ⑬ 实战：从零构建一个 Tomcat 镜像
@@need 要解决什么
把前面 12 个知识点串成一条线：手写一个"JDK 8 + Tomcat 9 + 环境变量"的自定义镜像。这是本章的大结局。

@@idea 核心思路
步骤：准备 Dockerfile 与 tomcat 安装包 → build → run → 访问验证。

```dockerfile
# 1. 基础镜像：自带 JDK 8
FROM java:8

# 2. 维护者（占位信息）
MAINTAINER yourname yourname@gmail.com

# 3. 把 Tomcat 9 压缩包拷进镜像并自动解压到 /usr/local
ADD ./apache-tomcat-9.0.50.tar.gz /usr/local

# 4. 设工作目录
WORKDIR /usr/local
```

环境部分搞定，接下来是环境变量、端口声明和启动命令：

```dockerfile
# 5. 环境变量：Tomcat 路径写死，bin 目录加入 PATH
ENV TOMCAT_HOME=/usr/local/apache-tomcat-9.0.50
ENV PATH=$PATH:$TOMCAT_HOME/bin

# 6. 声明端口
EXPOSE 8080

# 7. 启动命令：启动 Tomcat，并持续输出日志（tail -F 防止容器退出）
CMD startup.sh && tail -F /usr/local/apache-tomcat-9.0.50/bin/catalina.out
```

```cmd
# 构建（apache-tomcat-9.0.50.tar.gz 要和 Dockerfile 在同目录）
docker build -t mytomcat:1.0 .

# 运行并访问：浏览器打开 http://localhost:8080
docker run --name tomcat -d -p 8080:8080 mytomcat:1.0
```

关键设计点：
- `CMD startup.sh && tail -F catalina.out`：因为**容器会随主进程退出而停止**，Tomcat 是后台启动的（startup.sh 秒退），所以必须用 `tail -F` 顶住前台，容器才能常驻；
- 为什么不用仓库现成 tomcat 镜像？——版本、JDK、变量都是"你要的"，可复现、可进 Git。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 容器秒退，STATUS 显示 Exited(0) | 启动命令里没有"前台常驻"进程；参考上面的 tail -F 顶住，或用 `/bin/bash` 挂交互终端 |
| 访问不到页面 | ① docker ps 确认在跑；② -p 映射的容器内端口是否 8080（Tomcat 默认）；③ 浏览器地址用 localhost |
| build 报解压失败 | ADD 的 tar 包损坏，或文件名和 Dockerfile 里写的不一致；核对文件名 |

@@point ⑭ 构建优化：合并 RUN，让镜像"瘦身"
@@need 要解决什么
一个坑你没注意到：**RUN 每写一条就多一层**。装软件的命令写成七八条 RUN，镜像体积和构建时间都爆炸。怎么压？

@@idea 核心思路
用 `&&` 把多条命令串进**一条 RUN**：

```dockerfile
# 优化前：4 条 RUN = 4 层
RUN rm -rf /etc/yum.repos.d/*
RUN curl -o /etc/yum.repos.d/CentOS-Base.repo http://xxx
RUN curl -o /etc/yum.repos.d/epel.repo http://xxx
RUN yum install -y nginx

# 优化后：1 条 RUN = 1 层（\ 是续行符）
RUN rm -rf /etc/yum.repos.d/* && \
    curl -o /etc/yum.repos.d/CentOS-Base.repo http://xxx && \
    curl -o /etc/yum.repos.d/epel.repo http://xxx && \
    yum install -y nginx
```

原理：**Dockerfile 每条指令生成一个镜像层**，层越多镜像越大、传输越慢、构建越久。
其他减量技巧：
- 装完的临时文件在同一 RUN 内顺手删掉（如 `yum install ... && yum clean all`）；
- 基础镜像选小的（alpine 系）；
- 尽量避免多次 ADD 大文件。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 合并 RUN 后一条失败全失败 | `&&` 语义就是"前面失败后面不跑"；这反而好——定位到失败的子命令，在合并块里找 |
| 为了少层把 curl、tar、clean 全挤一行，阅读困难 | 平衡：`\` 续行 + 每行一个命令注释，可读性优先于极端瘦身 |
| 构建一直"复用到旧缓存" | RUN 内容变了缓存才会失效；`--no-cache` 强制重建 |

@@summary 本章小结
| 问题 | 答案 |
|---|---|
| 为什么自己造镜像 | 现成镜像版本/JDK/变量都对不上，且不可复现 |
| Dockerfile 是什么 | 文本配方文件，四部分：FROM / MAINTAINER / 构建指令 / 启动指令 |
| 每部分怎么用 | FROM 必须第一行；MAINTAINER 写占位；RUN 构建时跑；CMD 运行时跑 |
| 搬文件用谁 | 纯拷贝用 COPY；要解压 tar 才用 ADD |
| 端口怎么开 | EXPOSE 只是声明，真正开放要 -p/-P 映射 |
| CMD vs ENTRYPOINT | CMD 可被替换；ENTRYPOINT 打不死、参数可追加 |
| 怎么构建 | docker build -t 名字:版本 .（点 = 当前目录，即构建上下文） |
| 怎么少几层 | 多条 RUN 用 && 合并；临时文件同层清理；基础镜像选小的 |
| 常驻容器怎么写 | CMD 里加 tail -F / 前台进程，别让主进程秒退 |

一句话总结：**Dockerfile 是"环境配方"——FROM 选地基、RUN/COPY 装环境、ENV/EXPOSE 定配置、CMD/ENTRYPOINT 定启动；docker build -t 一键烘焙，用 && 并 RUN 给镜像瘦身，从此环境进 Git、处处可复现。**

@@quiz
1. Dockerfile 的四个部分分别是什么？哪一部分必须在第一行？
2. RUN 和 CMD 的区别是什么？各在哪个阶段执行？
3. COPY 和 ADD 有什么区别？什么场景必须用 ADD？
4. EXPOSE 8080 之后端口就能被外部访问吗？怎样才能真正访问？
5. 只写 CMD 时，`docker run 镜像 自定义命令` 会发生什么？换成 ENTRYPOINT 呢？
6. `docker build -t tomcat:1.0 .` 里每个部分是什么意思？
7. 为什么要把多条 RUN 用 && 合并成一条？
@@links
参考|Docker技术应用与实战（76 页）|#
文档|Dockerfile 官方参考|https://docs.docker.com/engine/reference/builder/
文档|Dockerfile 最佳实践|https://docs.docker.com/develop/develop-images/dockerfile_best-practices/