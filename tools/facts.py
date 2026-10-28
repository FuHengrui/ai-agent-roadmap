# -*- coding: utf-8 -*-
"""「错过的那些事实」——一个来源，两处使用。

为什么单独放一个文件：
  这次自查里，同一类错反复出现在两章以上（`MEMORY_ONLY` 会溢写磁盘、`sortBy` 多分区局部有序、
  `_2` 是两份副本……），说明错误是从一章抄到另一章的。
  把「正确答案」和「曾经的错误写法」一起记下来，才能：① 生成给人看的清单；② 让检查器盯住复发。

用法：
  python tools/check_facts.py           # 扫全库，命中「错误写法」就报
  python tools/check_facts.py --doc     # 重新生成 docs/事实清单.md
  python tools/check_facts.py --check   # CI 用：有命中就退出码 1
"""

FACTS = [
    {
        "id": "rdd-memory-only",
        "fact": "RDD 的 MEMORY_ONLY 内存不够时怎么办",
        "right": "丢掉装不下的分区，下次用到时按血缘重算；只有 MEMORY_AND_DISK 才落盘。RDD 的「弹性」主要靠血缘重算。",
        "wrong": "说 MEMORY_ONLY 内存不足会自动溢写磁盘",
        "chapters": "阶段 13 RDD 章、缓存章、SparkSQL 章",
        "bad": [r"MEMORY_ONLY[^。\n]{0,20}溢出", r"内存不够[^。\n]{0,10}溢写到磁盘"],
    },
    {
        "id": "spark-sortby",
        "fact": "sortBy / sortByKey 在多分区下是否全局有序",
        "right": "用 RangePartitioner，分区之间按区间有序，所以多分区结果本身是全局有序的；代价是要全量排序。写单文件才需要 coalesce 到 1 个分区。",
        "wrong": "说多分区只是「分区内局部有序、跨分区不确定」",
        "chapters": "阶段 13 行动算子章、SparkSQL 章、RDD 实战章",
        "bad": [r"多分区[^。\n]{0,12}局部有序", r"sortBy[^。\n]{0,24}交叉分区[^。\n]{0,6}不确定"],
    },
    {
        "id": "spark-union",
        "fact": "union 去不去重、是什么依赖",
        "right": "union 不去重（并集），只是分区拼接：N 个父分区拼成 N 个，子分区与父分区一一对应，仍是窄依赖。",
        "wrong": "说 union 会去重；或说它「一个子分区依赖多个父分区」",
        "chapters": "阶段 13 转换算子章、内核章",
        "bad": [r"union[^。\n]{0,8}并集[^。\n]{0,6}（?不重", r"union[^。\n]{0,10}一对多"],
    },
    {
        "id": "spark-broadcast",
        "fact": "闭包里的变量会不会被自动广播",
        "right": "不会。autoBroadcastJoinThreshold 只对 join 的小表生效；闭包变量要显式 sc.broadcast。",
        "wrong": "说「≤10MB 的闭包变量 Spark 会自动广播」",
        "chapters": "阶段 13 并行度与广播变量章",
        "bad": [r"自动广播闭包", r"10MB 以下[^。\n]{0,8}自动"],
    },
    {
        "id": "spark-replica",
        "fact": "StorageLevel 里的 _2 是什么意思",
        "right": "每个分区存两份、落在两个节点上（共 2 份），不是「在原有基础上再加 2 份」。",
        "wrong": "把 _2 解释成「再加 2 份副本」",
        "chapters": "阶段 13 缓存与 Checkpoint 章",
        "bad": [r"[+＋]2 份副本"],
    },
    {
        "id": "spark-nulls",
        "fact": "Spark 排序时 null 排在哪",
        "right": "ASC 时 null 在前、DESC 时 null 在后（所以 desc_nulls_last 就是默认）。要让 DESC 时 null 仍在前，用 desc_nulls_first。",
        "wrong": "说 orderBy 默认 null 排最后、desc 时反而在最前",
        "chapters": "阶段 13 DSL 与 SQL 章、阶段实战章",
        "bad": [r"null 排最后（desc", r"desc 时 null 在前"],
    },
    {
        "id": "sklearn-sgdregressor",
        "fact": "SGDRegressor 是什么算法、learning_rate 默认值",
        "right": "随机梯度下降（可 partial_fit 增量训练）；learning_rate 默认是 'invscaling'（η=η0/t^power_t），adaptive 要显式指定。",
        "wrong": "说它是 BGD/Mini-Batch；或说默认是 adaptive",
        "chapters": "阶段 20 梯度下降实战章、衍生回归章",
        "bad": [r"SGDRegressor[^。\n]{0,20}默认是\s*`?adaptive", r"本质[^。\n]{0,6}BGD/Mini-Batch"],
    },
    {
        "id": "scaler-normal",
        "fact": "StandardScaler 会不会让数据变正态",
        "right": "不会。它只是减均值、除以标准差，线性变换不改变分布形状；要正态得另做 log / Box-Cox。",
        "wrong": "把「变正态」当成标准化的收益",
        "chapters": "阶段 20 归一化与正则化章",
        # 注意：这句话经常以「它不会把数据变成正态」的否定形式出现，正则容易误判，
        # 所以不机器匹配，靠人读。
        "bad": [],
    },
    {
        "id": "pandas-fillna-method",
        "fact": "pandas 里 fillna(method=...) 还能用吗",
        "right": "不能。2.1 起弃用、3.0 已移除，改用 df.ffill() / df.bfill()。",
        "wrong": "示例里写 fillna(method='ffill')",
        "chapters": "阶段 17 缺失值章",
        "bad": [r"fillna\(\s*method\s*="],
    },
    {
        "id": "chroma-distance",
        "fact": "Chroma 返回的分数是相似度还是距离",
        "right": "是距离，越小越相似；阈值判断要用 <=，或先换成 1-score 再比。",
        "wrong": "把分数当相似度、用 >= 过滤",
        "chapters": "阶段 11 向量化与向量库章",
        "bad": [r"if d\[1\] >= settings\.RAG_SCORE_THRESHOLD"],
    },
    {
        "id": "hermes-memory",
        "fact": "hermes memory 有没有 list / delete 子命令",
        "right": "没有。memory 工具只有 add / replace / remove（靠 old_text 定位）；条目就是 Markdown 文本，直接读改 memories 目录，或用 hermes journey 看时间线。",
        "wrong": "写 hermes memory list / hermes memory delete <id>",
        "chapters": "阶段 15 记忆章、定时任务章",
        "bad": [r"hermes memory (list|delete)"],
    },
    {
        "id": "jwt-signed",
        "fact": "JWT 是加密还是只签名",
        "right": "只签名、不加密，payload 是明文 base64；能做的只有「验签」+「解出 payload」。",
        "wrong": "写「解密验签」",
        "chapters": "阶段 11 用户认证章、阶段 9 JWT 章",
        "bad": [r"解密验签"],
    },
    {
        "id": "docker-rm-v",
        "fact": "docker rm -v 会不会删掉具名卷",
        "right": "只清匿名卷；具名卷要单独 docker volume rm。",
        "wrong": "说 rm -v 会连挂载的数据卷一起删",
        "chapters": "阶段 18 镜像与容器章、数据卷章",
        "bad": [r"rm -v[^。\n]{0,14}数据卷一起删", r"-V 连它挂载的数据卷"],
    },
    {
        "id": "docker-layer",
        "fact": "Dockerfile 是不是每条指令都加一层",
        "right": "只有 RUN / COPY / ADD 才加文件系统层；ENV、CMD、EXPOSE 只改镜像配置（BuildKit 下不占层）。",
        "wrong": "说「每一条指令都生成一个独立镜像层」",
        "chapters": "阶段 18 镜像仓库与架构章",
        "bad": [r"每一条指令都生成"],
    },
    {
        "id": "kmedoids",
        "fact": "KMedoids 的中心是什么",
        "right": "medoid——簇内真实样本点（让簇内距离和最小的那个样本），不是中位数。",
        "wrong": "说 KMedoids 用「中位数」当中心",
        "chapters": "阶段 20 聚类章、KMeans 变体章",
        "bad": [r"均值→中位数", r"KMedoids[^。\n]{0,10}中位数"],
    },
    {
        "id": "torch-to",
        "fact": "nn.Module.to() 是原地还是新建",
        "right": "Module.to() 原地改并返回 self；只有张量的 .to() 返回新张量、要接收返回值。",
        "wrong": "说 model.to(device) 返回新对象、必须重新赋值",
        "chapters": "阶段 21 nnModule 章",
        "bad": [r"\.to\(\)[^。\n]{0,8}返回新对象"],
    },
    {
        "id": "nn-linear-batch",
        "fact": "nn.Linear 是否必须带 batch 维",
        "right": "惯例是 (N, in)；一维 (in,) 也能算，输出 (out,)。只有后面接 BatchNorm 这类层才必须补 batch 维。",
        "wrong": "说 nn.Linear 要求输入必须自带 batch 维",
        "chapters": "阶段 21 nnModule 章",
        "bad": [r"nn\.Linear 要求输入自带 batch"],
    },
    {
        "id": "codex-auto",
        "fact": "Codex 面板上的 Auto 是最严还是最常用放行档",
        "right": "Auto 对应 workspace-write，是**最常用的放行档**；最保守的是 Read Only。审批策略另有三档。",
        "wrong": "把 Auto 当成最严格的一档",
        "chapters": "阶段 16 Codex 权限章",
        "bad": [r"Auto（自动层）[^。\n]{0,12}高危"],
    },
    {
        "id": "cursor-rules",
        "fact": "Cursor 规则优先级与规则类型",
        "right": "优先级 Team > Project > User（Team 在 Dashboard 配）；没有 Notebook / System 这两级。",
        "wrong": "写 User > Project > Notebook > System",
        "chapters": "阶段 16 Cursor Rules 章",
        "bad": [r"User > Project > Notebook", r"Notebook Rules（笔记本规则）"],
    },
    {
        "id": "uvicorn-import",
        "fact": "main.py 里调 uvicorn.run 要先 import",
        "right": "需要显式 import uvicorn，否则运行即 NameError。",
        "wrong": "调了 uvicorn.run 但块里没有 import",
        "chapters": "阶段 9/10 应用启动章",
        "bad": [],
    },
]