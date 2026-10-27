@@h1 第二章　Elasticsearch
@@sub 阶段 6 · 企业级RAG系统架构与实现　|　理论实操　|　难度 ★★★

@@why 这一章在解决什么问题
上一章的向量数据库帮你解决了"语义相近"的检索。可现实中还有另一类需求它搞不定：**精确匹配**。搜"iPhone16 512GB"，你不想看到"iPhone15 128GB"；搜"188号车位"，就得精确到 188 号，不能是 189 号。

同时你的日志、帖子、新闻、商品库都是**非结构化文本**，用 MySQL 的 `LIKE '%关键词%'` 去搜：一慢（全表扫）、二笨（搜不到同义词）、三弱（不能打分排序）。百度、京东、淘宝的搜索框背后，都不是数据库 LIKE，而是一个叫**搜索引擎**的东西。

这一章的主角 Elasticsearch（ES）就是全世界用得最多的开源搜索引擎：学完你能装起一套 ES，把数据灌进去，用 REST API 完成"搜得快、搜得准、还带高亮"的全文检索，并用 Spring Data ES 在 Java 项目里调起来——这正是企业级 RAG 系统的第二块地基。

@@map 这一章在整个知识库里的位置
上一章：向量数据库——解决了"语义相似"检索
**本章** ← 你在这里：Elasticsearch——解决"精确/关键词"检索，全文检索的工业标准
下一章：RAG 基础理论——把"检索+生成"串成完整架构
再下一章：RAG 端到端演示——向量库 + ES + LLM 跑通全流程
阶段终点：你能独立搭出"检索增强生成"的完整链路

@@note info 这一章你要达到什么程度
16 个知识点。前半是"原理"（倒排索引、分词器、数据结构），中间是"操作"（Kibana、CRUD、DSL 查询），后半是"工程"（Spring Data ES、优化、集群）与一个百度式搜索综合案例。**原理必懂，操作必跑，工程必记。**

@@point ① 非结构化数据为什么难搜
@@need 要解决什么
你手里有 100 万篇新闻、10 万条商品描述、一整天的最新日志。想找"包含'养老保险'的文章"，用 MySQL？`LIKE '%养老保险%'` 会把每篇都扫一遍——**数据过千万就是灾难**。更惨的是你想搜"养老金"，它搜不到只能搜"养老保险"。

| 数据库 LIKE | 搜索引擎 |
|---|---|
| 逐行扫全表，慢 | 建好索引，快几个数量级 |
| 只能字面匹配 | 能分词、能同义、能打分 |
| 无法排序、高亮 | 相关度排序、命中高亮是基本功 |

这就是为什么每个大厂都自己造"搜索"。而 Elasticsearch 把这件事做成了**人人可用的开源产品**。

@@idea 核心思路
一句话：**搜索引擎 = 预先建好一种"读书目录"，查的时候只翻目录**。这个"目录"在 ES 里叫**倒排索引**，是它一切性能的灵魂。非结构化数据的检索，本质是把"我要找的词"和"哪些文档里有这个词"的关系提前算好存起来。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为"有了 ES 就能替掉 MySQL"** | ES 是搜索引擎，不是业务库：**没有事务、没有强一致、关联查询很弱**。标准做法是"**MySQL 存业务 + ES 做检索**，两边同步" |
| 以为 LIKE 慢是"MySQL 不行" | 是**数据结构不匹配**：B+ 树为"精确相等/有序范围"设计，天生不擅长"任意词匹配"。换成 Postgres、Oracle 一样慢 |
| 数据才几千条就急着上 ES | 数据少、并发低时 LIKE 完全够用。**搜索的价值随数据量和并发增长**——过早引入 ES 只是给自己加一套要运维的东西 |

@@point ② 倒排索引：全文检索的秘密武器
@@need 要解决什么
"正排索引"就是把文档当成目录页：我给你一个词，你得翻遍全文才能知道它在哪。你想在 100 万篇文档里找"养老金"，【每篇都读一遍才能确认有没有这个词】——这就是 LIKE 慢的原因。

@@idea 核心思路
倒排索引反过来建**词 → 文档**的映射，像字典的拼音索引：

```
文档1：养老保险需要缴纳满15年
文档2：养老金按月发放
文档3：今天天气不错

倒排索引（分词后）：
   养老    → 文档1
   保险    → 文档1
   缴纳    → 文档1
   满15年  → 文档1
   养老金  → 文档2
   发放    → 文档2
   天气    → 文档3
```

查"养老金"，直接定位到"养老金 → 文档2"，**不用扫全库**。每个词后面还挂着位置信息、出现次数，用来算相关度分数（谁出现得多、在哪出现，谁更靠前）。**这是 ES 比 LIKE 快几个数量级的根本原因。**

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为"建了索引就什么都能搜"** | 倒排索引建的是**分词之后的词**。搜"养老"能中，是因为"养老保险"先被切成了"养老/保险"。**分词器决定索引里有什么**——分词不对，索引再好也搜不到 |
| 以为倒排索引是"免费"的 | 查询快是拿**写入慢 + 占空间**换来的：每个词都要维护"词→文档"映射和位置信息。写入越频繁，这笔账越贵 |
| 以为"改一个字"只动一个词 | 更新文档在底层是**先作废旧的倒排项、再写入新的**。频繁更新会产生大量待合并的段，磁盘和 IO 都跟着涨 |

@@point ③ Elasticsearch：百度/淘宝搜索的中台组件
@@need 要解决什么
你知道了需要"倒排索引"，但**自己写一个**？分词、排序、高亮、分布式、容灾……没有十年积累做不出来。你要的是现成的、经过大厂验证的搜索引擎。

@@idea 核心思路
Elasticsearch 是开源搜索引擎 Lucene 之上的"分布式 + REST API 封装"：
- **Lucene**：底层真的搜索能力（倒排索引、分词、打分），Java 库
- **ES**：把 Lucene 包成"开箱即用的数据库"：HTTP API、高可用集群、自动分片、监控面板

一份数据写进 ES = **写入多个副本分片**（写 3 份，坏 2 台还能读）——这是它敢撑起"全站搜索"的底气。配套生态：Kibana（可视化面板）、Logstash（日志管道）、Beats（采集器），合称 **ELK**。

| 组件 | 干什么 |
|---|---|
| Elasticsearch | 存数据 + 提供搜索 API |
| Kibana | 网页控制台，可视化操作与监控 |
| Logstash / Beats | 把 MySQL、日志等数据源源不断灌进 ES |

@@point ④ ES 的数据模型：跟 MySQL 一一对应
@@need 要解决什么
新人第一次看 ES 的 PUT 请求一脸懵：`PUT /users/_doc/1`？这个 URL 到底在干什么？其实 ES 的数据模型和你熟悉的 MySQL 几乎一一对应，只是换了名字——**把它当"NoSQL 版 MySQL"记就行**。

@@idea 核心思路
| MySQL | Elasticsearch | 说明 |
|---|---|---|
| Database 数据库 | **Index 索引** | 一个业务一个 Index，如 `news`、`users` |
| Table 表 | **Type（7.x 前）/ 默认 _doc（7.x 后）** | 7.x 起一个 Index 默认一种类型，少操一份心 |
| Row 行 | **Document 文档** | 一条 JSON 记录 |
| Column 列 | **Field 字段** | JSON 里的每个键就是字段 |
| 主键 id | **_id** | 文档唯一标识 |

```bash
# 本质就是"往 users 索引里写一个 JSON 文档"
PUT /users/_doc/1
{
  "name": "张三",
  "age": 28,
  "intro": "精通 Java"
}
```

**记忆锚点**：Index 不是"索引"而是"数据库/表"的合体概念（一个 Index = 一张表 + 它的所有索引）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为 ES 的 "Index" 就是"索引"** | 术语撞车，最容易混淆的一处。ES 的 Index ≈ MySQL 的库/表；而"倒排索引"才是索引。**看到 Index 先想"这是一张表"** |
| 按 MySQL 习惯"一个库装所有表" | ES 里通常**一个业务一个 Index**。全塞一个 Index 会 mapping 冲突（同名字段类型打架）、分片也切不均匀 |
| 照着老教程写多 Type | 7.x 起一个 Index 只有一种类型（`_doc`）。老教程里的 `/{index}/{type}/{id}` 写法已经废弃 |

@@point ⑤ 安装 ES 8：别被"非 root 用户"坑到
@@need 要解决什么
装 ES 最常见的坑：直接 `./bin/elasticsearch` 启动，报错"can not run elasticsearch as root"；或者装完 `localhost:9200` 打开提示要密码。**ES 的部署规范跟普通服务很不一样。**

@@idea 核心思路
ES 8 的安装四步（Linux 服务器）：
```bash
# 1. 下载解压（官网 tar.gz），ES 不允许 root 启动
adduser elif       # 创建专用用户
chown -R elif /usr/local/elasticsearch
su elif

# 2. 修改配置
vim config/elasticsearch.yml
#   network.host: 0.0.0.0     # 允许远程访问
#   cluster.name: mycluster
vim config/jvm.options
#   -Xms4g -Xmx4g            # 内存不够会频繁 GC，见"优化"一节

# 3. 启动
./bin/elasticsearch -d        # 后台运行

# 4. 验证
curl http://localhost:9200    # 返回 JSON，带 cluster_name 即成功
```

**为什么必须非 root**：ES 的 JVM 沙箱安全机制要求不能以超级用户运行，这是硬约束不是 bug。ES 8 默认开启安全认证，首次启动会打印一个临时的 `elastic` 用户密码，**务必存好**，后面 Kibana 连接和所有请求都要用它。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| can not run elasticsearch as root | 创建普通用户 `su` 切换后再启动 |
| 内存不足 fatal error | 默认 `-Xms1g`，机器小就把 jvm.options 改成 `-Xms512m -Xmx512m` |
| 启动太慢 / 卡住 | 磁盘 IO 慢；先 `./bin/elasticsearch -d` 看 `/logs/elasticsearch.log` |
| 忘记初始密码 | `./bin/elasticsearch-setup-passwords auto` 重置 |

@@point ⑥ 索引操作：PUT 建 / GET 查 / DELETE 删
@@need 要解决什么
数据写进 ES 之前，得先有一个"表"。但 ES 里没有 `CREATE TABLE` 那种宣言式建表——它的建表是"一条 PUT 请求顺便定义结构"。你要学会这三板斧。

@@idea 核心思路
```bash
# 1. 建索引（显式指定结构，生产必用：让 ES 知道该给什么字段建倒排索引）
PUT /news
{
  "settings": { "number_of_shards": 3, "number_of_replicas": 1 },
  "mappings": {
    "properties": {
      "title":   { "type": "text",   "analyzer": "ik_max_word" },
      "content": { "type": "text",   "analyzer": "ik_max_word" },
      "author":  { "type": "keyword" },
      "date":    { "type": "date" },
      "views":   { "type": "integer" }
    }
  }
}

# 2. 查询索引信息
GET /news

# 3. 删除（慎重！数据全没）
DELETE /news

# 4. 查看所有索引
GET /_cat/indices?v
```

**为什么要显式指定 mappings**：不指定的话 ES 会自动猜类型（数字猜 long、字符串猜 text+keyword），自动猜测经常不满足业务（比如想用 keyword 精确排序却被打成 text），所以**生产环境：先 PUT 建表，再写数据**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为 mapping 建完还能随便改** | **大部分字段类型建完就改不了**，要改只能"建新索引 + reindex 迁数据"。所以"**先想清楚 mapping，再灌数据**" |
| 图省事不写 mappings，让 ES 自动猜 | 自动猜测经常不合业务（想精确排序的字段被打成 text）。**生产必须显式声明**，开发阶段图快可以先猜 |
| `DELETE /news` 当成"删数据" | 这是**连索引带 mapping 带数据整个删掉**。只删一条文档要用 `DELETE /news/_doc/{id}` |
| 以为设置分片数可以随时改 | `number_of_shards` **建索引时定死**，之后不能改（只能 reindex）。副本数倒是可以随时调——**这两个别搞混** |

@@point ⑦ 文档 CRUD：增删改查与"软删除"
@@need 要解决什么
数据结构定了，接下来是最基本的四件事：增、查、改、删。ES 的写法跟 SQL 很不一样（全 REST + JSON），而且有一个**颠覆直觉**的更新机制——不搞懂它，你会调一次改一次还查不到结果。

@@idea 核心思路
```bash
# 新增（PUT 指定 id / POST 自动生成 id）
POST /news/_doc
{ "title": "养老保险新规", "author": "佚名" }
PUT  /news/_doc/1001
{ "title": "养老金调整", "author": "李四" }

# 查询
GET /news/_doc/1001

# 更新（部分字段）
POST /news/_doc/1001/_update
{ "doc": { "author": "张三" } }

# 删除
DELETE /news/_doc/1001
```

**软删除机制（重要）**：ES 的更新/删除不是真的覆盖原文档，而是**标记旧版本、写入新版本**，查询时只返回最新版本。旧版本要等后台"段合并"才会物理清理。后果：
- **频繁更新会让磁盘暂时膨胀**（旧版本还在）
- **批量更新比逐条快**：用 `_bulk` 一次提交几百条

```bash
# 批量写入（一次网络请求传多条，生产必备）
POST /_bulk
{ "index": { "_index": "news", "_id": 1 } }
{ "title": "第一条" }
{ "index": { "_index": "news", "_id": 2 } }
{ "title": "第二条" }
```

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **写完立刻查，查不到** | ES 是**近实时（NRT）**：默认 1 秒 refresh 之后才可被搜到。写完马上搜不到是正常现象，不是没写进去（用 `GET /_doc/{id}` 能立刻读到） |
| **以为"更新"是原地改** | 底层是**标记旧版本 + 写新版本**。所以更新一点都不便宜，频繁更新会让磁盘短暂膨胀 |
| 逐条 `POST` 写几千条 | 每条一次网络往返，慢到不能用。生产必须用 `_bulk` 批量 |
| 删了大量数据，磁盘没变小 | 要等后台**段合并**才物理释放。这是正常的，别急着以为没删掉 |
| 以为 `_bulk` 会报错就整体回滚 | `_bulk` **不是事务**：部分成功、部分失败是常态，必须**逐条检查返回结果**里的 `errors` 字段 |

@@point ⑧ 字段类型与属性：mapping 里的决定性配置
@@need 要解决什么
同一个词，在 A 字段里能当精确值匹配、在 B 字段里要被分词模糊查——为什么？因为**字段类型决定了 ES 怎么对待它**。mapping 里写错一个 type，全表检索行为就变了。这是初学者最常踩的隐性坑。

@@idea 核心思路
| 类型 | 场景 | 检索行为 |
|---|---|---|
| `text` | 标题、正文（要分词的内容） | 分词后建倒排索引，支持"模糊"匹配，**不能精确排序/聚合** |
| `keyword` | 状态、分类、标签、ID（要精确查的内容） | 整体作为一个词，支持 `term` 精确匹配、排序、聚合 |
| `long` / `integer` | 数字 | 范围查询、排序 |
| `date` | 时间 | 时间范围查询、按时间排序 |
| `boolean` | 布尔 | 过滤 |
| `geo_point` | 经纬度 | 地理搜索 |

字段属性常用：
- `"index": false`：该字段不建索引（只存不搜，省空间）
- `"analyzer"`：指定分词器（见下一节）
- `"format"`：date 字段的格式说明

**典型错误**：把"状态"字段（如 is_deleted）设成 text，然后 `term` 查询查不到——因为被分词拆了。正确做法：状态用 `keyword`，正文用 `text`。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **拿 text 字段做排序或聚合，直接报错** | text 被分词后**没有完整值**，排不了序、聚不了合。要排序/聚合必须用 `keyword`（或加 `fields` 子字段） |
| 把 ID、状态、标签设成 text | 被分词拆开，`term` 精确查不到。**这类"要精确匹配"的一律 keyword** |
| 以为 `keyword` 和 `text` 只是"分词与否" | 它还决定**能否排序聚合、能否 term 查询、占多少空间**。选错一个，整个检索行为都变 |
| 靠 `fielddata: true` 硬给 text 排序 | 它把分词结果全加载进堆内存，**数据量大直接 OOM**。正确做法是加 keyword 子字段 |

@@point ⑨ 分词器：ES 为什么"读不懂"中文
@@need 要解决什么
把"养老保险缴费年限"存入 ES，用"养老"去搜，**搜不到**——为什么？因为 ES 默认的 standard 分词器把中文当成"每个汉字一个字"，和"养老"压根不是一个词。搜索引擎的性能依赖"分词"，分错了一切都错。

@@idea 核心思路
分词器（Analyzer）负责把一句话切成"词"，切法决定了索引长什么样：

| 分词器 | 效果 |
|---|---|
| `standard`（默认） | 英文按空格切词，**中文按单字切** → 搜"养老"匹配不上 |
| `ik_smart` | IK 中文分词器：按词典切词 → "养老保险/缴费/年限" |
| `ik_max_word` | IK 最细切分：切出所有可能组合 → "养老保险/保险/缴费/年限" |
| `pinyin` | 中文转拼音 → "yanglao" 也能搜"养老" |
| `whitespace` / `keyword` | 按空格 / 整体不切 |

**为什么搜索引擎默认切不了中文**：英文天然空格分词；中文没有空格，需要专门的词典和算法。"IK + 拼音"这套组合是中文搜索的标配，见下一节。

```bash
# 测试分词效果（调试神器，先看切得对不对再查）
GET /news/_analyze
{ "analyzer": "ik_max_word", "text": "养老保险缴费年限" }
# 输出 ["养老保险", "养老", "保险", "缴费", "年限"]
```

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为"ES 天生支持中文"** | 默认 `standard` 把中文**按单字切**，搜"养老"匹配不上"养老保险"。中文必须装 IK |
| **索引和查询用了不同分词器** | 建索引时用 A 切、查询时用 B 切，两边词对不上——**搜不到**。同一个字段，写入和查询必须用同一个 analyzer |
| 装了 IK 还是搜不到新词 | 专有名词、网络新词（"酱香拿铁"）不在 IK 词典里，会被切散。**要维护自定义词典** |
| 搜不到就反复改查询语句 | 排查搜索问题的**第一步永远是 `_analyze`**：先看这句话被切成了什么词，问题八成就在那儿 |

@@point ⑩ 中文搜索标配：IK 分词器 + 拼音分词器
@@need 要解决什么
光有 IK 还差口气：用户搜"yanglao"或"yL"时，IK 无能为力（它不认识拼音）；用户搜"养老险"，IK 切出来对不上"养老保险"。**搜索产品要容忍用户的"模糊输入"**——拼音首字母、错别字、简称。

@@idea 核心思路
装两个插件 + 配一个自定义分词器（这就是企业级中文搜索的标准答案）：
```bash
# 1. 下载与 ES 版本完全一致的插件包（8.10.4 配 8.10.4）
./bin/elasticsearch-plugin install file:///opt/elasticsearch-analysis-ik-8.10.4.zip
./bin/elasticsearch-plugin install file:///opt/elasticsearch-analysis-pinyin-8.10.4.zip

# 2. 重启 ES 使插件生效
./bin/elasticsearch -d
```

装上之后要**改造 mapping**：让索引使用 `ik_max_word` 分词、`pinyin` 辅助。IK 还支持自定义词典（`IKAnalyzer.cfg.xml` 里配置），把"爱坤""酱香拿铁"这种新词加进词典，搜索才不会被切散。

**测试一下装没装好**：
```bash
GET /news/_analyze
{ "analyzer": "pinyin", "text": "养老保险" }
# 输出 ["yanglao", "baoxian", "yl", "bx", "养老", "保险", ...]
```

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **插件版本和 ES 版本不一致** | 必须**完全一致**（8.10.4 配 8.10.4），差一个小版本 ES 就起不来。这是"装不上"最常见的原因 |
| **以为装了插件就自动生效** | 插件只是**提供了分词能力**。还要在 mapping 里**显式指定 `analyzer`**，否则字段还是走默认分词器 |
| 装完没重启 | 插件是启动时加载的，**必须重启 ES** |
| 把拼音配到所有字段上 | 拼音会产生大量短词（`yl`、`bx`），**索引膨胀、还可能引入噪声**。只给需要拼音检索的字段配 |

@@point ⑪ 自定义分析器：让一个字段同时"吃"中文和拼音
@@need 要解决什么
IK 和拼音各管一段还不够：用户可能输入"养老"，也可能输入"ylbx"。**一个字段要同时支持中文关键词、拼音全称、拼音首字母三种匹配**——这需要一个把多个分词器叠起来的"自定义分析器"。

@@idea 核心思路
```json
PUT /news
{
  "settings": {
    "analysis": {
      "analyzer": {
        "ik_pinyin_analyzer": {
          "type": "custom",
          "tokenizer": "ik_max_word",        // 先按中文词典切
          "filter": ["pinyin_filter"]        // 再给每个词补上拼音
        }
      },
      "filter": {
        "pinyin_filter": {
          "type": "pinyin",
          "keep_full_pinyin": true,          // 保留全拼 yanglao
          "keep_first_letter": true,         // 保留首字母 yl
          "keep_original": true              // 保留原文词 养老/保险
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": { "type": "text", "analyzer": "ik_pinyin_analyzer" }
    }
  }
}
```
效果：一个 `title` 字段里同时索引了"养老""保险""yanglao""yl"等词 → 用户输入任意一种都能命中。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 搜拼音搜不到 | 字段用了默认 standard 分析器，忘记配 pinyin filter |
| 拼音把语义搞混 | 关闭 `keep_first_letter` 或给短词单独处理（首字母二义性高） |
| 自定义分析器不改 mapping | 分析器要**在索引创建时**配好，改 mapping 需要重建索引 |
| 插件版本不匹配 | 插件版本必须与 ES 完全一致，否则启动报错 |

@@point ⑫ 搜索 DSL：query 的基本盘
@@need 要解决什么
一切就绪，终于要"搜"了。ES 的搜索不是 SQL 而是 **DSL（领域特定语言）**——一坨 JSON 表达查询。你不需要背全部，记住最常见的四类就够了：全文、精确、范围、组合。

@@idea 核心思路
```bash
# ① 全文检索（分词匹配，按相关度打分排序）
GET /news/_search
{ "query": { "match": { "title": "养老保险" } } }

# ② 精确匹配（keyword 字段，不分词，等值判断）
GET /news/_search
{ "query": { "term": { "status": "published" } } }

# ③ 范围查询
GET /news/_search
{ "query": { "range": { "views": { "gte": 1000, "lte": 10000 } } } }

# ④ 匹配短语（要求词序相邻："缴费年限"不拆散）
GET /news/_search
{ "query": { "match_phrase": { "title": "缴费年限" } } }
```

**选型口诀**：
| 想做什么 | 用 |
|---|---|
| 搜关键词，要打分排序 | `match` |
| 精确等值（状态、标签、ID） | `term` |
| 数值/时间区间 | `range` |
| 固定短语 | `match_phrase` |
| 多个条件组合 | `bool`（下一节） |

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **`term` 和 `match` 用反了** | 最容易犯的错。`term` 是**精确匹配、不分词**（配 keyword）；`match` 是**分词匹配**（配 text）。**拿 `term` 查 text 字段就是查不到**（值被拆成词了） |
| 以为 `match_phrase` 和 `match` 差不多 | `match_phrase` 要求**词序相邻**："缴费年限"不会被拆散匹配；`match` 只要词出现就行，顺序无所谓 |
| 拿 `match` 查 keyword 字段 | 能查到但语义不对（keyword 整体一个词）。**keyword 就该用 term** |
| 搜不到就怀疑数据没写进去 | 先 `_analyze` 看词怎么切的、再 `GET /_doc/{id}` 确认数据在——**别直接改查询** |

@@point ⑬ 复合检索：bool 与排序、分页、高亮
@@need 要解决什么
真实搜索从来没有单个条件：**"已发布 + 标题含'养老' + 浏览数>1000，按时间倒序，只要前 10 条，还要把命中词高亮标红"**——一整套需求用一个请求搞定。这就要 `bool` 查询 + 排序分页 + 高亮。

@@idea 核心思路
```bash
GET /news/_search
{
  "from": 0, "size": 10,                              // 分页
  "sort": [ { "date": "desc" } ],                     // 排序
  "highlight": { "fields": { "title": {} } },         // 高亮命中词
  "query": {
    "bool": {
      "must":     [ { "match": { "title": "养老" } } ], // 必须匹配（AND）
      "filter":   [ { "term": { "status": "published" } },
                    { "range": { "views": { "gte": 1000 } } } ], // 过滤，不参与打分
      "must_not": [ { "term": { "author": "佚名" } } ] // 排除
    }
  }
}
```
要点：
- `must` = AND；`should` = OR（至少有 1 个命中即可，可配 `minimum_should_match`）
- **`filter` 不参与相关度打分**：过滤条件多的时候一定要放 filter，能省大量计算
- `highlight` 返回 `_source` 的 `highlight.title`，前端拿 `</em>` 标签包住的命中词直接渲染标红

**工厂级小技巧**：分页别用大 `from`（1000 之后非常慢），用 `search_after` 游标；深度分页用 scroll。生产系统搜"第 5000 页"的场景，用 from/size 会拖垮集群。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **把过滤条件放进 `must`** | `must` 参与相关度打分，`filter` 不参与。状态、时间、范围这类**纯筛选条件放 filter**，省掉大量打分计算，还能被缓存 |
| 用大 `from` 做深度分页 | `from=10000` 时**每个分片都要取 10000 条再汇总**，分片越多越慢。要用 `search_after` |
| 以为 `should` 是"必须" | `should` 是 OR。而且**一旦有 `must`，`should` 的"至少命中一个"约束可能失效**（变成只影响打分）——语义要看 `minimum_should_match` |
| 以为 `must_not` 会影响打分 | `must_not` 只做排除、不参与打分，也不缓存。别拿它当过滤器用 |

@@point ⑭ SQL 自由查询：不写 DSL 也能搜
@@need 要解决什么
DSL 是 JSON，写多了眼花缭乱；团队里有人只会 SQL。**ES 提供了 SQL 翻译层**——用 SQL 语法写查询，ES 自动翻译成 DSL 执行。学习阶段用它入门，比硬啃 DSL 快得多。

@@idea 核心思路
```bash
# 用 SQL 查询（x-pack 自带，ES 8 默认开启）
POST /_sql
{
  "query": "SELECT title, views FROM news WHERE views > 1000 ORDER BY views DESC LIMIT 10"
}

# 结果和普通 SQL 一样，转成表格
POST /_sql?format=txt
```

进阶：`_sql/translate` 可以把 SQL 翻译成 DSL，**学 DSL 的反向利器**——写条 SQL，看它翻译成什么 JSON，DSL 自然就会了。

适用边界：SQL 查询是给"人查数据"用的；**业务系统高频查询建议用原生 DSL**（效率略高、功能更全，如高亮、聚合）。

@@point ⑮ Spring Data ES：Java 开发者的标准姿势
@@need 要解决什么
前面你都在用 curl 敲 REST。但真实 Java/Spring 项目里，没有人敲 curl——**代码里怎么优雅地操作 ES**？Spring Data Elasticsearch 给了你一门"模板 + 注解"的语法糖，跟 Spring Data JPA 一个味道。

@@idea 核心思路
三步走：定义实体 → 定义 Repository 接口 → 注入使用。

```java
// ① 实体类（对应一个 Index 的 Document）
@Document(indexName = "news")
@Data
public class News {
  @Id private String id;
  @Field(type = FieldType.Text, analyzer = "ik_pinyin_analyzer")
  private String title;
  @Field(type = FieldType.Keyword)
  private String status;
  @Field(type = FieldType.Integer)
  private Integer views;
}

// ② 数据访问层：接口命名即查询（和 JPA 的 findByXxx 一模一样）
public interface NewsRepository extends ElasticsearchRepository<News, String> {
  List<News> findByTitle(String title);              // 等值查询
  List<News> findByViewsGreaterThan(int views);      // 范围查询
  List<News> findByStatusOrderByViewsDesc(String status); // 组合+排序
}

// ③ 业务代码里直接用
@Service
public class NewsService {
  @Autowired private NewsRepository newsRepository;
  public List<News> search(String kw) { return newsRepository.findByTitle(kw); }
}
```

数据同步：MySQL 里的数据怎么进 ES？**logstash** 一条管道同步增量数据（`input{ jdbc } → filter → output{ elasticsearch }`），配合 `sql_last_value` 记录游标，实现"MySQL 改一条、ES 同步一条"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为 `findByTitle` 就是"全文检索"** | 方法名查询按**字段类型**决定行为：text 字段走分词匹配，keyword 字段就是**精确等值**。**别指望方法名能表达复杂检索** |
| 拿 Repository 方法名硬凑复杂查询 | 方法名适合 CRUD 和简单条件。**bool、高亮、聚合、多字段加权**这些要用 `NativeSearchQuery` |
| 以为改了 MySQL 数据 ES 就自动更新 | **不会**。要有同步链路（Logstash / 应用双写 / CDC），而且要想好**失败重试和一致性校验** |
| 实体类注解和索引 mapping 不一致 | 两边都写了一遍，容易漂移。**以哪边为准要定死**，上线前用 `GET /index/_mapping` 核对 |

@@point ⑯ 集群、优化与综合案例：百度式新闻搜索
@@need 要解决什么
学完语法只是"会抄作业"。两个问题决定你的系统能不能上线：**一台机器挂了怎么办**（集群）、**数据大起来为什么越来越慢**（优化），最后用"百度式新闻搜索"把全部能力串起来。

@@idea 核心思路
**集群三板斧**：
- 分片（shard）：一份数据切成多个分片分散在多台机器，横向扩容的物理基础
- 副本（replica）：每个分片都有副本，**主分片挂了副本顶上**，还能分摊读压力
- 三节点起步：`discovery.seed_hosts` 把三台机器拉进一个 cluster，`node.master` / `node.data` 分配角色

**优化自查清单**：
| 症状 | 优化动作 |
|---|---|
| 查询慢 | 分片数过大（每分片数据 <5G 反而慢）、改成过滤查询、加缓存 |
| 内存炸 | JVM 别超过物理内存一半（留一半给 OS 文件缓存），`indices.fielddata.cache` 限量 |
| 磁盘涨 | 定期 `DELETE` 过期索引、改冷热分层（热节点 SSD/冷节点 HDD） |
| 写入慢 | 批量 `_bulk`、调大 refresh_interval、关副本写入再开 |

**综合案例：百度式新闻搜索**（配套项目 escase 的核心链路）：
```text
采集(Logstash) → 新闻表(MySQL) → 同步进 ES(news 索引，ik_pinyin 分词)
        ↓
用户输入"养老" → ES 查询三连：
    ① title.match("养老")       主打语义命中
    ② 拼音字段 term("ylbx")     兼容拼音/首字母
    ③ completion 自动补全        输入"养老"就给下拉建议"养老保险/养老金发放"
        ↓
返回结果：相关度打分排序 + highlight 高亮 + 分页
```

这就是一个"百度式"搜索框的完整骨架：**采集、同步、分词、检索、补全、高亮**六件套齐活。

@@summary
这一章你拿到了企业级 RAG 的第二块地基，从零搭过一套能打的中文搜索引擎：
- 理解倒排索引原理——知道 ES 为什么比 LIKE 快几百倍
- 能写好 mappings（text/keyword 分清楚）和分析器（IK+拼音）
- 会用 DSL 完成 match/term/range/bool、排序分页高亮
- 会写 Spring Data ES 的 Repository 查询
- 懂集群与优化，能照着综合案例复刻一个搜索功能

到这里，"检索"的两大支柱（语义检索/关键词检索）都齐了。下一章把它们焊进 RAG 架构。

@@quiz
1. 倒排索引相对于正排（LIKE 扫描）的核心优势是？
   A. 存储更省　　B. 词 → 文档映射，免全表扫描　　C. 支持事务　　D. 数据结构更简单
2. 微博"状态"字段（published/draft）应该用什么类型？
   A. text　　B. keyword　　C. long　　D. date
3. 默认 standard 分词器搜中文"养老"搜不到"养老保险"的原因？
   A. ES 不支持中文　　B. 中文被拆成单字，没组合成词　　C. 需要装 License　　D. 数据没写入
4. 搜索"已发布 + 标题含养老 + 浏览>1000"，过滤条件应放哪？
   A. must（参与打分）　　B. filter（不参与打分，更快）　　C. must_not　　D. 任意处都行
5. ES 中 `term` 查询与 `match` 查询的本质区别？
   A. term 是精确匹配（keyword），match 是分词匹配（text）　　B. 两者一样　　C. term 更快但只支持英文　　D. match 不支持中文

@@links
参考|章节2_Elasticsearch.pdf|#
参考|es.rar（SpringBoot+ES Java 工程源码，选读）|#
软件|elasticsearch-8.10.4、kibana、logstash 安装包（章节2/软件/）|#
官网|Elastic 官网|https://www.elastic.co/cn
插件|IK 分词器仓库|https://github.com/medcl/elasticsearch-analysis-ik
插件|拼音分词器仓库|https://github.com/medcl/elasticsearch-analysis-pinyin
官网|Spring Data Elasticsearch 文档|https://docs.spring.io/spring-data/elasticsearch/reference/