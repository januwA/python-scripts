## 一些python脚本

- python3
- 文件名都将以`a`开始，避免冲突.
- 脚本文件首行必须是`#!/usr/bin/python3`


## [在cmder中使用](https://github.com/cmderdev/cmder/issues/2611)

需要将 python 安装到`cmder\vendor\git-for-windows\usr\bin` 然后`cp ./python.exe ./python3.exe`

将脚本路径添加到环境变量

```
$ vim /etc/profile

# 文件最后添加
PATH=$PATH:/usr/local/python-scripts
export PATH
```