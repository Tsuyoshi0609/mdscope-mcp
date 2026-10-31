# mdscope-mcp

**チャットで「この軌道を見せて」と頼むだけで、計算機上の構造・MD 軌道・密度マップを 3D で回して確かめる。**

mdscope-mcp は、Claude Code と Codex から使う MCP サーバーです。データのあるマシンで動き、
回転・ズームできる 3D ビューアを返します。

- **Claude Code**: ビューアが Artifact として開く。ブラウザやスマホ（リモートコントロール）から見られる
- **Codex**: ChatGPT デスクトップの会話の中に、そのままビューアが出る

## できること

| | 内容 |
|---|---|
| 構造を見る | `.pdb` / `.gro` / `.prmtop` / `.tpr` など（MDAnalysis が読める形式）を cartoon で表示 |
| 軌道を再生する | GROMACS（`.xtc` / `.trr`）、AMBER（`.nc`）、DCD などをスライダーと ▶ で再生。分子が周期境界で千切れないよう繋ぎ直し、最初のフレームに重ねて、動きだけを見せる |
| 表現を変える | cartoon / sticks / spheres / lines / surface、配色（二次構造・鎖・N→C・元素）。部分ごとに表現を重ねる（例: リガンドの周り 5 Å を sticks）、残基にラベル。ビューアの中でも切り替えられる |
| 密度マップを重ねる | クライオ電顕などのマップ（`.mrc` / `.map`）を等値面で構造に重ね、しきい値をスライダーで動かす |

解析（RMSD など）やシミュレーションの実行は対象外です。

頼み方の例:

> `traj/protein.gro` と `traj/md.xtc` を再生して見せて
>
> 全体は cartoon、`resname LIG` の周り 5 Å を sticks で、10〜20 番にラベルを付けて
>
> `em/map.mrc` を `em/model.pdb` に重ねて見せて

## 使い方の組み合わせ

mdscope-mcp は **チャットのセッションを起動するマシン**（データがあるマシン）に入れます。
デスクトップアプリ側に入れるものはありません。

| 使い方 | セッションを起動する場所 | 見るアプリ | ビューア |
|---|---|---|---|
| A | リモート PC で `claude --remote-control <name>` | Claude デスクトップ | Artifact |
| B | リモート PC で `codex` | ChatGPT デスクトップ | 会話内に描画 |
| C | 手元の PC で `claude --remote-control <name>` | Claude デスクトップ | Artifact |
| D | 手元の PC で `codex` | ChatGPT デスクトップ | 会話内に描画 |

- セットアップ: [docs/setup.md](docs/setup.md)
- 頼み方とツールの引数: [docs/usage.md](docs/usage.md)
- 困ったとき: [docs/help.md](docs/help.md)
- サンプルデータの取得: [example/README.md](example/README.md)

## 注意

Claude Code の Artifact で表示すると、表示に使う座標データ（既定ではタンパク質の重原子、数 MB 以下）が
claude.ai にアップロードされます。外に出せないデータは、サーバー PC に書き出される HTML ファイル
（`~/.cache/mdscope/view_….html`、ネットワーク不要）をブラウザで直接開いてください。

## ライセンス

MIT
