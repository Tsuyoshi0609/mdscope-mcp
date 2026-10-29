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

`~/.codex/config.toml` に追記:

```toml
[mcp_servers.mdscope]
command = "/home/<you>/.local/bin/mdscope-mcp"
env = { MDSCOPE_ALLOWED_ROOTS = "/home/<you>:/data3/<you>" }
```

## 5. サンプルデータで確認する

[example/README.md](../example/README.md) の手順で ALA2 の軌道を `example/` に置き、
Claude Code で「`example/alanine-dipeptide-nowater.pdb` を見せて」と頼む。

## 開発用

```bash
conda activate mdscope
pytest
ruff check src tests
```
