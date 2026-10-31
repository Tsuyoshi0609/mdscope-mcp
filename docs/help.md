# 困ったとき

構成（A〜D）とサーバー PC の意味は [setup.md](setup.md) §0。

## 新しいツール（`view_trajectory` など）が呼ばれない／直したはずの挙動のまま

MCP サーバーは **`claude` / `codex` のセッション開始時に起動され、ツール一覧もそのとき取得される**。
サーバーのコードを更新しても、動いているセッションには反映されない（軌道を頼んでも
`view_structure` で 1 フレームだけ返ってくる、など）。`claude` / `codex` を終了して起動し直す。
どのコードで動いているかは、サーバー PC で `ps -o lstart,cmd -C mdscope-mcp` の起動時刻と
`src/mdscope/server.py` の更新時刻を比べれば分かる。

## 「ファイルが見つからない」と言われる

パスはサーバー PC 上のもの。`list_files` ツールで探させるか、絶対パスで頼む。
`MDSCOPE_ALLOWED_ROOTS` の外にあるファイルは「outside MDSCOPE_ALLOWED_ROOTS」で拒否される
（[setup.md](setup.md) §1 の環境変数を直して登録し直す）。

## Codex / ChatGPT でツールを呼ぶまでに時間がかかる

サーバーの起動は約 1.6 秒で、遅さの原因ではない。時間はモデル側の寄り道と承認待ちで使われる。

- **探し回る**: 「mdscope のツールが無い」と判断してプラグイン一覧やブラウザを探すことがある
  （初回に約 3 分かかった例がある）。「mdscope の `view_trajectory` で …… を再生して」のように**ツール名を添える**
- **下調べをする**: このリポジトリの中で `codex` を起動すると、`AGENTS.md` を読んだうえで動く。
  `AGENTS.md` には「表示だけの依頼ではファイルを読まず、パスの確認もせず、すぐ `view_*` を呼ぶ」と書いてある。
  ツール側の説明にも「パスを事前に確かめない」とある
- **ツールごとの承認**: Codex は MCP ツールを呼ぶたびに許可を求めることがある。1 回の表示で何度も聞かれるなら、
  承認ダイアログで常に許可を選ぶ。全ツールに読み取り専用の注釈（`readOnlyHint`）を付けてあるが、
  これで承認が省かれるかどうかは Codex 側の設定次第で、未確認

## デスクトップアプリ内で結果のリンクを開くと空白ページになる

ChatGPT / Codex デスクトップ内のブラウザは `localhost` の URL に届かない。会話内に描画された
ビューアを使う。HTML ファイルを直接見たいときは、サーバー PC のブラウザで開く。

## ビューアに "viewer error" / "coordinates would be misassigned" と出る

- "WebGL is not available": そのブラウザ・ウィンドウで WebGL が無効。別のブラウザで開く。
- "parsed N atoms but the payload has M": ビューアが読んだ原子数とペイロードが合わない。
  古い `ui://mdscope/viewer/...` がホストにキャッシュされている可能性が高い。セッションを起動し直す。
  （Codex は長いツール結果の両端 約 32 KB ずつだけをビューアに渡す。今のビューアはそれを検出して
  サーバーから取り直すので、v5 以降でこの表示が出るなら別の原因）

## 予備経路: 生成した HTML を別のマシンのブラウザで見る

通常は不要（A・C は Artifact、B・D は会話内描画）。Codex をターミナルだけで使うときなどに、
サーバー PC の HTML を HTTP で配り、手元のブラウザで開く。

```bash
# サーバー PC（tmux などで常駐）
conda activate mdscope
mdscope-mcp --serve                      # ~/.cache/mdscope を http://127.0.0.1:8765/ で配信
codex mcp add mdscope --env MDSCOPE_VIEW_URL="http://localhost:18765" \
  --env MDSCOPE_ALLOWED_ROOTS="$HOME:/data3/kawai" -- "$(which mdscope-mcp)"   # 結果に url が付く
# 手元の PC: ~/.ssh/config のサーバー PC のエントリに 1 行足し、ssh で入っている間だけ見える
#   LocalForward 18765 127.0.0.1:8765
```

手元側のポートを 18765 にするのは、Mac では 8765 を別のアプリが使っていることがあるため
（転送が張れていなくても「何かが見える」ので気づきにくい）。LAN に直接公開（`--host 0.0.0.0`）は、
手元から届かないネットワークが多いので使わない。
