# majsoul-helper

## 现有功能:

- [x] 支持[Akagi](https://github.com/shinkuan/Akagi)
- [x] 自动打牌

## 欢迎 PR

## 用前须知

> _魔改千万条，安全第一条。_
>
> _使用不规范，账号两行泪。_
>
> _本插件仅供学习参考交流，_
>
> _请使用者于下载 24 小时内自行删除，不得用于商业用途，否则后果自负。_

## 支持平台

- 雀魂网页端

## 使用方法

需求 Python >= 3.10

同步仓库

```bash
git clone https://github.com/lqgl/majsoul-helper.git && cd majsoul-helper
```

配置国内镜像源（可选）

```bash
python -m pip config set global.index-url https://mirror.nju.edu.cn/pypi/web/simple
```

安装依赖

```bash
python pip install --upgrade pip
python pip install -r requirements.txt
python playwright install chromium
```

使用 Akagi

> 到 [Discord](https://discord.gg/Z2wjXUK8bN) 下载 Akagi 提供的 bot.zip。 注: 网盘中除 v2 版本均可用，任选一个下载。解压获取 **mortal.pth** 与 **libriichi** 文件，放置到 bot 文件夹中。

> 注: 3p 的 mortal.pth 及对应的 libriichi 文件需捐赠 Akagi 进行获取.

启动

```bash
python main.py
```

## 特别感谢

- [Akagi](https://github.com/shinkuan/Akagi)

- [majsoul-hook-mitm](https://github.com/anosora233/majsoul-hook-mitm)

## 交流群

[Discord](https://discord.gg/NTXFtuRK)