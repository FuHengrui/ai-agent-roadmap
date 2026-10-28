@@h1 第十二章　AI 配图与 OSS 上传发布
@@sub 阶段 9 · 智能运营平台　|　实践　|　难度 ★★★★★

@@why 这一章在解决什么问题
文案完成了，但小红书笔记还差两口气：**图从哪来**、**发到哪去**。本章是平台的最后一公里，解决三件事：**用阿里百炼文生图给标题配图**（提示词工程 + 返回 URL 解析）、**把图片上传阿里云 OSS 变成可公网访问的稳定链接**、**以及发布体系**（发布记录管理 + 小红书自动化发布脚本」。

这也是项目里工程细节最多的一章：图片尺寸约束、异步转同步的重试、OSS SDK 新老版本坑、发布 Cookie 与无头浏览器——每一条都是真实踩过的坑。

@@prep 开始之前
要备好百炼 API Key、阿里云 OSS 的 AccessKey 和 Bucket，还要小红书发布 Cookie。

@@goal 学到这儿就够了
能把图从百炼转存到 OSS 拿到稳定链接、留下发布记录，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：文案创作与编辑——正文就绪，素材页完整
**本章** ← 你在这里：AI 配图与 OSS 上传发布——图文齐备、可发布可追溯
再往后：项目收尾——全链路验收、构建部署、安全排查

@@point ① 配图链路总览：标题 → 风格 → 生成 → 存储
@@need 要解决什么
一张配图从无到有要经过哪些环节？先画链路，再逐环拆解。

@@idea 核心思路
```
用户选标题+风格 → POST 生成请求
  → qwen_agent 拼提示词（标题 + 风格 fengge + 质量约束）
  → 调百炼 dashscope qwen-image 文生图 → 返回临时图片 URL
  → 下载图片 → 上传阿里云 OSS → 得到稳定 image_url
  → 写入 t_title_images（title_id + image_type 0/1/2）
```
两个存储边界：
- **百炼返回的 URL 是"临时/限时"的**——直接存它的 URL 会过期失效，所以必须"转存"；
- **OSS 的 URL 常驻可访问**——这才是入库的 image_url（500 长度的字段就是放它）。

⚠️ 前端轮询：文生图接口是异步（提交任务 → 轮询结果），后端要对百炼的异步结果做封装，前端只需一次请求。也给了"阻塞等待到底"的直连写法（可跑但慢，生产走异步轮询）。

@@point ② 提示词工程：把标题翻译成画面
@@need 要解决什么
"给 AI 一句话生成封面"和"生成小红书合格封面"之间差一个结构化提示词。qwen_agent 的核心是拼一个好的文生图提示词。

@@idea 核心思路
generate_cover_prompt 的逻辑：
```
f"{style 风格描述（来自 t_style.fengge）}"
+ 主体："主体是{title}（或主题词）"
+ 文字处理：include_text 分支——要求"画面中嵌入文案文字"（封面场景）
+ 质量约束："高清、构图完整、色彩协调、主体突出、符合小红书封面规范"
+ 负向提示词："低清、模糊、变形、多余文字、水印、杂乱背景"
```

提示词结构价值：**风格字段（fengge）来自数据库，可运营配置**——运营想换风格，改一行 t_style 数据即可，不用改代码。这就是第 2 章风格表设计的回报。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 生成的图有乱码文字 | 文生图对"嵌入文字"支持有限；封面需要文字时用 include_text 分支但校验内容尽量短 |
| 图片变形/主体残缺 | 负向提示词没写；及尺寸参数（宽高比）与版面要求不匹配 |
| 风格没生效 | 拼 prompt 时漏了 fengge 或 fengge 为空（种子数据缺失） |

@@point ③ 百炼文生图调用：dashscope 的同步姿势
@@need 要解决什么
项目里 qwen-image 怎么调、返回怎么解析——这是和 Coze 完全不同的另一家 AI SDK。

@@idea 核心思路
```python
import dashscope
dashscope.base_http_api_url = "...your endpoint..."   # 自定义网关（可空，默认官方）

resp = dashscope.MultiModalConversation.call(
    model="qwen-image-2.0-pro",
    messages=[{"role": "user", "content": [
        {"image": prompt},             # 纯文本提示词
    ]}],
    size="960*1696",                    # 竖版封面尺寸规格
    water_mark=False,
    prompt_extend=True,                 # 提示词扩展
    negative_prompt="低清,模糊,水印,变形,多余文字",
)
url = resp.output.choices[0].message.content[0].image   # 取生成的图片 URL
```
- `size="960*1696"`：小红书竖版封面常见比例（3:5 左右），**尺寸随用途定**（封面/正文/缩略图可不同）；
- **返回解析路径很深**：`output.choices[0].message.content[0].image`——多一层数组就多一个取错的机会；
- 超时/失败要重试：图片生成是重活，偶发失败属常态。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| KeyError: 'image' / NoneType | content 里可能带文字或图片数组顺序不同；解析前先打印 resp 结构再定位 |
| 报 ApiKey 鉴权失败 | QWEN_KEY 缺失或不是百炼密钥（别名 okhttp-apikey），检查 .env |
| 拿到的 URL 直接入库后过期打不开 | 必须"转存 OSS"（见下一点），别把临时 URL 当正式数据 |

@@point ④ OSS 上传：新 SDK alibabacloud_oss_v2
@@need 要解决什么
百炼返回临时 URL，需要下载并转存到 OSS。项目用的是**阿里云新版 Python SDK（alibabacloud-oss-v2）**——和网上大量老教程（oss2）API 完全不同，这是最容易"抄错作业"的地方。

@@idea 核心思路
```python
import oss2  # 兼容层/新SDK形态，旧版 SDK 用 v2 形态：
from alibabacloud_oss_v2 import config as oss_config
from alibabacloud_oss_v2 import credentials, oss

cfg = oss_config.load_default()                 # 从环境变量读取 OSS 配置
provider = credentials.StaticCredentialsProvider(
    access_key_id=OSS_ACCESS_KEY_ID,
    access_key_secret=OSS_ACCESS_KEY_SECRET)
client = oss.Client(cfg, provider)              # 构建客户端

oss_key = f"images/{原文件名}_{uuid4().hex[:8]}{ext}"
req = oss.PutObjectRequest(bucket=OSS_BUCKET, key=oss_key, body=图片字节)
result = client.put_object(req)                 # result.etag 校验成功
public_url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{oss_key}"
```
要点：
- **StaticCredentialsProvider**（静态密钥）vs 老版 oss2 的直接传参——API 形态完全不同；
- oss_key 加入 **uuid4 短缀防重名覆盖**（同标题二次生成不互相覆盖）；
- 存库的是拼好的 public_url（可公网访问），不是 object key。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| `AttributeError: module 'oss2' has no attribute ...` | 误装老版 oss2 却按 v2 调用；按 pyproject 的 alibabacloud-oss-v2 安依赖 |
| 上传成功但 URL 访问 403 | bucket 未设为公共读（public-read），或签名 URL 过期；开发期将 bucket 权限设 public-read |
| 中文文件名乱码/拒绝 | oss_key 用原文件名会带中文编码问题；统一重命名（原名_uuid.ext），避免中文 key |
| Content-Type 不对（图片变下载流） | 显式按扩展名映射：.jpg→image/jpeg、.png→image/png，别让 OSS 猜 |

@@point ⑤ 两种上传姿势：本地文件 vs URL 转存
@@need 要解决什么
upload.py 支持两类输入：本地已存在的图片文件、远程 URL（百炼生成结果）。两种姿势分别怎么传？

@@idea 核心思路
```python
# 姿势 A：本地文件 → put_object_from_file
with open(本地路径, "rb") as fp:
    req = PutObjectRequest(bucket, key, fp)
    client.put_object(req)

# 姿势 B：URL 下载 → 内存 → put_object
resp = requests.get(百炼临时URL, timeout=30)
if resp.status_code == 200:
    body = io.BytesIO(resp.content)
    req = PutObjectRequest(bucket, key, body)
    client.put_object(req)
```
统一封装：`upload_image(来源, 目标key) -> public_url`，业务层只需传"图片在哪"，不用关心 A/B 差异。**下载要设超时并校验状态码**，失败归为重试而非静默跳过。

@@point ⑥ 发布体系：记录先行，脚本跟进
@@need 要解决什么
平台真正的交付是"能发出去"。先做**发布记录管理**（t_publish_records），并提供**小红书自动发布脚本**（puppeteer）作为发布执行器。

@@idea 核心思路
发布记录 API（records 相关）：创建发布任务（platform/publish_status=0 待发布）→ 推进状态 0→1→2/3 → 数据表现回填（view/like/comment/share_count）。状态机与第 2 章定义一致：
```
0待发布 → 1发布中 → 2发布成功（终态）
                  ↘ 3发布失败（可重试回 1）
2/3 → 4已删除（软删）
```

小红书发布脚本（scripts/publish-xiaohongshu.mjs）：
- 用 **puppeteer 启动无头浏览器**打开 creator.xiaohongshu.com（创作者平台）；
- 注入账号 Cookie（前端 xiaohongshu.js 里 localStorage 配置了多账号 Cookie）；
- 填标题、正文、传图、点发布。

⚠️ 边界要讲清：**"自动发布"依赖账号 Cookie 有效与平台页面结构**——Cookie 过期必须人工重新获取；页面改版脚本就失效。所以发布脚本是"执行器辅助"，真实发布动作当前仍建议人工确认（定位为能力演示）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 发布脚本报"请登录" | Cookie 过期；需重新从浏览器登录态导出 Cookie 更新到 localStorage 配置 |
| 无头浏览器打不开/闪退 | puppeteer 的 Chromium 没装好；重跑安装或指定本机 Chrome 路径 |
| 发布状态卡在"发布中" | 脚本失败未回写状态；发布动作要有超时与失败回写（status→3）兜底 |

@@point ⑦ 安全红线：密钥与 Cookie 的终检
@@need 要解决什么
项目收尾时要跑一遍"凭据排查"——源码与文档里出现过的真实密钥，绝不能以明文出现在任何交付物里。

@@idea 核心思路
检查清单（本项目必备，对照自查）：
1. **QWEN_KEY**（百炼，sk- 开头）→ 交付物里写 `QWEN_KEY=sk-你的百炼ApiKey`
2. **COZE_TOKEN**（扣子个人令牌，pat_ 开头）→ `COZE_TOKEN=pat_你的扣子令牌`
3. **OSS AccessKey**（LTAI 开头 ID + 32 位 Secret）→ `OSS_ACCESS_KEY_ID=你的AccessKeyId` / `OSS_ACCESS_KEY_SECRET=你的AccessKeySecret`
4. **签名 URL**（含 OSSAccessKeyId/Signature 的完整链接）→ 一律脱敏
5. **小红书 Cookie** → 只写"存放位置与获取方式"，不写真实值

做法：写完后用正则扫一遍交付目录（sk-、pat_、LTAI、Signature=），发现即替换为占位符并复查上下文（占位符本身别写成真实值样式）。

@@point ⑧ 全链路大验收：从"输入主题"到"记录在案"
@@need 要解决什么
十二证合一的终局验收：用一条真实任务把整平台的每一环走到底。

@@idea 核心思路
验收剧本（对照前面所有章节）：
1. 注册/登录 → 拿 token（第 6 章）；
2. 创作页输入"新能源汽车" → /start → 50 标题落库（第 10 章）；
3. 素材页选一条 → /copy 生成 220-420 字文案 → 保存/重置（第 11 章）；
4. 选风格 → 文生图 → 转存 OSS → t_title_images 出现（本章）；
5. 创建发布 → 状态推进 → 数据回填（本章）；
6. 侧边栏/历史列表数据与库一致（第 2/10 章）；
7. 刷新页面仍就绪（cookie 持久化，第 7 章）；
8. 全仓库扫密钥：零真实凭据（本章）。

任一环失败回到对应章节定位；全部通过 = 阶段 9「智能运营平台」实战完成。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 全链路验收时某步"卡住"但单测都过 | 全链路是"联调问题"高发区：跨站代理、Cookie、时区、字符集任一环错都难查；按"前端→代理→后端→AI→存储"逐段打断点 |
| 验收只测"成功路径" | 至少要过一遍异常路径（错密码登录、超时重试、OSS 密钥错、发布失败回写），平台才敢交给运营用 |

@@summary 这一章你学到了什么
- 配图链路：标题+风格 → 拼提示词 → 百炼文生图 → 转存 OSS → 落库
- 提示词工程：风格（数据驱动）+ 主体 + 文字分支 + 质量约束 + 负向提示词
- 百炼调用：MultiModalConversation、size 960*1696、深度解析 output.choices[0].message.content[0].image
- OSS v2 SDK：load_default + StaticCredentialsProvider + oss.Client；与老版 oss2 API 完全不同
- oss_key 规则：原名_uuid8 + 扩展名；中文文件名/Content-Type 显式处理；bucket public-read 才可访问
- 双上传姿势：本地文件 put_object_from_file / URL 下载内存 put_object，统一 upload_image 封装
- 发布体系：records 状态机 0→1→2/3→4 + puppeteer 小红书自动发布（Cookie 过期/页面改版会失效）
- 收尾终检：QWEN/COZE/OSS 密钥与签名 URL 全占位符化，正则扫库零残留

@@quiz
1. 百炼返回的图片 URL 为什么不直接入库？
   A. 太长　　B. 临时/限时，会过期；必须转存 OSS　　C. 格式不对　　D. 收费
2. 配图提示词里的"风格"来自哪里？
   A. 硬编码　　B. 数据库 t_style 的 fengge 字段（可运营配置）　　C. 用户每次手写　　D. 模型默认
3. 封面图推荐尺寸是？
   A. 960*1696（竖版）　　B. 1920*1080　　C. 1:1 方形　　D. 任何尺寸
4. upload.py 用的 OSS SDK 形态是？
   A. 老版 oss2　　B. alibabacloud_oss_v2（load_default + StaticCredentialsProvider）　　C. boto3　　D. 官方 CLI
5. oss_key 加 uuid4 短缀的目的是？
   A. 加密　　B. 防重名覆盖　　C. 排序　　D. 统计
6. OSS 图片 URL 访问 403 的常见原因是？
   A. 网络　　B. bucket 未设置 public-read 权限　　C. 图片太大　　D. 文件名中文
7. 收尾密钥排查应该扫哪些模式？
   A. sk- / pat_ / LTAI / Signature=　　B. 只扫 password　　C. 不需要扫　　D. 只扫 token

@@links
参考|智能运营平台.pdf|#
官方|阿里云百炼文生图 API|https://help.aliyun.com/zh/dashscope/
官方|OSS Python SDK (v2)|https://help.aliyun.com/zh/oss/developer-reference/
官方|Puppeteer 文档|https://pptr.dev/