# 泡泡画图 · 输出

返回总览：`/nai`

> 以下包含可选配置说明，不表示二维码、公开图床或夸克分享已开启；查看帮助不会上传图片或修改设置。

## 🖼️ 图片输出方式

默认会以**合并转发消息**的形式发送，避免图片在聊天列表中过于显眼。

如需直接发送图片，可在配置中关闭：

- `general.merge_draw_to_chat_record=false`

### 每张图的 Seed

生成成功后，每张图片旁会附带 `seed=实际数字`，直发和合并转发均支持，
不需要开启 `data=true`，也不会因此额外输出提示词。
不填 `seed` 时，插件在组装官方请求前随机产生具体数字；
批量生成会逐张随机，失败重试只回显成功那次请求的 seed。
填写 `seed=数字` 可以固定种子。seed 同时写入本地生成记录，
旧记录不会自动补全。复现图片还需要保持模型、提示词和其他参数一致。

### 生成参数记录

参数记录由配置 `general.send_generation_details` 控制，也可以在单次绘图指令中使用
`data=true` 开启。插件会额外发送一条合并聊天记录，内容包括：
- 原始指令
- 最终正向和反向提示词
- 最终模型、尺寸、步数、采样器、种子等参数；批量生成按图片顺序列出各张实际 seed
- 使用的输入图片（若有）
优先级规则：
- 配置开启且未填写 `data`：输出
- `data=true`：输出
- 配置开启且 `data=false`：仍输出（配置开启优先）
- 配置关闭且未填写 `data` 或 `data=false`：不输出

### 发送二维码

在通用设置中开启 `general.send_qr=true` 后，每次生成完成会额外发送二维码；即使配置关闭，也可以用 `QR=true` 对单次请求开启：

```
nai
tag=1girl, coffee shop
QR=true
```

二维码中编码的是匿名图床链接，因此每张生成图片只会发送一张二维码。二维码功能独立于夸克网盘，不需要夸克登录；若图床上传失败，则不会发送对应二维码。

### 发送夸克网盘分享链接

在通用设置中开启 `general.send_quark_link=true` 后，每次生成完成会额外上传图片到夸克网盘并发送公开分享链接；即使配置关闭，也可以用 `QK=true` 对单次请求开启：

```
nai
tag=1girl, coffee shop
QK=true
```

使用前需要：

1. 开启 `general.send_quark_link`。
2. 首次启用或 Cookie 缺失时，插件会在 AstrBot 日志输出夸克登录二维码，使用夸克 APP 扫码即可。
3. 根据需要设置 `quark.link_expiry_minutes`、`quark.parent_folder_id` 和 `quark.delete_after_expiry`。

夸克链接会作为生成后的独立附加消息发送，不会替代原图；批量生成时每张图片都会尝试上传并输出对应链接。开启自动删除后，插件只会删除自己登记的上传文件。



### 出图后反馈

开启 `reaction.enabled` 后，生成成功会按冷却时间随机发送短评。配置 `reaction.sticker_enabled=true` 并将表情图片放入插件数据目录的 `reaction_stickers` 文件夹后，还会按 `reaction.sticker_probability` 随机附带表情包。短评文本在 `reaction.comments` 中按行配置。

### 图片缓存

- `general.vibe_image_cache_enabled`：缓存氛围转移输入原图，默认开启。
- `general.image_cache_enabled`：缓存全部 AI 生成图片，默认关闭。
- `general.image_cache_max_size_mb`：图片缓存容量上限，默认 10MB。

Vibe 输入原图缓存只保存输入图片用于排查，不会替代或绕过 NovelAI 的氛围转移编码请求。
关闭缓存时仍会直接将输入图片提交给官方编码接口；如果接口返回
`GenerateError: 氛围转移参考图编码失败 (status=500)`，通常是官方编码服务、图片格式或图片内容导致，
与本地是否保存输入原图无关。


