# Codeforces 个人助手 (CF StatTracker)

这是一个专为Codeforces打造的轻量级、高度可定制的桌面端数据看板，使用Python编写。

设计灵感来自CS的StatTrak™（又称暗金计数器），我觉得把AC的题目像打游戏的击杀一样全都记录下来会很coooool，所以我搞了这个:D

**🔒 隐私与安全声明** — 包括API key、secret在内的所有敏感数据全部存储在本地，网络请求仅限于与Codeforces官方服务器进行数据交互，无需过分担心隐私泄露。

>这是我的某种意义上的第一个独立开源项目，部分功能使用Gemini Code Assist进行vibe coding辅助开发，代码可读性、可拓展性可能有所欠缺，请见谅。

~~*AI太好用了你们知道吗）*~~

## 🔧 功能 Features

- 💀 **AC数量显示**：让你直观地看到自己至今为止在CF上面AC了多少道题。
- 📊 **个人数据显示**：快速浏览账号基本信息、最近 Rating 变更、即将开始的比赛。
- 📚 **错题本系统**：自动拉取最近未通过的提交记录，支持双击直接跳转网页重做。
- 🎨 **丰富自定义内容**：
  - 支持自定义窗口大小、背景图、侧边栏/卡片底色。
  - 全局字体、字号、颜色（标题/内容/侧边栏）完全解耦，支持自由选取。
  - 模块化设计，支持在设置中通过“上移/下移”自定义卡片排序及显示/隐藏。
- 🔒 **多线程安全**：底层采用ThreadPoolExecutor调度网络请求，确保 UI 流畅不卡顿。

## 🛠️ 安装与运行 Application

1. 克隆本项目到本地：
   ```bash
   git clone https://github.com/你的用户名/你的仓库名.git
   cd 你的仓库名
   ```

2. 安装所需依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 运行程序：
   ```bash
   python main.py
   ```
   （也可将文件重命名为 main.pyw 实现无控制台静默运行）

* Windows系统可以直接下载release版本的exe使用，但是相对来说比较臃肿（30MB左右）

## 📮 联系我 Contact
- E-mail ykx_personal@163.com
- 或者直接在github上面提交issue

enjoy ;)