#!/usr/bin/env bash
# 出片封装 —— 实际逻辑都在 render.py (管道直连, 无中间文件, 全平台通用)。
cd "$(dirname "$0")"
exec python render.py "$@"
