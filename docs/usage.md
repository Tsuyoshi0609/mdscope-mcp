# 使い方

セットアップは [setup.md](setup.md)。Claude Code に `mdscope` が登録されている前提。

## 構造ファイルを見る

Claude Code で頼むだけでよい:

> `example/alanine-dipeptide-nowater.pdb` を見せて

裏では `view_structure(topology=...)` が呼ばれ、自己完結の HTML（3Dmol.js 同梱、約 0.6 MB + 座標）が
`~/.cache/mdscope/view_<hash>.html` に書かれる。Claude Code はそれを Artifact として公開するので、
返ってきたリンクをブラウザ・スマホで開く。マウス / 指で回転・ズームできる。

Artifact を使わない（使えない）場合は、そのパスの HTML をブラウザで開けば同じものが見える。

## 軌道を見る

> `example/alanine-dipeptide-nowater.pdb` と `example/alanine-dipeptide-0-250ns-nowater.xtc` を再生して見せて

`view_trajectory(topology=..., trajectory=...)` が呼ばれ、軌道全体から **等間隔に 50 フレーム**
（`max_frames`）を抜き、**水素を除いて**（`hydrogens=False`）1 つの HTML にする。ビューア下部の ▶ で再生、スライダーで任意のフレーム、
スペースキーで再生 / 停止、← → で 1 フレームずつ。表示されるフレーム番号は元の軌道でのフレーム番号。

フレームは次の処理を経て埋め込まれる（`warnings` にも出る）:

- **周期境界の補正**（`pbc=True`）: 残基を箱の中で繋ぎ直し、連続する残基どうしを最小像で並べる。
  結合情報が無いファイル（PDB + XTC など）でも動く。箱の情報が無いファイルでは何もしない
- **重心を原点へ**: 全フレームで選択部分の重心を原点に置く（並進の漂いを消す）
- **重ね合わせ**（`align=True`）: 最初のフレームの CA 原子（3 個未満なら全原子）に回転で重ねる
- **int16 化**: 0.01 Å 単位の整数にして base64 で埋め込む。LLM には座標を渡さない

区間を指定するときは `start` / `stop` / `stride`（元のフレーム番号）。それでも `max_frames` を超えれば
等間隔に間引く。座標が `max_payload_mb`（既定 8 MB）を超える場合はフレーム数を自動で減らし、
1 フレームも入らなければ選択を絞るよう促すエラーになる（例: `protein and not name H*`、`name CA`）。

### ChatGPT デスクトップ / Claude Desktop から（MCP Apps）

MCP Apps に対応したホストでは、`view_structure` / `view_trajectory` の結果が **会話内にそのまま 3D ビューアとして
描画**される（サーバーが `ui://mdscope/viewer/v3.html` を UI リソースとして公開し、ツールに関連付けている）。
ビューアの右上 ⤢ で全画面にできる。描画されない場合は Codex と同じく `url` / HTML パスで開く。

### Codex から

`mdscope-mcp --serve` を立てて `MDSCOPE_VIEW_URL` を設定しておくと（[setup.md](setup.md) §4）、
結果の `artifacts[0].url`（例 `http://localhost:18765/view_<hash>.html`）が返るので、SSH ポート転送を張った
手元のブラウザで開く。Codex に頼むときは「見せて。URL を教えて」と言えばよい。
`http://localhost:18765/` を開けば生成済み HTML の一覧も見える。

## ツール

| ツール | 主な引数 | 返すもの |
|---|---|---|
| `list_files` | `path`, `pattern="*"` | サーバー側（floyd）のファイル一覧。パスの確認用 |
| `load_system` | `topology`, `trajectory`（任意、複数可） | `system_id` と組成（chain・残基範囲・配列、リガンド候補、水・イオン数、フレーム数） |
| `describe_system` | `system_id` | 同上（選択文字列を書くための情報源） |
| `view_structure` | `system_id` か `topology`（+ `trajectory`）, `selection="protein"`, `frame=0`, `style`, `color`, `highlight`, `title`, `pbc` | 1 フレームのビューア。HTML のパス（`artifacts[0].path`）と配信 URL（`url`、設定時のみ）、表示内容の要約、`warnings` |
| `view_trajectory` | 同上 + `start`, `stop`, `stride`, `max_frames=50`, `align=True`, `hydrogens=False`, `max_payload_mb=8` | スライダー・再生付きのビューア。要約に `n_frames`, `time_span_ps` |
| `get_view_payload` | `view_id` | ビューア用データ（PDB 文字列・座標・表示設定）。**ビューアが呼ぶ**もので、人が呼ぶ必要はない |
| `mdscope_info` | — | バージョン、許可ルート、キャッシュ先、読込済みの系 |

### `view_structure` / `view_trajectory` の共通引数

| 引数 | 値 | 既定 | 備考 |
|---|---|---|---|
| `selection` | MDAnalysis の選択文字列（`protein`, `segid A and resid 10:50`, `resname LIG`, `around 5 resname LIG`） | `protein` | `protein` のときだけ、水・イオン以外の非タンパク質残基（リガンド）を自動で含める |
| `frame` | 0 始まりのフレーム番号（`view_structure` のみ） | `0` | 軌道を読んでいれば任意のフレームを 1 枚表示できる |
| `style` | `cartoon` / `sticks` / `spheres` / `lines` | `cartoon` | cartoon のとき、リガンドは sticks で重ねる。二次構造が 1 つも無い系（ペプチドなど）は sticks に落ちる |
| `color` | `ss`（二次構造）/ `chain` / `rainbow`（N→C）/ `element` | `ss` | — |
| `highlight` | 選択文字列 | なし | マゼンタの sticks で上書き表示 |
| `pbc` | `true` / `false` | `view_structure` は軌道を読んだときだけ `true`、`view_trajectory` は `true` | 構造ファイル単体はファイルどおりの座標で表示する |

HTML 内のメニューから `style` / `color` はあとから切り替えられる。

## 制限（2026-10-30 時点）

- 二次構造（cartoon の螺旋・シート）は最初のフレームで決めたものを全フレームに使う。
- 周期境界の補正は「残基が連続している」ことを前提にする。鎖が複数ある系では、鎖どうしの相対配置が
  最小像に寄せられる（複合体がバラバラに見えたら `pbc=false` で比べる）。
- 水・イオン・脂質は既定では表示しない（`selection` で明示すれば出る）。
- 描画は常にブラウザ側。再生が重いときは `selection` を絞る（例: `name CA`）か `max_frames` を減らす。
  目安はサーバー側の実測とともに [mechanism.md](mechanism.md)。
- 時刻の表示はファイルの時刻情報をそのまま使う。DCD など単位が曖昧な形式では ps の値が合わないことがある
  （フレーム番号は常に正しい）。
