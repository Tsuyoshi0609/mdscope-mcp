# mdscope-mcp

**手元のチャットから「この軌道を見せて」で、計算機上の MD 軌道を回して確認する。**

mdscope-mcp は、タンパク質の構造ファイルと MD 軌道を Claude Code / Codex から
インタラクティブに表示するための MCP サーバーです。データがあるマシンで動かし、
3Dmol.js を同梱した自己完結の HTML を書き出します。Claude Code はそれを Artifact として
公開するので、ブラウザやスマホ（リモートコントロール）からそのまま回せます。

状態: 開発中（v0.0.1）。まだ動きません。

## できること（予定）

| 優先 | 機能 | 状態 |
|---|---|---|
| 1 | 構造ファイル（`.pdb` / `.cif` / `.gro`）を cartoon で表示 | 未 |
| 2 | MD 軌道（GROMACS / AMBER / DCD）をフレーム再生 | 未 |
| 3 | 表現の変更（sticks / spheres / surface、配色、ハイライト） | 未 |
| 4 | 密度マップ（`.mrc` / `.map`）の等値面 | 未 |

解析（RMSD など）やシミュレーションの実行は対象外です。

## 使い方

- セットアップ: [docs/setup.md](docs/setup.md)
- 使い方: [docs/usage.md](docs/usage.md)
- 困ったとき: [docs/help.md](docs/help.md)
- サンプルデータの取得: [example/README.md](example/README.md)

## 注意

Claude Code の Artifact 経由で表示すると、表示に使う座標データ（既定でタンパク質の
重原子のみ、数 MB 以下）が claude.ai にアップロードされます。外に出せないデータは、
生成された HTML ファイルをローカルのブラウザで開いてください。

## ライセンス

MIT
