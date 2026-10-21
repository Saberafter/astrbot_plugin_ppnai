# V5 Full Medium

## 使用

将下面内容作为一条消息发送：

```text
/nai
model=nai5_medium
tag=1girl, outdoors, smile
```

完整模型 ID 为 `nai-diffusion-5-full-medium`，简写 `nai5_medium`、
`nai5_full_medium` 均可。也可以在管理面板中将它设为默认模型；
本次更新不会主动切换现有默认模型。

## 固定参数

- 步数固定为 14。
- 采样器固定为 `k_euler_ancestral`。
- 负面提示词固定使用官方 Heavy 预设，不接受自定义负面词。
- CFG Rescale 固定为 0。
- SMEA / SMEA+DYN 关闭。

这些限制在请求模型校验时应用，并在最终 API 请求边界再次应用，避免预设、
LLM 参数和显式覆盖绕过限制。参数记录会反映实际使用的固定值。
提示词引导值 `scale` 与分辨率仍按原配置处理，不会自动变更。

Medium 是 V5 Full 的蒸馏版本，不等于把 High 模式手动降到 14 步。
它通常消耗更少额度，但不承诺与 Full High 完全相同的质量、成本或速度。
最终计费与可用功能以 NovelAI 服务端为准。

## 适配证据

核对日期：2026-10-21。

- 官方说明：<https://docs.novelai.net/en/image/effort/>
- 官方图像页面：<https://novelai.net/image>
- 当前官方前端入口脚本：
  `/_next/static/chunks/1kcqqvyilqyxf.js?dpl=b50892a-38995131626-1`

官方前端定义了 `nai-diffusion-5-full-medium`，固定设置为 14 步、
`k_euler_ancestral` 和 Heavy 负面预设；Heavy 的当前预设编号为 2，
其预设文本已用于本插件的 Medium 请求。

离线测试覆盖模型选择、别名、参数约束、请求体和 Full 回归。
没有使用真实 Token 调用付费生成接口，因此正式使用前仍需一次经授权的实际出图验证。
