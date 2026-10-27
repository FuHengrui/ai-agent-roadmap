@@h1 第十六章　Docker 镜像与容器基本操作
@@sub 阶段 18 · 云原生开发环境与 DevOps 工具链　|　容器化　|　难度 ★★★★

@@why 这一章在解决什么问题
上一章只讲了思想，这一章动手：**把 Docker 装上、拉个镜像、把容器跑起来。**
你现在缺的是三件事：① 机器上还没有 Docker（要装）；② 没有镜像（要搜要拉）；③ 不会管理容器（要练）。
这一章 14 个知识点全部围绕一条主线：**镜像从哪来 → 容器怎么跑 → 跑起来后怎么管、怎么查、怎么删**。
跟练完，你就能亲手用 Docker 跑起一个 JDK 和一个 Tomcat，并在浏览器里访问到网页——"我能用 Docker 了"的第一个里程碑。

@@map 这一章在整个知识库里的位置
**上一章**：Docker 概述与容器化思想——镜像/容器/仓库三概念
**本章** ← 你在这里：安装引擎 + 镜像三操作（查/拉/删）+ 容器全生命周期
**下一章**：容器数据卷——容器删了数据不能丢
**阶段终点**：会装会用，数据、镜像定制、网络、发布逐级解锁

@@point ① 镜像从哪来：pull 拉取 or build 构建
@@need 要解决什么
要跑容器必须先有镜像。镜像不是天上掉下来的，也不建议从零组装——绝大多数场景都有现成的。先搞清楚"镜像从哪来"，后面才不迷路。

@@idea 核心思路
镜像只有两个来源：
1. **从仓库拉取**（最常见）：`docker pull 镜像名:标签`。比如 `docker pull openjdk:11`，一个命令拿到官方做好的 JDK 11 环境；
2. **自己用 Dockerfile 构建**（第 18 章）：现有镜像满足不了需求时，基于它写配方，构建出独属于自己的镜像。

这里出现第一个关键概念 **tag（标签）**：`openjdk:11` 里的 `11` 就是标签，代表镜像的版本。
**不写 tag 时默认拉 `latest`（最新版）**——图省事的默认值，但生产环境建议显式指定版本，否则环境不可控。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 不写 tag 拉镜像，过段时间环境"悄悄变了" | 拉的是 latest，随官方更新内容会变；生产环境必须写死版本号如 openjdk:11 |
| 以为镜像必须自己从头做 | 90% 的场景仓库里有现成的，先 search 后 pull，别徒手造轮子 |

@@point ② 安装 Docker 引擎：环境准备 + yum 三步半
@@need 要解决什么
镜像要拉、容器要跑，前提是机器上得有 Docker。在 CentOS 上装 Docker 不是一条命令的事，还得先给"地基"腾地方。

@@idea 核心思路
准备工作（CentOS 7.x，内核 3.8 以上）：
1. **关防火墙**：容器要开端口，防火墙会拦；
2. **关 SELinux**：这个安全模块经常导致容器起不来，学习阶段先关；
3. **yum 安装** Docker 引擎；
4. **启动 + 设开机自启**；
5. **跑 hello-world 验证**。

```cmd
# 1. 关闭防火墙并禁止开机自启
systemctl stop firewalld
systemctl disable firewalld

# 2. 关 SELinux：编辑 /etc/selinux/config，把 SELINUX=enforcing 改成 disabled
#    （改完需重启才完全生效，学习阶段先跳过重启）

# 3. 用 yum 安装 Docker 引擎（-y 表示全程自动确认）
yum install -y docker

# 4. 启动 Docker 服务 + 设为开机自启
systemctl start docker
systemctl enable docker

# 5. 验证：能输出 Hello from Docker! 就说明引擎装好了
docker run hello-world
```

`docker run hello-world` 是全世界第一个 Docker 命令：本地没有 hello-world 镜像，它会自动从仓库拉一个最小的，跑完即退——用来验证"引擎 + 网络 + 仓库"三通。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| docker run hello-world 卡住不动 | 国内访问 Docker Hub 慢：给 Docker 配置**镜像加速器**（形如 `https://xxxx.mirror.aliyuncs.com`，xxxx 换成你自己账号下的专属地址） |
| 容器起得来但不通外网 | 多半是防火墙或 SELinux 没关，回到第 1、2 步 |
| 重启机器后 docker 服务没了 | 少了 `systemctl enable docker`，补上即可 |

@@point ③ docker images：查看本地镜像
@@need 要解决什么
Docker 装好了，但你不知道机器上"有哪些镜像、什么版本、多大"。查看本地镜像，这是第一件事。

@@idea 核心思路
```cmd
# 列出本地所有镜像
docker images
```

输出五列：

| 列 | 含义 |
|---|---|
| REPOSITORY | 镜像来自哪个仓库（如 openjdk） |
| TAG | 标签/版本（如 11） |
| IMAGE ID | 镜像的唯一 ID |
| CREATED | 创建时间 |
| SIZE | 镜像大小 |

**IMAGE ID 是镜像的唯一身份证**：哪怕名字相同，ID 也不同；按 ID 操作永远比按名字更精确。
（现代 Docker 显示的是短 ID，前面一段就足够唯一标识了。）

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| docker images 列表为空 | 正常——你还没 pull 过任何镜像，先 `docker pull` 一个 |
| 想区分同名镜像的版本 | 看 TAG 列：openjdk:11 和 openjdk:17 是两个独立的镜像版本 |

@@point ④ 镜像三操作：search 搜索 / pull 拉取 / rmi 删除
@@need 要解决什么
不知道仓库里有什么 → 搜；看中了 → 拉；本地太多不用了 → 删。三个命令覆盖镜像的完整生命周期。

@@idea 核心思路
```cmd
# 1. 搜索远程仓库里有哪些相关镜像（默认搜 Docker Hub）
docker search openjdk

#    结果里看这几列：名字、描述、星级（越大越受欢迎）、
#    OFFICIAL（是否官方出品）、AUTOMATED（是否自动构建）

# 2. 拉取到本地（不写 tag 默认 latest）
docker pull openjdk:11

# 3. 删除本地镜像：可按"仓库名:标签"删，也可按镜像 ID 删
docker rmi openjdk:11
docker rmi <IMAGE ID>
```

经验：**优先选星多、带 OFFICIAL 的官方镜像**，第三方镜像里的环境可能藏雷（版本怪、带不明插件）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| rmi 报"image is being used by container" | 有容器正用着这个镜像，先停/删对应容器再删镜像；`-f` 强删不推荐 |
| 按 TAG 删不掉，镜像还在 | 同一镜像可能打了多个 tag；用 IMAGE ID 删能一次清掉 |
| search 结果一大堆不知道选谁 | 看 OFFICIAL 列 + 星级排序，优先官方 |

@@point ⑤ docker run：一行命令走完"拉→建→启→连→跑"
@@need 要解决什么
镜像有了，怎么变成跑着的容器？先理解 `docker run` 背后到底替你干了什么——这是理解容器的一把钥匙。

@@idea 核心思路
严格讲，容器创建分两步：`docker create`（建一个停止的容器）+ `docker start`（启动它）。
而 `docker run` 是两步合一（镜像不存在还会自动先 pull）。它完整走一遍：

```
docker run 镜像
  1. 检查本地有没有这个镜像，没有 → 去仓库下载
  2. 用镜像创建一个容器
  3. 在只读镜像层上叠一层可读写层（容器因此能写文件）
  4. 从宿主机网桥（docker0）给容器接一个虚拟网口
  5. 从地址池给容器分配一个 IP
  6. 执行你指定的命令；命令执行完，容器就退出
```

最简用法：

```cmd
# 前台跑一个一次性任务：输出 hello world 后退出
docker run 镜像名 /bin/echo "hello world"
```

**关键认知：容器是"执行完命令就退出"的**——没有常驻进程就活不下来。想让它常驻，见第 ⑦、⑧ 点。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| run 一个 bash 容器，瞬间就退出了 | 容器里没有保持运行的前台进程；需要 `-it` 挂个交互终端进去（下一点） |
| 以为 run 只是"启动已有容器" | run 是"创建+启动"合一；单纯启动已有容器是 `docker start` |

@@point ⑥ -it 交互模式：进到容器里敲命令
@@need 要解决什么
很多 Linux 镜像拉下来是为了进去敲命令的（装软件、看文件）。但容器"命令跑完就退出"，怎么才能"住"进去不退出？

@@idea 核心思路
两个参数缺一不可：
- `-i`：保持容器的标准输入打开（不然你敲不进东西）；
- `-t`：为容器分配一个伪终端（pseudo-tty），让你有个像样的命令行界面。

```cmd
# 创建一个 centos 容器，并以 bash 交互式进入
docker run -t -i centos /bin/bash
# 进去后会看到 root@容器ID:/# 这样的提示符，可以随意敲命令了
```

#### 退出容器有两种方式，别搞混
- `exit`：退出并**停止容器**（容器里主进程 bash 结束了）；
- `Ctrl + p` 再 `Ctrl + q`（也写作 Ctrl+p+q）：退出终端但**容器保持运行**——适合你暂时走开、容器里的进程还要继续跑的场景。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只写 -t 不写 -i，进去后敲命令没反应 | -t 只给终端不给输入通道；两个参数要一起（现在也可写作 -it） |
| 担心 exit 后容器就废了 | 容器只是停了，`docker start 容器ID` 能再拉起来，可读写层数据还在 |

@@point ⑦ -d 守护模式：让容器在后台安静地跑
@@need 要解决什么
交互终端只适合"进去干活"。真实场景是：容器应该像服务一样**在后台一直跑**，你不挂着终端它也不死。

@@idea 核心思路
加 `-d`（daemon，守护进程）参数，容器就在后台运行，命令执行完立刻回到你的终端，容器继续活着。

```cmd
# 后台跑一个"每秒打印一行"的容器（sh -c 里写个小循环）
docker run -d 镜像名 /bin/sh -c "while true; do echo hello world; sleep 1; done"

# 返回的是容器的唯一 ID——珍贵！后面管理全靠它
# （不用背全，记住前几位 + 用 docker ps 查全量）
```

后台容器看不见输出，怎么确认它活着？看 `docker ps`，或者用 `docker logs` 拉它的日志（下一点）。
**坑点预告**：`-d` 只负责放后台，容器有没有"活着的进程"才是生死线——你的命令一跑完，容器照样退出。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| docker run -d 后容器几秒变 Exited | 启动命令执行完就结束了（没有常驻前台进程）；换成能一直运行的命令（web 服务器、上面的 while 循环） |
| 只记住了容器名字没记住 ID | 容器 ID 不用记——`docker ps` 随时能查；也可以启动时用 `--name` 起名（下一点） |

@@point ⑧ --name 命名 与 -p 端口映射：把容器"露"给宿主机
@@need 要解决什么
后台容器跑起来了，外面有两个问题：① 一堆容器怎么好认？② 容器里的服务（Tomcat 的 8080）在容器"内部"的 IP 上——宿主机的浏览器怎么访问得到？

@@idea 核心思路
```cmd
# --name 给容器起名字，管理时再也不用看那串乱码 ID
# -p 端口映射：把"宿主机端口:容器内端口"打通
docker run -d --name mytomcat -p 9090:8080 docker.io/tomee
```

端口映射原理：

```
  你的浏览器               宿主机(9090)              容器 mytomcat
──────────►   localhost:9090  │  docker 引擎转发  │  容器内 8080
                              └──────────────────►  Tomcat
```

- `-p 宿主机端口:容器内端口`：精确指定。访问 `宿主机IP:9090` 就等价于访问容器里的 8080；
- `-P`（大写）：**自动随机映射**容器暴露的所有端口，不用手动指定（适合玩票，映射到哪得查 `docker ps` 的 PORTS 列）；
- 实践约定：**外部用非标准端口（如 9090）映射容器内标准端口（8080）**，避免和宿主机已有服务撞车。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 映射了 -p 9090:8080，访问 localhost:9090 打不开 | 检查：容器是否在跑（docker ps）、防火墙是否放行 9090、"容器内端口"是否填的是应用真实监听端口 |
| -p 写反成 8080:9090 | 格式是"**宿主机:容器内**"，写反会转发到一个没有服务的端口，自然打不开 |
| 报端口被占用 | 宿主机端口已被别的进程占用，换一个宿主机端口 |

@@point ⑨ docker ps：查看容器状态
@@need 要解决什么
容器都跑起来了，怎么知道"现在有几个在跑、状态如何、端口映射到哪"？——查户口。

@@idea 核心思路
```cmd
# 只列出运行中的容器
docker ps

# 列出所有容器（含已停止的）——加 -a
docker ps -a

# 只要容器 ID 列表（配合批量操作用）
docker ps -aq
```

`docker ps` 输出的关键列：CONTAINER ID、IMAGE（用的什么镜像）、COMMAND（启动命令）、STATUS（Up/Exited）、PORTS（端口映射）、NAMES（名字）。
`docker ps -aq` 常和"一键清理"连用：`docker stop $(docker ps -aq)` 再 `docker rm $(docker ps -aq)`，一条不留。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 刚 run 的容器在 docker ps 里看不到 | 它已经 Exited（退出）了，要加 -a 才显示；原因八成是启动命令跑完就结束了 |
| 忘了端口映射到哪 | 看 docker ps 的 PORTS 列，格式 `0.0.0.0:9090->8080/tcp`，箭头左边是宿主机端口 |

@@point ⑩ 进入运行中的容器：docker exec（和 attach 的恩怨）
@@need 要解决什么
用 `-d` 把容器放后台之后，你想再"钻"进去看看情况、改个配置。问题来了：容器已经在跑，怎么进？

@@idea 核心思路
Docker 提供两条路，现在主流用 `exec`：

```cmd
# 1. exec（Docker 1.3+ 提供）：在运行中的容器里执行命令，最常用
docker exec -it 容器ID /bin/bash
#    进去后开一个新的 bash 交互终端，从这敲命令
#    在容器里做的一切不影响容器原有的主进程

# 2. attach：直接"贴"到容器的主进程上
docker attach 容器ID
```

**为什么推荐 exec 而不是 attach**：
- attach 是多窗口"同步直播"——两个窗口 attach 同一个容器，你敲的命令在别的窗口也看得到；
- 一个窗口被命令卡住时，其他窗口也跟着卡（因为挂在同一个主进程上）；
- exec 则是"另开一个新终端"，互不影响，进出自由。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| exec 进去后敲 exit，容器停了 | 不会——exec 的 bash 是额外开的，exit 只退出这个终端，容器主进程照常跑；attach 里 exit 则可能干掉容器 |
| 容器里没有 bash（极简镜像） | 用 `docker exec -it 容器ID /bin/sh` 换 sh 试试 |

@@point ⑪ 生命周期管理：stop / start / restart / rm
@@need 要解决什么
容器会经历"跑着 → 停 → 再启 → 删"几个状态，新手最容易在这些命令上绕晕。把生命周期捋直。

@@idea 核心思路
```
         docker create（只建不启）
                │
                ▼
  ┌── docker start（启动）◄────────────┐
  ▼                                   ▼
 运行中 ── docker stop（停止）──► 已停止 ── docker restart（重启=停+启）
  │                                   │
  └──────── docker rm（删除）◄─────────┘
```

```cmd
docker stop 容器ID      # 停止（优雅，先给信号再停）
docker start 容器ID     # 启动已停止的容器
docker restart 容器ID   # 重启：stop 再 start，一步到位

# 删除容器（注意是 rm 不是 rmi——rm 删容器，rmi 删镜像）
docker rm 容器ID
docker rm -f 容器ID     # -f 强制删除运行中的容器
```

还有两个贴心的历史参数：`-l` 只删容器间的连接，`-V` 连它挂载的数据卷一起删（第 17 章会用到）。
**口诀：镜像用 rmi 删，容器用 rm 删，stop 只是"熄火"不是"报废"。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| docker rm 删不掉运行中的容器 | 先 stop 再 rm，或直接用 `docker rm -f` 强删（会先杀进程） |
| 把 docker rm 打成 docker rmi | 一字之差：rm 管容器，rmi 管镜像；从报错信息里的 image/container 关键词可判断敲错哪个 |
| stop 后以为容器没了 | stop 只是停止，容器实体还在（docker ps -a 能看到），不想要就补一个 rm |

@@point ⑫ 排查三件套：logs 日志 / top 进程 / cp 拷文件
@@need 要解决什么
容器"起不来"或"起来了但有毛病"时，你得有"看内脏"的手段——日志、进程、文件，三件套齐活。

@@idea 核心思路
```cmd
# 1. 日志：容器里输出过的所有内容（启动失败的报错也在这）
docker logs 容器ID
#    常用参数：
#    -f          实时跟踪（像 tail -f）
#    --tail 50   只看最后 50 行
#    -t          每条带时间戳
#    --since 42m 只看最近 42 分钟的

# 2. 进程：容器里现在跑着哪些进程
docker top 容器ID

# 3. 拷贝：容器文件带出来（或带进去），主机与容器互通
docker cp 容器ID:容器内路径 宿主机路径    # 容器 → 主机
docker cp 宿主机路径 容器ID:容器内路径    # 主机 → 容器
```

**排错铁律：容器启动失败，第一个动作永远是 `docker logs`**——它说了算，别瞎猜。比如 Tomcat 起不来，logs 里会直接告诉你 "Port already in use" 或配置文件哪行写错。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| docker logs 什么都打不出来 | 应用把日志写进文件了，没往标准输出写；改应用配置把日志输出到 stdout |
| docker cp 拷出来是空目录 | 路径写错：容器内路径必须用绝对路径，且"容器ID:路径"中间用冒号 |

@@point ⑬ 实战一：用 Docker 跑 JDK
@@need 要解决什么
光说不练假把式。用前面所有知识，30 秒跑起一个 JDK 11 环境并验证——第一次"从 0 到 1 用上 Docker"。

@@idea 核心思路
```cmd
# 1. 在仓库里找 openjdk 镜像
docker search openjdk

# 2. 拉指定版本 11（不写 tag 可能拉到 17/21，注意版本）
docker pull openjdk:11

# 3. 直接跑镜像，执行 java -version，验证环境
docker run openjdk:11 java -version
#    输出类似：
#    openjdk version "11.0.x"
#    OpenJDK Runtime Environment ...
```

看到版本号，说明：**拉取成功 + 容器创建成功 + JDK 环境可用**——你的 Java 世界从此多了一种"不用装 JDK 也能跑 Java"的姿势。
想进去敲 javac 之类，加 `-it` 进 bash：`docker run -it openjdk:11 /bin/bash`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| search 找不到 openjdk:11 | search 是模糊搜名字，不看 tag；先用 `docker search openjdk` 看有哪镜像，再用 pull 指定 tag |
| 官方 openjdk 镜像很精简，缺工具报错 | 只验证 java -version 就够了；缺编译工具是正常现象，别在精简镜像里硬装 |

@@point ⑭ 实战二：用 Docker 跑 Tomcat 并浏览器访问
@@need 要解决什么
JDK 只是"跑了个命令"。Tomcat 更接近真实：它是一个 Web 服务器，能在浏览器里访问到页面，才算"Docker 落地"。

@@idea 核心思路
```cmd
# 1. 搜索 + 拉取（docker.io/tomee 是官方 Tomcat 的一个实现）
docker search docker.io/tomee
docker pull docker.io/tomee

# 2. 后台运行，起名 mytomcat，把宿主 9090 映射到容器内 8080
docker run -d --name mytomcat -p 9090:8080 docker.io/tomee

# 3. 查看容器状态和端口映射
docker ps

# 4. 验证：浏览器打开 http://localhost:9090
#    看到 Tomcat 页面 = 成功；打不开先 docker logs mytomcat
```

到这一步你已经体验了完整的 Docker 工作流：**search → pull → run(-d --name -p) → ps → logs**。
以后管任何中间件（MySQL、Nginx、Redis）都是这套套路，只是换镜像名和端口。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 浏览器访问 localhost:9090 白屏/拒绝连接 | ① 容器没在跑（docker ps 看 STATUS）；② 端口映射写错；③ 在云服务器上还要看安全组是否放行 9090 |
| 另一台机器访问不到 | 用宿主机 IP 而非 localhost；且确保防火墙/安全组开放了对应端口 |

@@summary 本章小结
| 问题 | 答案 |
|---|---|
| 镜像从哪来 | docker pull 从仓库拉，或后续用 Dockerfile 构建 |
| 怎么装 Docker | 关防火墙/SELinux → yum install docker → start+enable → hello-world 验证 |
| 怎么查/删镜像 | docker images（IMAGE ID 唯一）；docker rmi 名前:tag 或 ID |
| 怎么跑容器 | docker run（=create+start，可自动 pull），-it 进交互、-d 进后台 |
| 怎么对外访问 | -p 宿主机端口:容器内端口；-P 随机映射 |
| 怎么查容器 | docker ps（-a 全看，-q 只要 ID） |
| 怎么进运行中的容器 | docker exec -it（推荐）vs attach（同步直播，易卡） |
| 容器生命周期 | create/start/stop/restart/rm；镜像 rmi、容器 rm |
| 起不来怎么办 | 先 docker logs，再 top/cp 对症下药 |

一句话总结：**镜像操作三连（search→pull→rmi）、容器一生（run/ps/exec/stop/restart/rm）加排查三件套（logs/top/cp），JDK 与 Tomcat 两手实战跑通——Docker 日常操作你就出师了。**

@@quiz
1. 不写 tag 直接 docker pull 会拉到什么版本？生产环境为什么建议写死 tag？
2. docker run 一条命令背后做了哪几件事？容器为什么"命令执行完就退出"？
3. -it、-d、-p 9090:8080、--name 四个参数各是干什么的？
4. exit 和 Ctrl+p+q 退出容器的区别是什么？
5. docker rm 和 docker rmi 有什么区别？各自负责什么对象？
6. 容器启动失败了，你第一步应该做什么？为什么？
@@links
参考|Docker技术应用与实战（76 页）|#
文档|Docker 官方文档|https://docs.docker.com/
文档|docker run 参考|https://docs.docker.com/engine/reference/run/