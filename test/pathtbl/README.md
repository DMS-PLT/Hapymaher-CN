# test/pathtbl — 界面图回写排查留下的脚本

2026-10-06 查「界面图怎么塞回游戏」时写的一次性工具，留着备查。
结论写在《汉化实施交接文档.md》§3.10，工具用法见《工具总览.md》§7。

日常用不到这些；真要再动 `start.ps3` 路径表或 pb3 层，从这里挑。

| 文件 | 干嘛的 |
|---|---|
| `dump_paths.py` | 解 `start.ps3` 后把里面的字符串表打出来（路径表就藏在其中） |
| `scan_exe.py` | 在 `cmvs32.exe` 里搜 `.cpz` / `.pb3` / `pack` 之类的串 |
| `dump_region.py` | dump exe 某一段的可打印串（ASCII + SJIS） |
| `disasm.py` | 反汇编 exe 指定 VA 附近（需要 `capstone` + `pefile`） |
| `setup_chip_test.py` | 改 `start.ps3` 的 chip 路径（`prepare` / `pathonly` / `revert`） |
| `install_formA.py` | 把 `UI界面/chip` 铺成 Form A 到游戏目录（功能已并入 `build_encrypted.py`） |
| `keystream.py` / `cipher_test.py` | 反推封包加密密钥流的尝试 —— **没成功，也没必要**（散装目录这条路不用碰它） |
| `shot.ps1` / `grab_window.ps1` | 截屏存证用 |

跑 `disasm.py` 要带依赖：

```bash
uv run --with capstone --with pefile python disasm.py 0x42FFA8 0x140 0x30
```
