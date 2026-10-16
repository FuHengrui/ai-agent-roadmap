# -*- coding: utf-8 -*-
"""从手机的百度网盘目录拉取一个阶段的资料，并正确还原中文文件名。

★ 为什么要这么绕
----------------
`adb pull` 遇到**中文目录名**会失败：

    adb: error: failed to create directory '...\\章\\': Illegal byte sequence

而且**改成英文目标路径也没用** —— 因为源目录里面的 `代码`/`文档`/`软件` 也是中文，
adb 建这些子目录时一样会炸。

Windows 自带的 `tar.exe` 也不是答案：它会把 tar 里的 UTF-8 文件名按 CP936 读，
解出来是 `Agent椤圭洰鍚` 这种乱码，而且**部分字节走了回退路径，逆变换救不回来**。

★ 正确的做法（本脚本）
---------------------
    1. 手机上用 tar 打包成【英文名】的压缩包
    2. adb pull 这个 .tar.gz（纯英文路径，不会炸）
    3. 用 Python 的 `tarfile` 解压 —— 它对 UTF-8 文件名的处理是正确的
    4. 搬到中文目标目录

用法
----
    python pull_stage.py "04低代码Agent平台实战" "4.低代码Agent平台实战"

    第一个参数：手机上的阶段目录名（原样，可以带中文）
    第二个参数：电脑上的目标文件夹名（可选，默认跟第一个一样）
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ======================================================================
#  配置区 —— 按你自己的环境改
# ======================================================================
# adb 可执行文件：https://developer.android.com/tools/releases/platform-tools
ADB = os.environ.get("ADB", r"C:\platform-tools\adb.exe")

# 手机上的源目录
PHONE_BASE = os.environ.get("PHONE_BASE", "/sdcard/Download/资料")

# 电脑上的目标目录
PC_BASE = Path(os.environ.get("PC_BASE", r"D:\资料"))

# 设备序列号：同时插多台设备时【必须】指定，否则 adb 报
#   "more than one device/emulator"
#
# 怎么查你自己的序列号：
#   adb devices
# 输出第二列那一串就是，例如：
#   2TX9K24203001097        device
#
# 设成环境变量 ANDROID_SERIAL，或者直接改下面这行的默认值。
SERIAL = os.environ.get("ANDROID_SERIAL", "")

TMP_TAR = Path(os.environ["TEMP"]) / "_kb_pull.tar"
TMP_EXT = Path(os.environ["TEMP"]) / "_kb_ext"


def run(args):
    """跑 adb 命令，自动带上 -s <序列号>。"""
    full = [args[0], "-s", SERIAL] + list(args[1:])
    return subprocess.run(full, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def human(n: float) -> str:
    return "%.1f MB" % (n / 1024 / 1024) if n > 1024 * 1024 else "%.1f KB" % (n / 1024)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    src_name = sys.argv[1]
    dst_name = sys.argv[2] if len(sys.argv) > 2 else src_name
    dst = PC_BASE / dst_name

    print("=" * 70)
    print("  拉取：%s" % src_name)
    print("  目标：%s" % dst)
    print("=" * 70)

    # ---------- 0. 手机上确认存在 ----------
    r = run([ADB, "shell", "test -d '%s/%s' && echo YES || echo NO" % (PHONE_BASE, src_name)])
    if "YES" not in (r.stdout or ""):
        print("  !! 手机上找不到这个目录：%s/%s" % (PHONE_BASE, src_name))
        return 1

    # ---------- 1. 手机上打包 ----------
    # 刻意【不压缩】：后面几个阶段的体积大头是 .exe / .tar.gz / .zip 这类
    # 早已压缩过的安装包，再 gzip 一遍几乎不减小体积，却要手机 CPU 啃很久。
    # 实测压缩比接近 1:1，纯属浪费。直接 tar 打包，把时间花在传输上更划算。
    print("\n  (1) 手机上打包（不压缩）...")
    r = run([ADB, "shell", "cd '%s' && rm -f %s && tar -cf %s '%s' && echo OK"
             % (PHONE_BASE, PHONE_TAR, PHONE_TAR, src_name)])
    if "OK" not in (r.stdout or ""):
        print("     失败：%s" % ((r.stdout or "") + (r.stderr or "")))
        return 1
    r = run([ADB, "shell", "ls -l %s" % PHONE_TAR])
    print("     OK  %s" % (r.stdout or "").strip())

    # ---------- 2. 拉取 ----------
    print("\n  (2) 拉取 tar 包...")
    TMP_TAR.unlink(missing_ok=True)
    t0 = time.time()
    r = run([ADB, "pull", PHONE_TAR, str(TMP_TAR)])
    if not TMP_TAR.exists():
        print("     失败：%s" % ((r.stdout or "") + (r.stderr or "")))
        return 1
    print("     %s  耗时 %.1f 秒" % (human(TMP_TAR.stat().st_size), time.time() - t0))

    # ---------- 3. tarfile 解压（关键：UTF-8 正确）----------
    print("\n  (3) 用 Python tarfile 解压...")
    if TMP_EXT.exists():
        shutil.rmtree(TMP_EXT, ignore_errors=True)
    TMP_EXT.mkdir(parents=True)
    with tarfile.open(TMP_TAR, "r:*", encoding="utf-8") as tf:
        names = tf.getnames()
        print("     包内条目 %d 个，顶层：%s" % (len(names), names[0] if names else "?"))
        try:
            tf.extractall(TMP_EXT, filter="data")
        except TypeError:      # Python < 3.12 没有 filter 参数
            tf.extractall(TMP_EXT)

    # ---------- 4. 搬到目标位置 ----------
    print("\n  (4) 放到目标位置...")
    inner = TMP_EXT / src_name
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if inner.is_dir():
        shutil.move(str(inner), str(dst))
    else:
        subs = [p for p in TMP_EXT.iterdir() if p.is_dir()]
        shutil.move(str(subs[0] if len(subs) == 1 else TMP_EXT), str(dst))
    print("     OK  %s" % dst)

    # ---------- 5. 清理 ----------
    run([ADB, "shell", "rm -f %s" % PHONE_TAR])
    shutil.rmtree(TMP_EXT, ignore_errors=True)
    TMP_TAR.unlink(missing_ok=True)

    # ---------- 6. 报告 ----------
    nf = sum(1 for _, _, fs in os.walk(dst) for _ in fs)
    total = sum(p.stat().st_size for p in dst.rglob("*") if p.is_file())
    print("\n  解出 %d 个文件，合计 %s" % (nf, human(total)))
    print()
    print("  最终结构：")
    base_depth = len(str(dst).split(os.sep))
    for dp, dns, fs in os.walk(dst):
        depth = len(dp.split(os.sep)) - base_depth
        print("    %s[%s]" % ("  " * depth, os.path.basename(dp) or "."))
        for x in sorted(fs):
            sz = (Path(dp) / x).stat().st_size
            print("    %s  %-38s %10s" % ("  " * (depth + 1), x, human(sz)))

    print()
    print("  资料文件夹现有阶段：")
    for d in sorted(PC_BASE.iterdir()):
        if d.is_dir():
            n = sum(1 for _, _, fs in os.walk(d) for _ in fs)
            sz = sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
            print("    %-34s %2d 个文件  %8s" % (d.name, n, human(sz)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
