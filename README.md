## 一些python脚本

- 文件名都将以`a`开始，避免冲突.

## Windows 安装 python3

```sh
winget search python3
winget install Python.Python.3
```

安装好后把`python.exe`在同目录复制一份为`py.exe`

## Fedora 安装 python3

Fedora安装后自带python3，但需要安装pip和launcher

```sh
dnf install python-pip python-launcher -y 
```

## bash

将脚本路径添加到环境变量

```
$ vim /etc/profile

# 文件最后添加
PATH=$PATH:/usr/local/python-scripts
export PATH
```


如果是`windows+wsl`可以直接在windows上设置环境变量，打开wsl时会自动读取