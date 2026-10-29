# 使い方

セットアップは [setup.md](setup.md)。Claude Code に `mdscope` が登録されている前提。

## 構造ファイルを見る

Claude Code で頼むだけでよい:

> `example/alanine-dipeptide-nowater.pdb` を見せて

裏では `view_structure(topology=...)` が呼ばれ、自己完結の HTML（3Dmol.js 同梱、約 0.6 MB + 座標）が
`~/.cache/mdscope/view_<hash>.html` に書かれる。Claude Code はそれを Artifact として公開するので、
返ってきたリンクをブラウザ・スマホで開く。マウス / 指で回転・ズームできる。

Artifact を使わない（使えない）場合は、そのパスの HTML をブラウザで開けば同じものが見える。

### Codex から

`mdscope-mcp --serve` を立てて `MDSCOPE_VIEW_URL` を設定しておくと（[setup.md](setup.md) §4）、
結果の `artifacts[0].url`（例 `http://localhost:8765/view_<hash>.html`）が返るので、SSH ポート転送を張った
手元のブラウザで開く。Codex に頼むときは「見せて。URL を教えて」と言えばよい。
`http://localhost:8765/` を開けば生成済み HTML の一覧も見える。

## ツール

| ツール | 主な引数 | 返すもの |
|---|---|---|
| `load_system` | `topology`, `trajectory`（任意、複数可） | `system_id` と組成（chain・残基範囲・配列、リガンド候補、水・イオン数、フレーム数） |
| `describe_system` | `system_id` | 同上（選択文字列を書くための情報源） |
| `view_structure` | `system_id` か `topology`（+ `trajectory`）, `selection="protein"`, `frame=0`, `style`, `color`, `highlight`, `title` | HTML のパス（`artifacts[0].path`）と配信 URL（`url`、設定時のみ）、表示内容の要約、`warnings` |
| `mdscope_info` | — | バージョン、許可ルート、キャッシュ先、読込済みの系 |

### `view_structure` の引数

| 引数 | 値 | 既定 | 備考 |
|---|---|---|---|
| `selection` | MDAnalysis の選択文字列（`protein`, `segid A and resid 10:50`, `resname LIG`, `around 5 resname LIG`） | `protein` | `protein` のときだけ、水・イオン以外の非タンパク質残基（リガンド）を自動で含める |
| `frame` | 0 始まりのフレーム番号 | `0` | 軌道を読んでいれば任意のフレームを 1 枚表示できる |
| `style` | `cartoon` / `sticks` / `spheres` / `lines` | `cartoon` | cartoon のとき、リガンドは sticks で重ねる。二次構造が 1 つも無い系（ペプチドなど）は sticks に落ちる |
| `color` | `ss`（二次構造）/ `chain` / `rainbow`（N→C）/ `element` | `ss` | — |
| `highlight` | 選択文字列 | なし | マゼンタの sticks で上書き表示 |

HTML 内のメニューから `style` / `color` はあとから切り替えられる。

## 制限（2026-10-30 時点）

- 軌道の再生は未実装。`frame` で 1 枚を選ぶだけ。
- 水・イオン・脂質は既定では表示しない（`selection` で明示すれば出る）。
- 描画は常にブラウザ側。表示が重いときは `selection` を絞る（例: `protein and not name H*`）。
