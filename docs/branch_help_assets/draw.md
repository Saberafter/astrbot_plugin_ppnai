# 泡泡画图 · 画图

返回总览：`/nai`

> 参数完整列表另见 `/nai 参数`。普通提示词可直接粘贴，自由换行；旧 `tag=` 仍有效。

# 泡泡画图插件 使用文档

## 📖 概述

泡泡画图是一个基于 NovelAI 官方 API 的 AI 绘图插件，支持文生图、图生图、氛围转移、角色保持等多种功能。

### 🆓 Opus 免费模式

本插件支持 **Opus 免费模式**（小图模式），开启后会自动调整参数以符合 NovelAI Opus 订阅的免费生成条件：
- 分辨率限制在 **1024×1024 像素**以内
- 步数限制在 **28 步**以内

> 💡 Opus 订阅用户在此条件下可以**无限免费生成**图片，无需消耗 Anlas！
> 
> ⚠️ 注意：部分高级功能（如高分辨率、高步数）在免费模式下会被自动调整。

---



## 🎨 画图命令

### 基础命令 `nai`

普通正文就是正向提示词，保留换行、空行、权重和中英文描述。模型、尺寸、种子等参数仍独立一行：

```
/nai
model=5f

1girl, solo,
white hair, blue eyes,

white dress, standing,
garden, sunlight
```

### 多人分区

```
/nai
model=5f
size=1216x832
2girls, garden, sunlight

角色1=左
girl, white hair, white dress

角色2=右
girl, black hair, black jacket

负面1=
black hair, black jacket

负面2=
white hair, white dress

negative=
blurry, watermark
```

`角色1=` / `role1=` 开始该角色正向；`负面1=` / `negative1=` 对应角色负面。再次进入同一编号会追加正文，普通参数不改变分区。`negative=` / `负面=` 始终是全局负面；单独一行 `tag=` 可切回全局正向。

角色按编号排序，正向、负面、坐标分别绑定。位置可写九方位、A1～E5、0～1 的 x,y 坐标，详见 `/nai 参数`。所有角色须全部明确定位或全部自动，不混用。V3 不支持；V5 Medium 不支持自定义角色负面。

独立 `键=值` 行键名未知会提示行号；若这是正文，用 `tag=键=值`。不加分类标题或注释，标题会成为提示词。

### 只写词 `/nai写词`

```
/nai写词 两名女孩站在花园，左边白发白裙拿花，右边黑发夹克拿书
```

使用与聊天相同的 `anima-tag-planner` 规则，只返回可复制的 `/nai` 指令，中文对照另条发送；不生成图片、不扣绘图额度。使用高级参数 LLM，未配置则使用当前聊天模型；LLM 服务正常计费。开启识图后可附参考图。
#### 批量生成（扣除对应额度）

```
nai
tag=1girl, coffee shop, smile
n=3
```

未填写 `n` 时默认生成 1 张；开启额度系统后按 `n` 扣除额度。`nai画图` 与自动画图批量模式会为每张图重新调用 LLM 生成参数。



### AI 画图命令 `nai画图`

使用 AI 自动解析描述生成参数：

```
nai画图
s1=预设名
ds=画一个在咖啡店微笑的女孩
```

- `s1`、`s2` 等：按优先级使用多个预设
- `ds`：自然语言描述，AI 会自动转换为绘图参数

#### 使用 `nai` 参数进行个性化设置（推荐）

`nai画图` 除了支持自然语言 `ds` 让 AI 自动生成参数，也支持直接写 **与 `nai` 同款的 `key=value` 参数**来个性化控制；这些显式参数会优先生效/覆盖 AI 自动生成的结果。

示例：
```
nai画图
ds=把图里的角色改成冬装
model=nai-diffusion-4-5-curated
steps=28
size=竖图
前置正向=best quality, masterpiece
s=预设
s2=预设
cs1=角色名
cs2=另一个角色名
```

