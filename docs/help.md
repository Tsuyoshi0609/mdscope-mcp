# 困ったとき

構成（A〜D）と「サーバー PC」の意味は [setup.md](setup.md) §0。

## 新しいツールが呼ばれない／更新したのに前の動きのまま

MCP サーバーは **`claude` / `codex` のセッション開始時に起動され、ツールの一覧もそのとき読まれる**。
`git pull` で更新しても、動いているセッションには反映されない（軌道を頼んだのに 1 フレームだけ返ってくる、など）。
`claude` / `codex` を終了して起動し直す。

## 「ファイルが見つからない」と言われる

パスはサーバー PC 上のもの。絶対パスで頼むか、`list_files` で探させる。
`MDSCOPE_ALLOWED_ROOTS` の外にあるファイルは「outside MDSCOPE_ALLOWED_ROOTS」で拒否される。
[setup.md](setup.md) §1 の環境変数を直して、§2 / §3 の登録をやり直す。

## Codex でビューアが出るまでに時間がかかる

- **ツール名を添える**: 「mdscope の `view_trajectory` で …… を再生して」のように頼む。添えないと、モデルが
  ツールを探し回って数分かかることがある
- **承認ダイアログ**: Codex はツールを呼ぶたびに実行の許可を求めることがある。何度も聞かれるなら、
  ダイアログで常に許可を選ぶ
- **大きなデータ**: 会話内のビューアは、大きな系（数 MB）のデータを少しずつ読み込む。
  「loading structure… N%」と出ている間は待つ

## デスクトップアプリ内で結果のリンクを開くと空白ページになる

ChatGPT / Codex デスクトップ内のブラウザは `localhost` の URL に届かない。会話内に出たビューアを使う。
HTML ファイルを直接見たいときは、サーバー PC のブラウザで開く。

## ビューアに "viewer error" と出る

- "WebGL is not available": そのブラウザ・ウィンドウで WebGL（3D 描画）が使えない。別のブラウザで開く
- "parsed N atoms but the payload has M": mdscope-mcp を更新した後に、古いビューアが使われている。
  セッションを起動し直す

## 密度マップが構造からずれて見える／ほとんど見えない

結果の `atoms_inside_map`（CA 原子のうち等値面の内側にある割合）を見る。

- 0 に近く、しきい値を下げても構造を包まない: 構造とマップの座標系が違う。mdscope-mcp は位置合わせをしないので、
  マップに当てはめたモデル（EMDB のエントリに対応する PDB など）を使う
- しきい値を下げると包む: しきい値が高すぎた。ビューアの Level スライダーで下げるか、`level` を指定して頼む

## 予備経路: 生成した HTML を別のマシンのブラウザで見る

通常は不要（A・C は Artifact、B・D は会話内に出る）。Codex をターミナルだけで使うときなどに、
サーバー PC の HTML を HTTP で配り、手元のブラウザで開く。

```bash
# サーバー PC（tmux などで常駐させる）
conda activate mdscope
mdscope-mcp --serve                      # ~/.cache/mdscope を http://127.0.0.1:8765/ で配信
codex mcp add mdscope --env MDSCOPE_VIEW_URL="http://localhost:18765" \
  --env MDSCOPE_ALLOWED_ROOTS="$HOME:/path/to/data" -- "$(which mdscope-mcp)"   # 結果に URL が付く
# 手元の PC: ~/.ssh/config のサーバー PC のエントリに 1 行足す。ssh で入っている間だけ見える
#   LocalForward 18765 127.0.0.1:8765
```

手元側のポートを 18765 にするのは、Mac では 8765 を別のアプリが使っていることがあるため
（転送が張れていなくても「何かが見える」ので気づきにくい）。LAN に直接公開（`--host 0.0.0.0`）は、
手元から届かないネットワークが多いので使わない。
