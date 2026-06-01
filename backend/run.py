#!/usr/bin/env python
"""一键启动脚本。

用法:
    python run.py api              # 启动 FastAPI 后端
    python run.py test             # 运行测试
    python run.py test --watch     # 监听模式（文件变化自动重跑）
    python run.py test --coverage  # 带覆盖率报告
    python run.py install          # 安装依赖
"""

import sys
import os


def cmd_api():
    print("🚀 启动 FastAPI: http://localhost:8000")
    os.chdir(os.path.dirname(__file__))
    os.system("uvicorn app.main:app --reload --port 8000")


def cmd_test():
    os.chdir(os.path.dirname(__file__))
    args = sys.argv[2:]

    if "--watch" in args or "-w" in args:
        print("🧪 监听模式 - 文件变化自动重跑测试...")
        os.system("ptw tests/ -- --tb=short")
        return

    cmd = "python -m pytest tests/ -v --tb=short"

    if "--coverage" in args or "-c" in args:
        print("🧪 运行测试 + 覆盖率报告...")
        os.system(cmd + " --cov=app --cov-report=term")
        return

    print("🧪 运行测试...")
    exit_code = os.system(cmd)
    sys.exit(exit_code)


def cmd_install():
    print("📥 安装依赖...")
    os.chdir(os.path.dirname(__file__))
    os.system("python -m pip install -r requirements.txt")
    print("✅ 安装完成")


def main():
    args = sys.argv[1:]
    cmds = {
        "api": cmd_api,
        "test": cmd_test,
        "install": cmd_install,
    }
    if not args:
        cmd_api()
        return

    cmd = args[0]
    if cmd in cmds:
        cmds[cmd]()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
