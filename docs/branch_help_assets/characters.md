# 泡泡画图 · 角色

返回总览：`/nai`

> 这是文字 Tag 库，不等于图片角色保持。图片角色保持与画风参考见 `/nai 识图`。

## 🧩 角色 Tag 库（CS）

CS 是纯 NovelAI 角色 Tag 库，不再调用 LLM 生成或改写角色外貌档案，也不会把角色档案作为 `nai画图` 的额外系统上下文。

### 添加角色

第一行写角色名称，后续行直接填写该角色的 NovelAI Tag：

```text
cs添加 夕立
yuudachi kai ni (Kancolle)
```

角色库按用户隔离。旧版 `nn=` 纯 Tag 条目继续兼容；旧版 `<tag>...</tag>` 档案会自动提取其中的 Tag。

### 查看、修改和删除

```text
cs
scs 夕立
ccs 夕立
yuudachi kai ni (Kancolle), red eyes
dcs 夕立
```

`cs` 查看名称列表；`scs` 查看 Tag；`ccs` 覆盖更新 Tag；`dcs` 删除条目。管理员仍可按原方式指定用户 ID 管理其他用户的条目。

### 在绘图中引用角色

`nai`、`nai画图` 和 `nai自动画图` 均支持 `cs`、`cs1`、`cs2` 等选择器，写法与 `s1` 预设相似。多个角色按编号顺序将角色库原始 Tag 追加到最终正向 `tag`：

```text
nai
tag=standing, looking at viewer
cs1=夕立
cs2=樱羽艾玛
```

`nai画图` 也可与 `ds` 一起使用。高级参数 LLM 负责生成描述参数；CS Tag 会在 LLM 生成后追加，不会被改写：

```text
nai画图
ds=两人在樱花树下并肩散步
cs1=夕立
cs2=樱羽艾玛
```

AI 绘图工具不会自动添加 `csN` 或替 AI 决定是否使用角色。智能体可先调用 `stnai_search_character_tags`，将用户原始请求作为 `query`；检索结果会返回可放入绘图 description 的“人物Tag预留库”区块及 `角色名:角色库原始Tag` 行，例如 `夕立:yuudachi kai ni (Kancolle)`。之后由 AI 自行决定是否将原始 Tag 纳入绘图 description/`tag`，再调用 `stnai_generate_image`。命中的 Tag 不会被插件自动改写、追加或转成 `csN`。

此 CS 文本 Tag 库不同于 NovelAI 图片角色保持参数 `character_keep=图库名称`。

---

