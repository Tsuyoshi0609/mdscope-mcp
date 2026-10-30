# mdscope-mcp

**手元のチャットから「この軌道を見せて」で、計算機上の MD 軌道を回して確認する。**

mdscope-mcp は、タンパク質の構造ファイルと MD 軌道を Claude Code / Codex から
インタラクティブに表示するための MCP サーバーです。データがあるマシンで動かし、
3Dmol.js を同梱した自己完結の HTML を書き出します。Claude Code はそれを Artifact として
公開するので、ブラウザやスマホ（リモートコントロール）からそのまま回せます。

状態: v0.1.0。ChatGPT デスクトップと Codex デスクトップでは会話内に 3D ビューアが描画されます（MCP Apps）。

## できること

| 優先 | 機能 | 状態 |
|---|---|---|
| 1 | 構造ファイル（`.pdb` / `.gro` / `.prmtop` …）を cartoon で表示 | 動作確認済み（Claude Code / Codex / ChatGPT デスクトップ） |
| 2 | MD 軌道（GROMACS / AMBER / DCD）をフレーム再生。周期境界の補正と重ね合わせ付き | 動作確認済み（Claude Code / Codex） |
| 3 | 表現の変更（sticks / spheres / surface、配色、ハイライト） | 一部（sticks / spheres / lines、4 配色、ハイライト） |
| 4 | 密度マップ（`.mrc` / `.map`）の等値面 | 未 |

解析（RMSD など）やシミュレーションの実行は対象外です。

## 使い方

- セットアップ: [docs/setup.md](docs/setup.md)
- 使い方: [docs/usage.md](docs/usage.md)
- 仕組みと実測: [docs/mechanism.md](docs/mechanism.md)
- 困ったとき: [docs/help.md](docs/help.md)
- サンプルデータの取得: [example/README.md](example/README.md)

## 注意

Claude Code の Artifact 経由で表示すると、表示に使う座標データ（既定でタンパク質の
重原子のみ、数 MB 以下）が claude.ai にアップロードされます。外に出せないデータは、
生成された HTML ファイルをローカルのブラウザで開いてください。

## ライセンス

MIT
