# 开发与部署

## 仓库来源

- 维护仓库：`Saberafter/astrbot_plugin_ppnai`
- 上游仓库：`dafeiwu666/astrbot_plugin_ppnai`
- 原部署基准：`3fba81326ef789e4ec38cd2a20d589efca5b68f3`（v1.7.0）
- `origin` 指向维护仓库，`upstream` 指向上游。

## 本机开发

```powershell
uv venv --python 3.13
uv pip install --python .venv/Scripts/python.exe -r requirements.txt -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m compileall -q main.py src scripts tests
```

测试不需要 NovelAI Token，不调用付费生成接口。未安装 AstrBot 时，测试只为
日志和消息组件提供最小替身，不模拟真实 QQ 发图或 AstrBot 插件热更新。

## 帮助系统

- `/nai`：功能总览。
- `/nai 预设`、`/nai 参数` 等：对应主题帮助。
- `/nai帮助`：帮助入口。
- `src/manual_help.py`：指令匹配、静态帮助图校验、文字回退。
- `docs/branch_help_assets/`：当前使用的主题文案、图片和清单。
- `docs/USAGE.md`：完整使用文档。

主题帮助不再依赖旧快速帮助模块或旧整页帮助图片。
修改完整文档时，同步修改相关主题的 `.md`，然后只重建受影响的主题：

```powershell
.venv/Scripts/python.exe scripts/build_help_assets.py --topic params
```

不指定 `--topic` 会重建全部主题。提交对应文案、PNG 和 `manifest.json`，
测试会校验完整文档、主题文案和图片的哈希。渲染器只在本机开发时运行，
生产环境仍使用静态帮助图片。

不要把运行配置、用户数据、Token、Cookie 或生成记录放入仓库。

## 从 GitHub 更新 VPS

推送 GitHub 不会自动修改 VPS。首次接入维护仓库时，需要：

1. 备份当前插件源码，并记录可回滚的提交。
2. 保留外部的插件配置和 `plugin_data`，不要覆盖或删除它们。
3. 在 AstrBot 的插件安装或更新流程中，将来源指定为本 fork。
4. 安装或核对依赖，重载插件，检查日志和帮助命令。

之后可由 AstrBot 的插件更新功能更新代码并重载。当前 VPS 上的 AstrBot
更新器会按仓库下载和替换插件，而且安装时会移除 Git 元数据，因此生产目录没有
`.git` 是正常情况，不需要把它改成 Git 工作区。
更新器默认使用插件元数据中的 `repo`，但调用方传入的仓库或下载源可覆盖它。
更新前务必核对面板选中的仓库，避免又从上游市场源覆盖本 fork。
不要直接在生产目录修改源码；更新操作会替换该目录，本地改动应先迁回开发仓库。

## 同步上游

先在本机执行 `git fetch upstream`、查看差异，合并并测试后再推送 `origin`。
不要在生产环境直接合并未经测试的上游改动。
