# 泡泡画图 · 识图

返回总览：`/nai`

> 这几种功能不是同一件事：识图是让多模态模型理解参考图；i2i 是基于原图重绘；vibe_transfer 是让 NovelAI 参考画风或氛围；character_keep 是参考图片中的角色。纯粹要求参考画风不一定需要 AI 识图。

基础 nai 的参考图示例请写 `tag=1girl`（下面原文的 `nai 1girl` 是旧式写法）。

#### 识图（可选）

`nai画图` 和 `nai自动画图` 支持“把你发送的图片或引用的图片作为参考”交给**高级参数模型**进行识图（多模态）。

- 使用方式：发送命令时带上图片即可（同一条消息内）。

当你在同一条消息里发送多张图片时：

- 若启用了 `i2i` / `vibe_transfer` / `character_keep` 等参数，会按图片顺序先“消耗”对应数量。
- **剩余图片会作为识图参考**传给高级参数模型（需要开启 `llm.enable_vision=true`）。
- 可选：用 `llm.vision_image_limit` 限制传给模型的参考图片数量（0 表示不限制）。

---



## 🖼️ 图片引用功能

引用图片要注意只能引用聊天记录的第一张图，无法多张引用并使用。

### 图生图(i2i)
```
nai 1girl
i2i=true

[图片]
```

### 氛围转移(vibe_transfer)
```
nai 1girl
vibe_transfer=true
vibe_transfer_info_extract=0.8

[图片]
```

> ⚠️ `vibe_transfer` 与 `character_keep` 不能在同一次请求中同时使用。NovelAI
> 官方接口不允许同时混合普通参考图和 Director Reference；如需使用角色保持，
> 请移除 `vibe_transfer` 及其对应的参考图片。

### 角色保持(character_keep)
```
nai 1girl
character_keep=true

[图片]
```


