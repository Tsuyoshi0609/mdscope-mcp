# セットアップ

サーバーは **データがあるマシン**（Claude Code を動かすマシン）に入れる。

## 1. conda 環境を作る

```bash
git clone https://github.com/Tsuyoshi0609/mdscope-mcp.git
cd mdscope-mcp
mamba env create -f environment.yml     # conda でも可。環境名は mdscope
conda activate mdscope
mdscope-mcp --check                     # バージョン・許可ルート・キャッシュ先が stderr に出れば OK
```

`environment.yml` には MDAnalysis、netCDF4（AMBER 軌道）、mrcfile（密度マップ）、fastmcp と、
このリポジトリ自身（`pip install -e .`）が含まれる。

PNG スナップショットも欲しい場合だけ、PyMOL を追加する（無くても表示はできる）:

```bash
mamba install -n mdscope -c conda-forge pymol-open-source
```

## 2. 環境変数

| 変数 | 既定 | 意味 |
|---|---|---|
| `MDSCOPE_ALLOWED_ROOTS` | `$HOME` | 読んでよいディレクトリ。`:` 区切り。**ここ以外のパスは拒否される** |
| `MDSCOPE_CACHE_DIR` | `~/.cache/mdscope` | 生成した HTML / PNG とログの置き場 |
| `MDSCOPE_VIEW_URL` | なし | `mdscope-mcp --serve` の URL（例 `http://192.168.1.102:8765`）。設定すると結果に `url` が付く（Codex 用、§4） |

データが `$HOME` の外にあるなら必ず設定する（例: `/data3/kawai`）。

## 3. Claude Code に登録する

```bash
claude mcp add --scope user mdscope \
  -e MDSCOPE_ALLOWED_ROOTS="$HOME:/data3/kawai" \
  -- conda run -n mdscope --no-capture-output mdscope-mcp
```

`claude mcp list` で `mdscope` が `connected` になれば完了。

`conda run` が遅い・不安定な場合は、環境の Python を直接指すラッパーを使う:

```bash
cat > ~/.local/bin/mdscope-mcp <<'EOF'
#!/bin/sh
exec "$HOME/.conda/envs/mdscope/bin/mdscope-mcp" "$@"
EOF
chmod +x ~/.local/bin/mdscope-mcp
claude mcp add --scope user mdscope -e MDSCOPE_ALLOWED_ROOTS="$HOME:/data3/kawai" -- ~/.local/bin/mdscope-mcp
```

## 4. Codex に登録する

Codex には Artifact に相当する表示手段が無いので、生成した HTML を **HTTP で配信**して
ブラウザで開く。2 段階。

**(a) 配信サーバーを立てておく**（tmux などで常駐させる）:

```bash
conda activate mdscope
mdscope-mcp --serve --host 0.0.0.0 --port 8765    # ~/.cache/mdscope を配信
```

`--host 0.0.0.0` は同じ LAN の端末から `http://<floyd の IP>:8765/` で開ける（他のユーザーにも見える）。
LAN に出したくなければ既定の `127.0.0.1` のまま起動し、手元で
`ssh -L 8765:127.0.0.1:8765 floyd` を張って `http://localhost:8765/` で開く。

**(b) MCP サーバーを登録する**。`MDSCOPE_VIEW_URL` にブラウザから見た配信 URL を入れると、
`view_structure` の結果に `url` が付く:

```bash
codex mcp add mdscope \
  --env MDSCOPE_ALLOWED_ROOTS="$HOME:/data3/kawai" \
  --env MDSCOPE_VIEW_URL="http://192.168.1.102:8765" \
  -- "$HOME/.conda/envs/mdscope/bin/mdscope-mcp"
codex mcp list    # mdscope が出れば OK
```

（`~/.codex/config.toml` に `[mcp_servers.mdscope]` が書かれる。）

## 5. サンプルデータで確認する

[example/README.md](../example/README.md) の手順で ALA2 の軌道を `example/` に置き、
Claude Code で「`example/alanine-dipeptide-nowater.pdb` を見せて」と頼む。

## 開発用

```bash
conda activate mdscope
pytest
ruff check src tests
```
