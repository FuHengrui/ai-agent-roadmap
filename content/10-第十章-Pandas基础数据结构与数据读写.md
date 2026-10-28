@@h1 第十章　Pandas 基础：数据结构与数据读写
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据分析　|　难度 ★★☆

@@why 这一章在解决什么问题
**前面学的都是"一个个数"，而真实业务数据是一张张表：Excel、CSV、数据库表。** 读进来、改一改、再写出去——这就是 Pandas 的看家本领，也是"数据分析"三个字里"数据"二字的地基。这里的关键是搞懂 Pandas 的两个核心数据结构：**Series（一列带索引的数据）** 和 **DataFrame（多列构成的表）**。

这一章把两步走完：**先认识 Series/DataFrame 怎么创建，再打通读写（Excel/CSV/MySQL）**。学完你能回答：Series 和 ndarray 的关系、DataFrame 怎么从字典/文件/数据库来、读 Excel 和 CSV 的差异点、DataFrame 怎么存回文件和数据库。

@@prep 开始之前
上一章的 NumPy 会用就能开始，Pandas 随 Anaconda 已有；读 Excel 要 openpyxl。

@@goal 学到这儿就够了
能建 Series 和 DataFrame，能用 read_excel、read_csv 读进来并保存，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：NumPy 计算进阶——数值计算的底座
**本章** ← 你在这里：Pandas 开篇——Series/DataFrame 两大结构 + Excel/CSV/MySQL 读写，数据科学的核心工具正式登场
**下一章**：数据探查、列操作与索引——拿到表后"看"与"改"
**再往后**：缺失值筛选分组 → 合并时间序列 → 统计可视化；MySQL 章节会用它的数据库读写能力
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"链路，Pandas 就是这条链的中枢

@@note info 学习提示
本章是 Pandas 全流程入口：**"读"（Excel/CSV/DB）→ 认识结构（Series/DataFrame）→ "写"（文件/DB）**。结构化记忆：先背两个数据结构的三件事（是什么/怎么建/怎么访问），再背三种读法和两种写法的函数名。pymysql 连接数据库一段**密码必须填你自己的**，文中的教学占位串只是示例。

@@point ① Pandas 是什么：数据分析的主干工具
@@need 要解决什么
NumPy 管数组，**但真实数据是"带列名的表"**——NumPy 缺标签、缺缺失值处理、缺数据库对接。谁能补上？Pandas。

@@idea 核心思路
Pandas 是基于 NumPy 构建的**数据分析核心库**，两大数据结构：

- **Series**：一维带标签数组（像"带索引的一列"）；
- **DataFrame**：二维表结构（多列 Series 拼成），是数据分析的主角。

```python
import pandas as pd   # 官方推荐别名，全社区统一

pd.__version__        # 确认安装
```

三个"它是谁"的定位：**读取各类数据是它的入口，清洗转换是它的主战场，是数据分析标准组件（后面可视化和入库都接它）**。安装：

```bash
pip install pandas
# 或 conda install pandas
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| import pandas 报错 | 确认当前环境装了 pandas；conda/pip 二选一即可 |
| 把 pandas 和 numpy 混着记 | numpy 管 n 维数值数组，pandas 管带标签的表格数据（Series/DataFrame） |

@@point ② Series：从列表创建
@@need 要解决什么
**一列数据 + 一列标签**，最基础的结构从哪来？

@@idea 核心思路

```python
import pandas as pd

s = pd.Series([1, 2, 3, 4])
print(s)
# 0    1
# 1    2
# 2    3
# 3    4
# dtype: int64
```

- 左边一列自动生成的 **0,1,2,3 是索引（index）**；
- 右边一行是**数值（values）**；
- `s[0]` 按位置取值、`s.values` 拿纯数据（内部是 numpy 数组）。

Series 与 numpy 的关系：**values 就是 ndarray**，运算规则（广播、ufunc）全部继承。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Series 就是一维数组 | 它比数组多一套"索引标签"；这才是它"带标签"的意义 |
| s[0] 在索引非默认时失效 | 索引自定义后 s[0] 是"标签0"而不再一定是最前面位置；用位置取见 loc/iloc（第 12 章） |

@@point ③ Series 的 values / index 与自定义索引
@@need 要解决什么
**自动索引不好记，能不能给数据贴上"名字"？**

@@idea 核心思路

```python
import pandas as pd

s = pd.Series([88, 95, 76],
              index=['语文', '数学', '英语'])
print(s['数学'])        # 95：按标签取值
print(s.values)         # [88 95 76]：值数组
print(s.index)          # Index(['语文', '数学', '英语'])
```

要点：

- **index 是 Series 的灵魂**：标签化后，业务含义（科目、名字、日期）直接挂在数据边上；
- `s.index` 返回 Index 对象（可迭代、可改：`s.index = [...]` 直接换标签）；
- **s['数学'] 按标签取，s.values 取原始值**——两者别混。

标签和位置的正确使用：标签意义明确用 s['数学']；不确定标签就用位置索引（iloc）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| s['数学'] 报 KeyError | 标签拼写/顺序不同；先 s.index 看真实标签 |
| 换索引忘了同步长度 | index 列表长度必须与 values 相同，否则报错 |

@@point ④ Series 从字典创建：标签即键，缺键成 NaN
@@need 要解决什么
手头正好是 {标签: 值} 的字典结构，**想直接转成 Series**；且想按指定顺序只挑几项——缺的怎么办？缺的变 NaN。

@@idea 核心思路

```python
import pandas as pd

d = {'语文': 88, '数学': 95, '英语': 76}
s = pd.Series(d)
print(s)
# 语文    88  ← 字典键自动成为索引标签
# 数学    95
# 英语    76

s2 = pd.Series(d, index=['数学', '物理'])   # 只取指定标签
print(s2)
# 数学    95.0     ← 数值变浮点（为容纳 NaN）
# 物理    NaN     ← 缺失值 NaN
```

NaN 的由来：**指定 index 中没有对应键时，填充 NaN**（Not a Number）。NaN≠0，它表示"没有数据"，后续章节有专门处理。

ddd=int 值一遇到 NaN 会自动升级为 float——记这个规律，后面类型转换会见到同样现象。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用字典创建后索引顺序"乱" | 从字典创建按字典序排；想要指定顺序就传 index 参数 |
| 出现 NaN 后数值全变 float | 正常，NaN 是浮点；要整型需先填充再转 astype |

@@point ⑤ Series 从标量创建：一个值广播全体
@@need 要解决什么
**"全部填同一个值"**（初始化/默认值）——传标量给 Series，自动广播到每个索引上。

@@idea 核心思路

```python
import pandas as pd

s = pd.Series(100, index=['a', 'b', 'c'])
# a    100
# b    100
# c    100
```

- 标量 + index → **按 index 数量重复填充**；
- 不传 index 只传标量 → 长度为 1 的 Series。

用途：掩盖初学者"拿循环造默认列"的坏习惯——一列数据要想全同值，一行 Series 搞定。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 不传 index 时只有 1 个元素 | 就是要 index 才广播；没有 index 默认长度 1 |
| 以为传列表和传标量一样 | 列表→逐项填入，标量→广播；两者结果长度不同，分辨清楚 |

@@point ⑥ DataFrame：从字典创建
@@need 要解决什么
**一张表怎么建出来？** 最直觉的入口：字典 {列名: 列表}。

@@idea 核心思路

```python
import pandas as pd

df = pd.DataFrame({
    '姓名': ['张', '王', '李'],
    '成绩': [88, 95, 76],
    '及格': [True, True, True]
})
print(df)
#   姓名  成绩    及格
# 0  张   88   True
# 1  王   95   True
# 2  李   76   True
```

认知同步：

- **字典的键 → 列名**，**值列表 → 各列数据**；
- 行索引默认 0,1,2…，可传 index 自定义；
- **各列长度必须一致**，否则报错（除了可以补 NaN 的场景）。

访问入门：`df['姓名']` 取一列（得 Series）；`df[['姓名','成绩']]` 取多列（得 DataFrame）——**单列表选择是 DataFrame 的第一高频操作**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 建 DataFrame 报 lengths 不一致 | 各列列表长度必须相同；缺的用 NaN 填充对齐（见第 12 章） |
| df['姓名'] 和 df.姓名 都行吗 | 两者大多等价，但列名含空格/中文时不推荐点语法；统一用方括号最稳 |

@@point ⑦ Excel 文件读写：read_excel / to_excel
@@need 要解决什么
**业务数据最大来源之一就是 Excel**——读进来（read_excel）、算完存回去（to_excel）。

@@idea 核心思路

```python
import pandas as pd

# 读取
df = pd.read_excel('data.xlsx')                 # 默认第一个 sheet
df = pd.read_excel('data.xlsx', sheet_name='2月')  # 指定 sheet
df = pd.read_excel('data.xlsx', header=None)    # 无表头时

# 写出
df.to_excel('out.xlsx', index=False)            # 不写索引列
df.to_excel('out.xlsx', sheet_name='结果', index=False)
```

三个高频参数：**sheet_name 选工作表、header=None 处理无表头文件、index=False 写文件别带索引列**（index 列通常没用还占位）。

依赖：read_excel 需要 openpyxl（Excel）引擎，未装会报 ImportError——`pip install openpyxl`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| read_excel 报"Missing optional dependency" | 缺 openpyxl：pip install openpyxl 后重试 |
| 写出的 Excel 首列多了 0,1,2… | to_excel 默认写索引；加 index=False |

@@point ⑧ CSV / TXT 读取
@@need 要解决什么
**CSV 是最通用的数据交换格式**（几乎没有软件不支持）——Pandas 读 CSV/TXT 一脉相承。

@@idea 核心思路

```python
import pandas as pd

df = pd.read_csv('data.csv')              # 万能默认
df = pd.read_csv('data.csv', encoding='utf-8')      # 编码显式指定
df = pd.read_csv('data.txt', sep='\t')              # TXT 按制表符分隔
df = pd.read_csv('data.txt', sep=None, engine='python')  # 自动探测分隔符

# 写出
df.to_csv('out.csv', index=False, encoding='utf-8-sig')
```

要点：

- **sep 指定分隔符**：默认逗号；TAB 分隔 txt 用 sep='\t'；
- **encoding 常摔跟头**：国内文件常是 gbk/utf-8，读出来乱码就先换 encoding 再试（utf-8/gbk/gb18030）；
- **utf-8-sig 写出**：带 BOM，Excel 打开不乱码（utf-8 无 BOM 在 Excel 里中文可能乱）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 读 CSV 中文乱码 | 文件可能 GBK：换 encoding='gbk'/'gb18030' |
| 写出的 CSV Excel 打开就乱码 | to_csv 用 encoding='utf-8-sig'（带 BOM 兼容 Excel） |
| txt 读出来一大坨 | 分隔符不对：传 sep='\t' 或其他实际分隔符 |

@@point ⑨ MySQL 数据库读写
@@need 要解决什么
**数据在数据库里**（第 16-21 章的主角）——Pandas 用 SQL 把表拉成 DataFrame 处理，算完再写回。

@@idea 核心思路
先装驱动，再建立连接：

```bash
pip install pymysql
```

```python
import pandas as pd
import pymysql

conn = pymysql.connect(
    host='localhost',          # 数据库地址
    port=3306,                 # MySQL 默认端口
    user='root',               # 用户名
    passwd='你的密码',          # 密码：替换成你自己的数据库密码
    db='mydb',                 # 库名
    charset='utf8'             # 字符集（中文数据必备！）
)

df = pd.read_sql('SELECT * FROM student', conn)   # SQL 查询进 DataFrame
df.to_sql('student_copy', conn, index=False, if_exists='replace')  # 写回新表
```

三个注意点：

- **连接参数里的密码是教学占位**，必须换成你自己的真实密码，且**不要把真实密码写进任何文件**（存环境变量最安全）；
- **charset='utf8' 必带**，否则中文乱码；
- **用完关连接**：`conn.close()`（或 with 语句自动关）。

详细概念（MySQL 安装、用户、权限）在第 16-21 章展开，这里先会用 Pandas 接库即可。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 连不上 / Access denied | 用户名密码错误或权限不足：核对账号、密码、host 权限 |
| 中文读出乱码 | 连接串漏了 charset='utf8' |
| 提示"Can't connect" | MySQL 服务没启动或端口不对：`net start mysql` 先起服务 |

@@point ⑩ 保存 DataFrame：三路出口总览
@@need 要解决什么
算完的结果**往哪存？** 三条常规出口（Excel/CSV/数据库）对照记忆。

@@idea 核心思路

```python
df.to_excel('结果.xlsx', index=False)                          # Excel
df.to_csv('结果.csv', index=False, encoding='utf-8-sig')        # CSV
df.to_sql('结果表', conn, index=False, if_exists='replace')     # 数据库
```

统一习惯：**任何 to_xxx 都默认写索引，业务文件一律 index=False**；CSV 出国配 utf-8-sig；to_sql 反复写同表用 if_exists='replace'。

数据科学通用流程闭环：

```text
读（read_excel/read_csv/read_sql）→ 分析（Pandas 操作）→ 写（to_excel/to_csv/to_sql）
```

每一项都是独立的，本阶段后的清洗、分组、可视化全在这个闭环里。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| to_sql 写不进 / 表已存在报错 | if_exists='fail'（默认）时表存在就报错；用 replace 覆盖或 append 追加 |
| 忘记写路径目录存在 | 输出目录不存在会报错；先建目录 |

@@summary
这一章，Pandas 的"入口与出口"全打通：

| 拿到什么 | 记住什么 |
|---|---|
| **Series**：一列数据 + 索引标签 | 列表/字典/标量三种创建；index 是灵魂 |
| **DataFrame**：多列组成的表 | 字典 {列名: 列表} 创建；df['列'] 取列 |
| **Excel 读写** | read_excel/to_excel；sheet_name、index=False |
| **CSV/TXT 读写** | read_csv/to_csv；sep、encoding（utf-8-sig 防乱码） |
| **MySQL 读写** | pymysql + read_sql/to_sql；charset='utf8'、密码别写文件里 |
| **保存三出口** | to_excel / to_csv / to_sql 一行一个 |

一句话记住本章：**Series 是一列带标签的数据，DataFrame 是表；read_xxx 进、to_xxx 出，Excel/CSV/MySQL 三路都通——Pandas 的大门从此敞开。**

@@quiz
1. Series 和 ndarray 的关系是什么？Series 相比 ndarray 多出来的是什么？
2. 用字典创建 Series 时，字典的键会变成什么？指定 index 缺键时会出现什么？
3. Series 传标量创建的结果是什么？与传列表有何不同？
4. 从 {列名: 列表} 字典创建 DataFrame，键和值分别对应什么？
5. read_excel 读取非第一个 sheet 要传哪个参数？缺 openpyxl 时报什么错？
6. 读 CSV 中文乱码应怎么排查？写出给 Excel 用的 CSV 应该用什么编码？
7. Pandas 连 MySQL 需要安装什么库？连接参数里哪两个最容易坑？（一个字符集、一个保密）
@@links
参考|Pandas （145 页）|#
工具|Pandas 官网|https://pandas.pydata.org/
文档|Pandas IO 工具一览|https://pandas.pydata.org/docs/user_guide/io.html