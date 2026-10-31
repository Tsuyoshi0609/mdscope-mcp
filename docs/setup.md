# セットアップ

## 0. 構成を決める

mdscope-mcp は **チャットのセッションを起動するマシン**に入れる。そのマシン上の軌道を見る。
デスクトップアプリ（Claude / ChatGPT）は進捗を見て操作するだけで、**デスクトップアプリ側に入れるものは無い**。

| 使い方 | セッションを起動するマシンとコマンド | 見るアプリ | 3D ビューアの出方 |
|---|---|---|---|
| **A** | リモート PC で `claude --remote-control <session-name>` | Claude デスクトップ | Artifact のリンク |
| **B** | リモート PC で `codex` | ChatGPT デスクトップ | 会話内に描画（MCP Apps） |
| **C** | 手元の PC で `claude --remote-control <session-name>` | Claude デスクトップ | Artifact のリンク |
| **D** | 手元の PC で `codex` | ChatGPT デスクトップ | 会話内に描画（MCP Apps） |

以下、**「サーバー PC」= セッションを起動するマシン**（A・B ならリモート PC、C・D なら手元の PC）。
§1 はサーバー PC で 1 回、§2 は Claude Code を使うなら（A・C）、§3 は Codex を使うなら（B・D）。
コマンドはすべて **サーバー PC のターミナル**で打つ。デスクトップアプリ側の操作は §4。

## 1. サーバー PC に入れる

前提: conda か mamba（[Miniforge](https://github.com/conda-forge/miniforge) で可）、git、
Claude Code（`claude`）または Codex（`codex`）が入っていること。

```bash
git clone https://github.com/Tsuyoshi0609/mdscope-mcp.git
cd mdscope-mcp
mamba env create -f environment.yml     # conda でも可。環境名は mdscope
conda activate mdscope
mdscope-mcp --check                     # version, allowed_roots, cache_dir が表示されれば OK
which mdscope-mcp                       # ← この絶対パスを §2 / §3 で使う
```

`environment.yml` で、構造・軌道の読み込み（MDAnalysis、AMBER 軌道用の netCDF4）、密度マップの読み込み（mrcfile）、
MCP サーバー本体がまとめて入る。

### 環境変数

| 変数 | 既定 | 意味 |
|---|---|---|
| `MDSCOPE_ALLOWED_ROOTS` | `$HOME` | 読んでよいディレクトリ。`:` 区切り。**ここ以外のパスは拒否される** |
| `MDSCOPE_CACHE_DIR` | `~/.cache/mdscope` | 生成した HTML とログの置き場 |

データが `$HOME` の外にあるなら `MDSCOPE_ALLOWED_ROOTS` に追加する（例: `$HOME:/path/to/data`。以下の例も同じ）。
§2 / §3 の `-e` / `--env` で渡す。

## 2. Claude Code に登録する（A・C）

```bash
conda activate mdscope
claude mcp add --scope user mdscope \
  -e MDSCOPE_ALLOWED_ROOTS="$HOME:/path/to/data" \
  -- "$(which mdscope-mcp)"
claude mcp list        # mdscope: ... - ✔ Connected と出れば OK
```

`--scope user` なので、どのディレクトリで `claude` を起動しても使える。
外す: `claude mcp remove --scope user mdscope`。

## 3. Codex に登録する（B・D）

```bash
conda activate mdscope
codex mcp add mdscope \
  --env MDSCOPE_ALLOWED_ROOTS="$HOME:/path/to/data" \
  -- "$(which mdscope-mcp)"
codex mcp list         # mdscope が enabled で出れば OK
```

`~/.codex/config.toml` に `[mcp_servers.mdscope]` が書かれる。外す: `codex mcp remove mdscope`。

## 4. 使う

サンプルデータは [example/README.md](../example/README.md) の手順でサーバー PC の `example/` に置く。
以下の依頼文はそのファイルを使う。パスは **サーバー PC 上のパス**で書く。

### A・C: Claude Code + Claude デスクトップ

1. サーバー PC のターミナルで、軌道のあるディレクトリに移動し
   ```bash
   claude --remote-control mdscope-test      # mdscope-test はセッション名（任意）
   ```
2. 手元の PC の Claude デスクトップに、セッション `mdscope-test` が現れるので開く。
3. そこから頼む:
   > `example/alanine-dipeptide-nowater.pdb` と `example/alanine-dipeptide-0-250ns-nowater.xtc` を再生して見せて
4. Artifact のリンクが返る。開くと 3D ビューアが出て、▶ で再生、スライダーでフレーム移動ができる。
   構造 1 つだけなら「`example/alanine-dipeptide-nowater.pdb` を見せて」。
   表現の変え方や密度マップの重ね方は [usage.md](usage.md)。

Claude Code は HTML を Artifact として claude.ai に公開する。表示に使う座標（既定ではタンパク質の
重原子、数 MB 以下）が claude.ai に上がることに注意（[README](../README.md)）。

### B・D: Codex + ChatGPT デスクトップ

1. 手元の PC の ChatGPT デスクトップで、設定の **リモートコントロール**をオンにしておく。
2. サーバー PC のターミナルで、軌道のあるディレクトリに移動し
   ```bash
   codex
   ```
3. ChatGPT デスクトップの Codex 画面にそのセッションが現れるので開く。
4. そこから頼む。**ツール名を添える**と迷わず速い:
   > mdscope の `view_trajectory` で `example/alanine-dipeptide-nowater.pdb` と
   > `example/alanine-dipeptide-0-250ns-nowater.xtc` を再生して見せて
5. ツールの実行許可を求められたら許可する。会話内に 3D ビューアが描画され、▶ で再生できる。

結果に `HTML: ~/.cache/mdscope/view_….html` も付く。会話内に描画されないときはそのファイルを
サーバー PC のブラウザで開く（別のマシンから見たいときは [help.md](help.md)）。

## 5. サーバーのコードを更新したとき

MCP サーバーは **セッション開始時に起動される**。`git pull` などで更新したら、`claude` / `codex` を
終了して起動し直す（[help.md](help.md)）。
