# 困ったとき

## `mdscope-mcp --serve` の URL がブラウザで開けない

floyd の LAN アドレス（`192.168.1.102`）には、手元の Mac から HTTP も SSH も届かない
（`No route to host`。floyd へは Cloudflare 経由の `ssh floyd-remote` だけが通る）。
`--host 0.0.0.0` で公開しても見えない。**SSH ポート転送を使う**（[setup.md](setup.md) §4）。

## `http://localhost:8765/` を開くと別のアプリの画面が出る

Mac 側で 8765 番を別のアプリ（Claude 系のローカルサービス）が使っていた。転送が張れていなくても
「何かが見える」ので気づきにくい。**手元側のポートは 18765** にし、`MDSCOPE_VIEW_URL` も
`http://localhost:18765` にする。転送が本当に floyd に届いているかは、floyd 側の `--serve` の
ログ（stderr）にアクセス行が出るかで確かめる。

## ChatGPT デスクトップで「ファイルが見つからない」と言われる

パスは floyd 上のものだが、モデルが Mac 側（Codex の作業ディレクトリ）を探している。
「mdscope の `view_structure` で …… を見せて」とツール名を添える。`list_files` で floyd 側を探させてもよい。
