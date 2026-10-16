@@h1 第五章　应用启动与患者管理 API
@@sub 阶段 10 · 安康智慧健康管理平台（糖尿病AI健康助手）　|　2 课时　|　难度 ★★★

@@why 这一章在解决什么问题
第四章写好了 7 个模型类，但代码还跑不起来——FastAPI 应用入口没建、路由没挂、数据库生命周期没注册。本章解决三件事：**一是从 main.py 把整个应用组装起来**（CORS、路由注册、Tortoise 生命周期、lifespan），**二是写第一个完整的 CRUD 模块（患者管理）**，**三是吃透 Pydantic v2 的 Schema 三件套**（Create/Update/Response）和 `from_attributes` 配置。

关键认知：**Schema 是 API 的"出入关口"**——请求体校验、响应序列化、计算属性导出全靠它。模型管"怎么存"，Schema 管"怎么对外"，两者分离才安全。

@@map 这一章在整个知识库里的位置
上一章：数据模型层——7 张表有了 Python 化身
**本章** ← 你在这里：应用启动 + 首个 CRUD——main.py 组装全局，患者 API 打通全链路
下一章：血糖管理——带统计分析的第二个 CRUD
再往后：饮食/用药/运动 → AI 引擎 → RAG → LangGraph
阶段终点：应用能启动、能连库、能增删改查

@@point ① main.py：应用的组装现场
@@need 要解决什么
FastAPI 应用不是"一个文件"，而是"一堆部件的组合"——入口文件负责把它们拧到一起。

@@idea 核心思路
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import main_router
from app.database import register_db
from app.core.knowledge_base import init_knowledge_base
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化医学知识库"""
    init_knowledge_base()   # 启动时把20条医学知识写入 ChromaDB
    yield

app = FastAPI(lifespan=lifespan)

# CORS：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(main_router)   # 挂载全部 API 路由（前缀 /api）
register_db(app)                  # 注册 Tortoise ORM 生命周期

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

组装时序很重要：**先建 app → 加中间件 → 挂路由 → 注册数据库**。lifespan 负责"启动前初始化"——医学知识库在服务一启动就灌进向量库，后续 RAG 检索才能命中。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 启动时报 "lifespan" 相关错误 | asynccontextmanager 装饰器必须搭配 `yield` 使用，yield 前是启动逻辑、yield 后是关闭逻辑 |
| CORS 没配导致前端请求被浏览器拦截 | 前端 5173 → 后端 8000 是跨域；allow_origins=["*"] 放行 |
| 路由 404 | 忘记 include_router(main_router) 或子路由没挂进 main_router |

@@point ② main_router：七个模块的路由聚合
@@need 要解决什么
患者、血糖、饮食、用药、运动、报告、对话七个模块各自有 router，入口文件怎么只挂一个？

@@idea 核心思路
`app/routers/__init__.py` 干这件事——**建一个主路由，把七个子路由全部收编**：

```python
from fastapi import APIRouter
from app.routers import (patient, blood_sugar, diet_record,
                         medication, exercise, health_report, chat)

main_router = APIRouter(prefix="/api", tags=["main"])
main_router.include_router(patient.router)
main_router.include_router(blood_sugar.router)
main_router.include_router(diet_record.router)
main_router.include_router(medication.router)
main_router.include_router(exercise.router)
main_router.include_router(health_report.router)
main_router.include_router(chat.router)
```

关键点：
- `prefix="/api"`：整棵路由树统一前缀，最终 URL 形如 `/api/patients/`、`/api/blood-sugar/`；
- 每个子路由在自己的文件里定义了 `prefix`（如 `"/patients"`），聚合后再叠一层 `/api`；
- **新增模块时这里必须同步 include**，否则前端调 `/api/xxx` 全是 404。

URL 拼接规律：`/api`（main 前缀）+ `/patients`（子路由前缀）+ `/路径`（装饰器路径）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 新增了模块但请求 404 | 忘了在 routes/__init__.py 里 include_router，或在 main.py 里 include |
| 路径多了一层/少了一层 | 前缀是叠加的：/api + /patients + /{id}，写前端请求时按这个拼 |

@@point ③ Pydantic Schema 三件套：Create / Update / Response
@@need 要解决什么
同一个患者，**创建**时必填 name/age，**更新**时全部可空，**返回**时多出 id 和计算属性——一个模型类装不下三种场景。

@@idea 核心思路
用"基类 + 继承 + 重写"一次搞定：

```python
class PatientBase(BaseModel):
    name: str
    age: int
    gender: str = "未知"
    diabetes_type: str = "2型"
    diagnosis_date: Optional[date] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    phone: Optional[str] = None
    ...

class PatientCreate(PatientBase):   # 创建：完整继承，name/age 必填
    pass

class PatientUpdate(PatientBase):   # 更新：所有字段转为可选
    name: Optional[str] = None
    age: Optional[int] = None
    ...

class PatientResponse(PatientBase): # 响应：加只读字段 + 计算属性
    id: int
    created_at: datetime
    updated_at: datetime
    bmi: Optional[float] = None
    bmi_status: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
```

设计要点：
- **Create** 复用基类，必填字段天然继承（name/age 必填，其余有默认值）；
- **Update** 把字段全部改成 `Optional`，配合 `exclude_unset=True` 实现"只更新传了的字段"；
- **Response** 增加数据库生成的 id/created_at 和计算属性 bmi/bmi_status。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Update 接口把没传的字段清空成 null | 更新时没用 `model_dump(exclude_unset=True)`——没传的字段被以 None 写入 |
| Response 报 "validation error for PatientResponse" | from_attributes 没配，或 ORM 对象上找不到 bmi 字段 |

@@point ④ from_attributes：让响应携带计算属性
@@need 要解决什么
模型上的 `bmi`、`bmi_status` 是 @property 计算出来的，Pydantic 怎么把"属性"当"字段"用？

@@idea 核心思路
妙处就在 `ConfigDict(from_attributes=True)`：

```python
class PatientResponse(PatientBase):
    bmi: Optional[float] = None
    bmi_status: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2 新配置
```

作用链拆开看：
1. 路由返回的是 Tortoise 模型对象（不是 dict）；
2. `from_attributes=True` 告诉 Pydantic：**按属性名从对象上取值**；
3. `bmi` 这个名字在模型上恰好是个 @property——于是**计算属性被自动序列化进响应体**；
4. 前端收到 `{"id": 1, "bmi": 24.3, "bmi_status": "正常", ...}`，不用自己再算。

这是 v2 相对 v1 的变化：v1 用 `class Config: orm_mode = True`，v2 统一改成 `model_config = ConfigDict(from_attributes=True)`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Response 里 bmi 恒为 null | 属性名对不上（模型上是 bmi，Schema 写成了 BMI）；或模型没定义该 @property |
| 报了 Config 相关警告 | 还在用 v1 风格的 `class Config: orm_mode`；v2 要写 `model_config = ConfigDict(...)` |

@@point ⑤ 患者 CRUD：增删改查五件套
@@need 要解决什么
路由层把"HTTP 请求"翻译成"数据库操作"，患者模块是七个子模块中最标准的样板。

@@idea 核心思路
```python
router = APIRouter(prefix="/patients", tags=["patients"])

# 列表：分页
@router.get("/", response_model=List[PatientResponse])
async def list_patients(skip: int = 0, limit: int = 20):
    patients = await Patient.all().offset(skip).limit(limit)
    return patients

# 单个详情
@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int):
    patient = await Patient.get(id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    return patient

# 创建
@router.post("/", response_model=PatientResponse)
async def create_patient(patient: PatientCreate):
    patient = await Patient.create(**patient.model_dump())
    return patient

# 更新（局部更新）
@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: int, data: PatientUpdate):
    patient = await Patient.get(id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    update_data = data.model_dump(exclude_unset=True)  # 只取传了的字段
    for key, value in update_data.items():
        setattr(patient, key, value)
    await patient.save()
    return patient

# 删除
@router.delete("/{patient_id}")
async def delete_patient(patient_id: int):
    patient = await Patient.get(id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    await patient.delete()
    return {"message": "删除成功"}
```

五个动作对应五种 HTTP 方法：GET 列表/详情、POST 创建、PUT 更新、DELETE 删除——这是**所有** CRUD 模块的通用骨架，后面六个模块全是它的变体。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 查不存在的患者返回 500 而非 404 | 用 `Patient.get()` 查不到会抛 DoesNotExist；先 get_or_none 判空再抛 HTTPException（本项目 get 配 if not 也可，注意 get 抛异常场景） |
| 创建接口 422 校验失败 | 前端传的字段名/类型与 Schema 不符；422 响应体里有具体字段错误，照着改 |
| 更新用 PUT 全量替换了记录 | PUT 语义是替换，本项目用 exclude_unset 实现"部分更新"，字段缺省则不覆盖 |

@@point ⑥ uvicorn 启动与自测
@@need 要解决什么
代码写完怎么跑起来？怎么验证接口真的通？

@@idea 核心思路
```bash
# 项目根目录下启动
python main.py
# 等价于：uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动后自测三连：
1. **文档页**：浏览器开 `http://localhost:8000/docs`，FastAPI 自动生成交互式 API 文档，每个接口都可以直接"Try it out"；
2. **健康检查**：访问 `http://localhost:8000/api/patients/` 应返回空列表 `[]`（数据库已通）；
3. **创建-查询闭环**：POST 创建一个患者 → GET 列表 → 确认返回头里带 `bmi` 计算属性。

`--reload` 的作用：改代码自动重启，开发期必备；生产部署去掉。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 端口被占用 | `uvicorn.run` 换成别的端口，或杀掉占用 8000 的进程 |
| 启动报 "Table patients does not exist" | 表没建！回第二章执行建库 SQL，或确认 generate_schemas 开关（本项目手动建表） |
| 改了代码不生效 | reload 模式下会自动重启；没开 reload 就手动重启服务 |

@@point ⑦ /docs 与响应验证：看懂 422 和 404
@@need 要解决什么
接口报错时，前端和后端怎么对齐"错在哪"？

@@idea 核心思路
FastAPI 把错误也"结构化"了，常见三种：

| 状态码 | 含义 | 本项目的场景 |
|---|---|---|
| 200/201 | 成功 | CRUD 正常返回 |
| 404 | 资源不存在 | `raise HTTPException(status_code=404, detail="患者不存在")` |
| 422 | 请求体校验失败 | 字段缺失、类型错、超范围 |

422 的响应体会明确告诉你哪里错：
```json
{
  "detail": [{"loc": ["body", "age"], "msg": "Input should be a valid integer", "type": "int_type"}]
}
```
`loc` 指出错误字段，`msg` 说明原因——联调时前端拿这个提示改参即可，不用猜。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 前端传 string 的 age，后端 422 | Strict 校验类型；前端应传数字，或 Schema 里做类型转换 |
| 中文 detail 显示乱码 | FastAPI 默认 UTF-8 正常；确认响应头 charset 无问题，浏览器端一般正常 |

@@point ⑧ 患者在整体架构里的"样板价值"
@@need 要解决什么
写完患者模块后，怎么把经验复用到后面六个模块？

@@idea 核心思路
患者模块是**最纯粹的 CRUD 样板**：无 AI、无统计、无关联聚合，只教"路由 + Schema + 模型"三者协作。对比后面模块：

| 模块 | 相对患者模块的增量 |
|---|---|
| 血糖 | 时间范围过滤 + 统计接口（调 health_analyzer） |
| 饮食 | 每日营养汇总 + AI 食谱推荐（调 diet_advisor） |
| 用药 | active_only 筛选 + 用药时间管理 |
| 运动 | 记录 + bs_change 计算属性 |
| 报告 | LLM 生成文本建议 + 周/月周期 |
| 对话 | LangGraph 工作流 + 历史持久化 |

**复用口诀**：路由五件套（列表/详情/创建/更新/删除）→ 字段差异甩给 Schema → 业务逻辑甩给 core 引擎。用这个节奏，后面六个模块每个都能在半小时内拿下。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 复制患者模块后忘了改 prefix | 路由前缀撞车，两个 /patients 冲突；每个文件 prefix 必须唯一 |
| response_model 忘了换 | 返回字段与声明的 Schema 不符，Pydantic 序列化报错 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **应用组装全流程** | main.py 里 CORS/路由/数据库/lifespan 各司其职，add_middleware → include_router → register_db 时序不乱 |
| **Schema 三件套模式** | Create 必填 / Update 全可选 + exclude_unset / Response 加 id 与计算字段，一处写好处处复用 |
| **可运行的患者 CRUD** | 五件套接口 + /docs 自测闭环，作为后续六个模块的复制模板 |

@@quiz
1. main.py 的组装顺序为什么是先 add_middleware 再 include_router 再 register_db？换序会怎样？
2. `/api/blood-sugar/patient/1` 这个 URL 是怎么由三层前缀拼出来的？各层在哪定义？
3. `exclude_unset=True` 的作用是什么？不用它时 PUT 更新会出现什么问题？
4. `from_attributes=True` 是干什么的？它如何让 bmi 这个 @property 出现在响应 JSON 里？
5. 请求体 age 传了 "abc"，后端返回什么状态码？响应体里如何定位错误字段？
6. 复用患者模块写血糖模块，至少需要改哪三处？

@@links
讲义|安康智慧健康管理平台：糖尿病AI健康助手讲义|#
官网|FastAPI 教程|https://fastapi.tiangolo.com/tutorial/
官网|Pydantic v2 模型配置|https://docs.pydantic.dev/latest/concepts/config/