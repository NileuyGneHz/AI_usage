下面给你一份**针对你这台 Ubuntu、已经建好 `~/ml-ng/.venv` 环境**的具体启动指南。你之前那次其实已经启动成功了，终端停住不是卡住，而是在等浏览器访问。

## 每次启动 JupyterLab 的标准流程

### 第 1 步：打开终端

在 Ubuntu 上按：

```text
Ctrl + Alt + T
```

### 第 2 步：进入你的机器学习目录

```bash
cd ~/ml-ng
```

### 第 3 步：激活虚拟环境

```bash
source .venv/bin/activate
```

激活成功后，终端提示符前面会出现：

```text
(.venv) nileuy@nileuy-GP66-Leopard-11UG:~/ml-ng$
```

看到 `(.venv)` 就说明环境对了。

### 第 4 步：启动 JupyterLab

```bash
jupyter lab
```

如果这条命令提示找不到，就用：

```bash
python -m jupyterlab
```

### 第 5 步：打开浏览器

启动后终端会出现类似：

```text
Jupyter Server 2.21.0 is running at:
http://localhost:8888/lab?token=xxxxxxxxxxxxxxxx
```

通常 Ubuntu 会自动打开浏览器。  
如果没有自动打开，手动打开 Firefox 或 Edge，把完整 URL 复制进去，包括 `token=` 后面那一长串。

例如你上次的地址是：

```text
http://localhost:8888/lab?token=9015dc58dcc57c014e17ff09ffc68dd90c55ae1a99d544a4
```

## 启动成功的标志

终端出现这行：

```text
Jupyter Server 2.21.0 is running at:
```

浏览器能看到 JupyterLab 界面，左侧有文件浏览器。  
这时终端会一直停在那里，这是正常的，不要关掉它。

## 选择正确的 Python 内核

进入 JupyterLab 后：

1. 点击 `File` → `New` → `Notebook`
2. 右上角选择内核：`Python (ML venv)`
3. 如果没有这个选项，刷新页面；你之前已经注册过 `ml-venv`，应该能看到。

然后运行：

```python
import sys
print(sys.executable)

import numpy as np
import sklearn
print(np.__version__)
print(sklearn.__version__)
```

如果 `sys.executable` 输出：

```text
/home/nileuy/ml-ng/.venv/bin/python
```

说明你用的是正确的虚拟环境。

## 如何停止 JupyterLab

回到运行 Jupyter 的终端，按：

```text
Ctrl + C
```

如果提示：

```text
Shutdown this Jupyter server (y/[n])?
```

输入：

```text
y
```

再按回车。  
如果没提示，就再按一次 `Ctrl + C`。

终端回到：

```text
(.venv) nileuy@nileuy-GP66-Leopard-11UG:~/ml-ng$
```

就说明已经关闭。

## 如果想让 Jupyter 不自动打开浏览器

有时你可能想自己复制 URL，可以用：

```bash
jupyter lab --no-browser
```

然后手动复制终端里的 `http://localhost:8888/lab?token=...`。

## 如果 8888 端口被占用

换一个端口，比如 8889：

```bash
jupyter lab --port=8889
```

然后访问：

```text
http://localhost:8889/lab?token=...
```

## 如果 ROS2 的 Python 路径干扰

你装了 ROS2，有时会干扰虚拟环境。可以这样启动：

```bash
unset PYTHONPATH
jupyter lab
```

## 一键启动脚本（可选）

如果你不想每次输三行命令，可以建一个脚本：

```bash
cd ~/ml-ng
nano start_jupyter.sh
```

写入：

```bash
#!/usr/bin/env bash
cd ~/ml-ng
source .venv/bin/activate
jupyter lab
```

保存后退出，然后给它执行权限：

```bash
chmod +x ~/ml-ng/start_jupyter.sh
```

以后启动只需要：

```bash
~/ml-ng/start_jupyter.sh
```

## 最简记忆版

以后每次就是：

```bash
cd ~/ml-ng
source .venv/bin/activate
jupyter lab
```

然后浏览器打开终端里给的 `http://localhost:8888/lab?token=...`。  
停止就按 `Ctrl + C`。
