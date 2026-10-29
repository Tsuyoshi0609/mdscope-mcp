# 困ったとき

## `mdscope-mcp --serve` の URL がブラウザで開けない

floyd の LAN アドレス（`192.168.1.102`）には、手元の Mac から HTTP が届かない（`curl` が
`Host is down` / タイムアウト。SSH だけが通る経路）。`--host 0.0.0.0` で公開しても見えない。
**SSH ポート転送を使う**（[setup.md](setup.md) §4）。`MDSCOPE_VIEW_URL` は `http://localhost:8765`。
