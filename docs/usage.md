# 使い方

セットアップと 4 つの使い方（A〜D）は [setup.md](setup.md)。ここでは頼み方と、ツールの引数。

## 構造ファイルを見る

> `example/alanine-dipeptide-nowater.pdb` を見せて

裏では `view_structure(topology=...)` が呼ばれ、自己完結の HTML（3Dmol.js 同梱、約 0.6 MB + 座標）が
サーバー PC の `~/.cache/mdscope/view_<hash>.html` に書かれる。見え方は使い方による:

- **Claude Code（A・C）**: HTML が Artifact として公開され、リンクが返る。ブラウザ・スマホで開く
- **Codex + ChatGPT デスクトップ（B・D）**: 結果が **会話内にそのまま 3D ビューア**として描画される
  （MCP Apps。サーバーが `ui://mdscope/viewer/v5.html` を UI リソースとして公開し、ツールに関連付けている）。
  右上の ⤢ で全画面

どちらでも、HTML ファイルをサーバー PC のブラウザで直接開けば同じものが見える。
マウス / 指で回転・ズーム。表現はビューアの中で変えられる（[表現を変える](#表現を変える)）。

Codex では「mdscope の `view_structure` で …… を見せて」のようにツール名を添えると速い（[help.md](help.md)）。

## 軌道を見る

> `example/alanine-dipeptide-nowater.pdb` と `example/alanine-dipeptide-0-250ns-nowater.xtc` を再生して見せて

`view_trajectory(topology=..., trajectory=...)` が呼ばれ、軌道全体から **等間隔に 50 フレーム**
（`max_frames`）を抜き、**水素を除いて**（`hydrogens=False`）1 つの HTML にする。ビューア下部の ▶ で再生、
スライダーで任意のフレーム、スペースキーで再生 / 停止、← → で 1 フレームずつ。
表示されるフレーム番号は元の軌道でのフレーム番号。

フレームは次の処理を経て埋め込まれる（`warnings` にも出る）:

- **周期境界の補正**（`pbc=True`）: 残基を箱の中で繋ぎ直し、連続する残基どうしを最小像で並べる。
  結合情報が無いファイル（PDB + XTC など）でも動く。箱の情報が無いファイルでは何もしない
- **重心を原点へ**: 全フレームで選択部分の重心を原点に置く（並進の漂いを消す）
- **重ね合わせ**（`align=True`）: 最初のフレームの CA 原子（3 個未満なら全原子）に回転で重ねる
- **int16 化**: 0.01 Å 単位の整数にして base64 で埋め込む。LLM には座標を渡さない

区間を指定するときは `start` / `stop` / `stride`（元のフレーム番号）。それでも `max_frames` を超えれば
等間隔に間引く。座標が `max_payload_mb`（既定 8 MB）を超える場合はフレーム数を自動で減らし、
1 フレームも入らなければ選択を絞るよう促すエラーになる（例: `name CA`）。

頼み方の例:

> 10 ns から 20 ns の間を 100 フレームで、`resname LIG` の周り 5 Å を sticks で再生して

## 表現を変える

> `example/adenylate_kinase.pdb` と `example/adenylate_kinase.dcd` を再生して。全体は cartoon、
> 残基 122〜159 を chain 色の surface、30〜59 を sticks で重ねて、1 番と 214 番にラベルを付けて

全体の表現（`style` / `color`）に、部分選択ごとの表現（`layers`）を上から重ねる。

```
layers=[{"selection": "resid 122:159", "style": "surface", "color": "chain"},
        {"selection": "resid 30:59",   "style": "sticks"}],
labels="resid 1 or resid 214"
```

- `layers` の各要素は `selection`（MDAnalysis の選択文字列）・`style`（既定 `sticks`）・`color`（既定 `element`）。
  **`selection` の外の原子も含められる**（例: `resname SOL and around 3 resname LIG` で、リガンド近くの水を出す）。
  その原子は層としてだけ描かれ、全体の表現には加わらない
- `labels` は選択に含まれる残基に「残基名+番号（:鎖）」を付ける。CA があれば CA の位置。最大 200 残基
- 軌道では、`around` など距離で決める層の原子は**最初のフレームで固定**する（フレームごとに選び直さない）

ビューアの中でできること:

| 操作 | 場所 |
|---|---|
| 全体の表現と配色を変える | 上段の Style / Color |
| 層の表示・非表示、表現・配色の変更、削除 | 2 段目の各層（チェックボックス・メニュー・✕） |
| 層を足す | 2 段目の入力欄に `10-20, 45`（残基番号）、`A:30-40`（鎖:範囲）、`LIG`（残基名）を入れて Add layer |
| 残基にラベルを付ける / 外す | 原子をクリック。Clear labels で全部消す |
| ライト / ダーク | 上段の ◐ |

ビューア内で足せる層は残基番号・鎖・残基名だけで指定する（ブラウザ側に MDAnalysis が無いため）。
`around` などはツールの `layers` で頼む。ビューアでの変更は保存されず、開き直すとツールで指定した状態に戻る。

## ツール

| ツール | 主な引数 | 返すもの |
|---|---|---|
| `list_files` | `path`, `pattern="*"` | サーバー PC のファイル一覧。パスが分からないとき、見つからないと言われたときに使う |
| `load_system` | `topology`, `trajectory`（任意、複数可） | `system_id` と組成（chain・残基範囲・配列、リガンド候補、水・イオン数、フレーム数） |
| `describe_system` | `system_id` | 同上（選択文字列を書くための情報源） |
| `view_structure` | `system_id` か `topology`（+ `trajectory`）, `selection="protein"`, `frame=0`, `style`, `color`, `layers`, `labels`, `highlight`, `title`, `pbc` | 1 フレームのビューア。HTML のパス（`artifacts[0].path`）と配信 URL（`url`、設定時のみ）、表示内容の要約、`warnings` |
| `view_trajectory` | 同上 + `start`, `stop`, `stride`, `max_frames=50`, `align=True`, `hydrogens=False`, `max_payload_mb=8` | スライダー・再生付きのビューア。要約に `n_frames`, `time_span_ps` |
| `get_view_payload` | `view_id`, `offset` | ビューア用データ（PDB 文字列・座標・表示設定）の JSON を 24000 文字ずつ。**ビューアが呼ぶ**もので、人が呼ぶ必要はない |
| `mdscope_info` | — | バージョン、許可ルート、キャッシュ先、読込済みの系。セットアップの診断用 |

### `view_structure` / `view_trajectory` の共通引数

| 引数 | 値 | 既定 | 備考 |
|---|---|---|---|
| `selection` | MDAnalysis の選択文字列（`protein`, `segid A and resid 10:50`, `resname LIG`, `around 5 resname LIG`） | `protein` | `protein` のときだけ、水・イオン以外の非タンパク質残基（リガンド）を自動で含める |
| `frame` | 0 始まりのフレーム番号（`view_structure` のみ） | `0` | 軌道を読んでいれば任意のフレームを 1 枚表示できる |
| `style` | `cartoon` / `sticks` / `spheres` / `lines` / `surface` | `cartoon` | cartoon と surface のとき、リガンドは sticks で重ねる。二次構造が 1 つも無い系（ペプチドなど）は sticks に落ちる。surface は cartoon の上に半透明の分子表面（SES） |
| `color` | `ss`（二次構造）/ `chain` / `rainbow`（N→C）/ `element` | `ss` | — |
| `highlight` | 選択文字列 | なし | マゼンタの sticks で上書き表示 |
| `layers` | `{selection, style, color}` のリスト | なし | 上の [表現を変える](#表現を変える) |
| `labels` | 選択文字列 | なし | 選んだ残基にラベル |
| `pbc` | `true` / `false` | `view_structure` は軌道を読んだときだけ `true`、`view_trajectory` は `true` | 構造ファイル単体はファイルどおりの座標で表示する |


## 制限（2026-10-31 時点）

- 二次構造（cartoon の螺旋・シート）は最初のフレームで決めたものを全フレームに使う。
- 軌道の表面（surface）は再生中は消え、止めると今のフレームで作り直す（作るのに時間がかかるため）。
- 周期境界の補正は「残基が連続している」ことを前提にする。鎖が複数ある系では、鎖どうしの相対配置が
  最小像に寄せられる（複合体がバラバラに見えたら `pbc=false` で比べる）。
- 水・イオン・脂質は既定では表示しない（`selection` で明示すれば出る）。
- 描画は常にブラウザ側。再生が重いときは `selection` を絞る（例: `name CA`）か `max_frames` を減らす。
  目安はサーバー側の実測とともに [mechanism.md](mechanism.md)。
- 時刻の表示はファイルの時刻情報をそのまま使う。DCD など単位が曖昧な形式では ps の値が合わないことがある
  （フレーム番号は常に正しい）。
