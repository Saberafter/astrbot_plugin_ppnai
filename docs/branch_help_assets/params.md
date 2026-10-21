# 泡泡画图 · 参数

返回总览：`/nai`

> 以下是完整参数参考。日常绘图入门见 `/nai 画图`；表中命令的具体操作见各功能分支。

## 📋 可用模型

- `nai-diffusion-3` `nai3` - NAI3 标准模型
- `nai-diffusion-furry-3` `nai3_furry` - NAI3 Furry模型
- `nai-diffusion-4-full` `nai4_full` - NAI4 完整版
- `nai-diffusion-4-curated-preview` `nai4_c_p` - NAI4 精选预览版
- `nai-diffusion-4-5-curated` `nai4.5_c` - NAI4.5 精选版
- `nai-diffusion-4-5-full` `nai45f` - NAI4.5 完整版
- `nai-diffusion-5-full` `nai5f` - NAI5 完整版
- `nai-diffusion-5-full-medium` `nai5m` - NAI5 Medium
- `nai-diffusion-5-curated` `nai5_c` - NAI5 精选版

Medium 固定使用 14 步、Euler Ancestral、官方 Heavy 负面预设，
CFG Rescale 为 0，SMEA 关闭。上述固定设置优先于默认值、预设和单次参数；
其他模型不受影响。

在绘图消息中添加 `model=nai5m`、`model=nai5f` 或 `model=nai45f`，
仅切换本次请求，不修改面板默认模型；下一次不写 `model=` 时仍按默认值或预设。
完整模型名称和旧简写 `nai5_medium`、`nai5_full_medium`、`nai5_full`、
`nai4.5_full` 继续支持。

```
/nai
model=nai5m
tag=1girl, outdoors, smile
```

---



## 🎯 多角色控制(role)

格式：`role=位置|正向提示词|反向提示词`

位置网格（5x5）：
```
     A    B    C    D    E
  ┌────┬────┬────┬────┬────┐
1 │ A1 │ B1 │ C1 │ D1 │ E1 │
  ├────┼────┼────┼────┼────┤
2 │ A2 │ B2 │ C2 │ D2 │ E2 │
  ├────┼────┼────┼────┼────┤
3 │ A3 │ B3 │ C3 │ D3 │ E3 │
  ├────┼────┼────┼────┼────┤
4 │ A4 │ B4 │ C4 │ D4 │ E4 │
  ├────┼────┼────┼────┼────┤
5 │ A5 │ B5 │ C5 │ D5 │ E5 │
  └────┴────┴────┴────┴────┘
```

示例：
```
nai 2girls
role=A2|1girl, cute, smile
role=D2|1girl, cool|bad anatomy
```

---



## ⚙️ 参数指令表

| 参数 | 别名 | 说明 |
|------|------|------|
| `nai` | 基础绘图指令 | 支持 `key=value` 参数 |
| `nai画图` | AI 辅助绘图指令 | 支持 `ds=` 与参数覆盖 |
| `nai自动画图` | 查看或设置自动画图 | 可附带预设参数 |
| `nai自动画图开` | 开启自动画图 | 消耗开启者额度 |
| `nai自动画图关` | 关闭自动画图 | |
| `s` `s1` `s2`... | 预设 | 按优先级使用预设内容（仅命令输入）s=s1 |
| `ds` | 描述 | 自然语言描述（`nai画图` 使用） |
| `cs` `cs1` `cs2` | 角色 Tag 选择器 | 引用并追加角色库中的 Tag |
| `cs添加` | 添加角色 Tag | 命令后写角色名，下一行起填写 NovelAI Tag |
| `cs` | 查看角色名称列表 |
| `dcs` | 删除角色 Tag |
| `scs` | 查看角色 Tag |
| `ccs` | 覆盖修改角色 Tag |
| `tag` | 正向提示词 | 期望生成的图片内容 |
| `negative` `ne` | 反向提示词 | 不想出现的内容 |
| `prepend_tag` `a_tag` | 前置正向/前置正向提示词 | 添加到正向提示词最前方 |
| `append_tag` `b_tag` | 后置正向/后置正向提示词 | 添加到正向提示词最后方 |
| `prepend_negative` `a_ne` | 前置负面/前置负面提示词 | 添加到负面提示词最前方 |
| `append_negative` `b_ne` | 后置负面/后置负面提示词 | 添加到负面提示词最后方 |
| `n` | 批量生成 | 批量出图并扣除对应额度 |
| `model` | 模型 | 选择绘图模型 |
| `artist` | 画师/画师串 | 指定画师风格 |
| `size` | 画面尺寸 | 竖图`portrait`/横图`landscape`/方图`square` 或 WxH(白名单专用) |
| `seed` | 种子 | 固定随机种子 |
| `steps` | 采样步数 | 1-50，默认23 (28以上为白名单专用)|
| `scale` | 提示词引导值 | 默认5 |
| `cfg` | 缩放引导值 | 默认0 |
| `sampler` | 采样器 | 选择采样方法 |
| `noise_schedule` `n_s` | 噪声调度 | karras等 |
| `other` | 高级配置 | SMEA等设置 |
| `i2i` | 图生图 | 引用图片进行重绘 |
| `i2i_force` `i_f` | 重绘力度 | 0-1，默认0.6 |
| `vibe_transfer` `v_t` | 氛围转移 | 参考图片风格 |
| `vibe_transfer_info_extract` `v_t_i_e` | 氛围转移信息提取度 | 0-1 |
| `vibe_transfer_ref_strength` `v_t_r_s` | 氛围转移参考强度 | 0-1 |
| `data` | 输出参数记录 | 可选 `true` / `false`；具体优先级见上方说明 |
| `QR` | 输出图片二维码 | `QR=true` 可单次开启；二维码编码图片分享链接，每张图片只发送一张 |
| `QK` | 上传并分享夸克网盘链接 | `QK=true` 可单次开启；需完成夸克扫码登录 |
| `role` | 角色/多角色 | 多角色控制 |
| `character_keep` `c_k` | 角色保持/ck | 保持角色特征 |
| `character_keep_vibe` `c_k_v` | 角色保持氛围 | true/false |
| `character_keep_strength` `c_k_s` | 角色保持强度 | 0-1 |
| `nai预设列表` | 查看所有可用预设 | |
| `nai预设查看` | 查看指定预设内容 | |
| `nai预设添加` | 添加预设（管理员） | |
| `nai预设修改` | 修改预设内容，并可更新预览图 | |
| `nai预设删除` | 删除预设（管理员） | |
| `nai图库` | 查看图库列表 | |
| `nai图片查看` | 查看指定图库图片；不填写图片名时查看图库列表 | |
| `nai图片添加` | 添加图库图片（管理员） | |
| `nai图片修改` | 修改图库图片（管理员） | |
| `nai图片删除` | 删除图库图片（管理员） | |
| `nai队列` | 查询队列状态 | |
| `nai签到` | 每日签到获取额度 | |
| `查询额度` | 查询剩余额度 | |
| `nai今日排行` | 查看今日成功出图排行榜（前十名） | |
| `nai总数` | 查看插件累计成功生成的图片总数 | |
| `nai账户` | 查询 NovelAI 账户订阅状态和 Anlas 余额（管理员） | |
| `nai审计` | 查看最近 NovelAI Anlas 消耗审计（管理员） | |
| `拉上帷幕` | 设置当前会话的帷幕表图 | 后续生成自动进行幻影坦克合成 |
| `查看帷幕` | 查看当前会话的帷幕表图 | |
| `撤下帷幕` | 移除当前会话的帷幕表图 | |
| `nai黑名单添加` | 添加黑名单（管理员） | |
| `nai黑名单移除` | 移除黑名单（管理员） | |
| `nai黑名单列表` | 查看黑名单（管理员） | |
| `nai白名单添加` | 添加白名单（管理员） | |
| `nai白名单移除` | 移除白名单（管理员） | |
| `nai白名单列表` | 查看白名单（管理员） | |
| `nai查询用户` | 查询用户额度（管理员） | |
| `nai设置额度` | 设置用户额度（管理员） | |
| `nai增加额度` | 增加用户额度（管理员） | |
---
