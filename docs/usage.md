# 使い方

セットアップと 4 つの使い方（A〜D）は [setup.md](setup.md)。ここでは頼み方、ビューアの操作、ツールの引数。
例のファイルは [example/README.md](../example/README.md) の手順で取得できる。パスは**サーバー PC 上のパス**で書く。

## 構造ファイルを見る

> `example/alanine-dipeptide-nowater.pdb` を見せて

`view_structure` が呼ばれ、3D ビューアが返る。

- **Claude Code（A・C）**: Artifact のリンクが返る。ブラウザ・スマホで開く
- **Codex + ChatGPT デスクトップ（B・D）**: 会話の中にビューアが出る。右上の ⤢ で全画面

どちらの場合も、同じビューアが HTML ファイル（サーバー PC の `~/.cache/mdscope/view_….html`）として残る。
ネットワーク無しでも、そのファイルをブラウザで開けば見られる。

Codex では「mdscope の `view_structure` で …… を見せて」のようにツール名を添えると速い。

## 軌道を見る

> `example/alanine-dipeptide-nowater.pdb` と `example/alanine-dipeptide-0-250ns-nowater.xtc` を再生して見せて

`view_trajectory` が呼ばれる。軌道全体から**等間隔に 50 フレーム**（`max_frames`）を抜き、**水素を除いて**表示する。

| 操作 | 方法 |
|---|---|
| 再生 / 停止 | 下段の ▶、またはスペースキー |
| フレームを選ぶ | スライダー。← → で 1 フレームずつ |
| 速さ | Speed（2〜30 fps） |

表示されるフレーム番号は元の軌道でのフレーム番号。表示の前に、次の処理をする（結果の `warnings` にも出る）:

- **周期境界の補正**（`pbc=True`）: 箱の境界で千切れた分子を繋ぎ直す。結合情報が無いファイル（PDB + XTC など）でも効く。
  箱の情報が無いファイルでは何もしない
- **中心合わせ**: 全フレームで、表示する部分の重心を画面の中心に置く
- **重ね合わせ**（`align=True`）: 各フレームを、最初のフレームの CA 原子に回転で重ねる（全体の回転を消して、動きだけを見せる）

区間を指定するときは `start` / `stop` / `stride`（元のフレーム番号）。それでも `max_frames` を超えれば等間隔に間引く。
大きな系でデータが `max_payload_mb`（既定 8 MB）を超えるときはフレーム数を自動で減らし、1 フレームも入らなければ
選択を絞るよう促すエラーになる（例: `name CA`）。

> 10 ns から 20 ns の間を 100 フレームで、`resname LIG` の周り 5 Å を sticks で再生して

## 表現を変える

> `example/adenylate_kinase.pdb` と `example/adenylate_kinase.dcd` を再生して。全体は cartoon、
> 残基 122〜159 を chain 色の surface、30〜59 を sticks で重ねて、1 番と 214 番にラベルを付けて

全体の表現（`style` / `color`）の上に、部分ごとの表現（`layers`）を重ねる。上の依頼は次の引数になる:

```
layers=[{"selection": "resid 122:159", "style": "surface", "color": "chain"},
        {"selection": "resid 30:59",   "style": "sticks"}],
labels="resid 1 or resid 214"
```

- `layers` の各要素は `selection`（MDAnalysis の選択文字列）・`style`（既定 `sticks`）・`color`（既定 `element`）
- 層には**全体の `selection` の外の原子も入れられる**（例: `resname SOL and around 3 resname LIG` でリガンド近くの水）。
  その原子は層としてだけ描かれる
- `labels` は選んだ残基に「残基名+番号（:鎖）」を付ける。最大 200 残基
- 軌道では、`around` など距離で決める層の原子は**最初のフレームで決めて固定**する

ビューアの中でできること:

| 操作 | 場所 |
|---|---|
| 全体の表現と配色を変える | 上段の Style / Color |
| 層の表示・非表示、表現・配色の変更、削除 | 2 段目の各層（チェックボックス・メニュー・✕） |
| 層を足す | 2 段目の入力欄に `10-20, 45`（残基番号）、`A:30-40`（鎖:範囲）、`LIG`（残基名）を入れて Add layer |
| 残基にラベルを付ける / 外す | 原子をクリック。Clear labels で全部消す |
| 視点を戻す / ライト・ダーク | 上段の Reset view / ◐ |

ビューアの中で足せる層は、残基番号・鎖・残基名での指定だけ。`around` などの選択はチャットで頼む。
ビューアでの変更は保存されず、開き直すとツールで指定した状態に戻る。

## 密度マップを重ねる

> `example/EMD-1733.map` を `example/3C91.pdb` に重ねて見せて

`view_density` が呼ばれ、構造（既定は鎖ごとに色分けした cartoon）にマップの等値面を重ねる。
**構造とマップが同じ座標系にある**こと（マップに当てはめたモデルなど）が前提で、位置合わせはしない。

- **しきい値（`level`）**: 既定は、モデルの質量に見合う体積（1.21 Å³/Da）を囲む値。ビューアのスライダーで、
  マップの中央値から最大値まで動かせる。数値で頼むときはマップの値の単位で（例: `level=1.5`）
- **粗さ（`max_voxels=128`）**: マップはどの軸も 128 ボクセル以下になるまで平均して粗くする。
  EMD-1733（144³、1.37 Å）は 72³、2.7 Å になる。細部が要るなら値を上げる（ビューアのファイルが大きくなる）
- **重なりの確認**: 結果の `atoms_inside_map` は、CA 原子のうち等値面の内側にある割合。3C91 + EMD-1733 では 0.97。
  0.2 未満なら警告が出る（マップの位置がずれているか、しきい値が高すぎる）

ビューアの 3 段目で、マップの表示切替・しきい値（Level）・surface / mesh・不透明度を変えられる。

## ツール

| ツール | 主な引数 | 返すもの |
|---|---|---|
| `view_structure` | `topology`（+ `trajectory`）か `system_id`, `selection`, `frame=0`, `style`, `color`, `layers`, `labels`, `highlight`, `title`, `pbc` | 1 フレームのビューア |
| `view_trajectory` | 同上 + `start`, `stop`, `stride`, `max_frames=50`, `align=True`, `hydrogens=False`, `max_payload_mb=8` | 再生できるビューア。要約にフレーム数と時間幅 |
| `view_density` | `map`, `topology` か `system_id`, `level`, `max_voxels=128`, `selection`, `style`, `color="chain"`, `layers`, `labels`, `highlight` | 構造 + マップの等値面のビューア。要約に `map_level`, `atoms_inside_map` |
| `load_system` | `topology`, `trajectory`（任意、複数可） | `system_id` と組成（鎖・残基範囲・配列、リガンド候補、水・イオン数、フレーム数） |
| `describe_system` | `system_id` | 同上。選択文字列を組むときの情報源 |
| `list_files` | `path`, `pattern="*"` | サーバー PC のファイル一覧。パスが分からないときに使う |
| `mdscope_info` | — | バージョン、読んでよいディレクトリ、HTML の置き場。セットアップの確認用 |

どのビューアの結果にも、HTML ファイルのパス・表示内容の要約・`warnings` が付く。

### 表示の引数（3 つの `view_*` 共通）

| 引数 | 値 | 既定 | 備考 |
|---|---|---|---|
| `selection` | MDAnalysis の選択文字列（`protein`, `segid A and resid 10:50`, `resname LIG`, `around 5 resname LIG`） | `protein` | `protein` のときは、水・イオン以外の非タンパク質残基（リガンド）も自動で含める |
| `frame` | 0 始まりのフレーム番号（`view_structure` のみ） | `0` | 軌道を読めば任意のフレームを 1 枚表示できる |
| `style` | `cartoon` / `sticks` / `spheres` / `lines` / `surface` | `cartoon` | cartoon と surface ではリガンドを sticks で重ねる。二次構造が無い系（ペプチドなど）は sticks になる。surface は cartoon の上に半透明の分子表面 |
| `color` | `ss`（二次構造）/ `chain` / `rainbow`（N→C）/ `element` | `ss`（`view_density` は `chain`） | — |
| `highlight` | 選択文字列 | なし | マゼンタの sticks で上に描く |
| `layers` | `{selection, style, color}` のリスト | なし | [表現を変える](#表現を変える) |
| `labels` | 選択文字列 | なし | 選んだ残基にラベル |
| `pbc` | `true` / `false` | `view_structure` は軌道を読んだときだけ `true`、`view_trajectory` は `true` | 構造ファイル単体はファイルどおりの座標で表示する |

## 大きさの目安

サーバー側の処理時間と、ビューアのファイルの大きさ（2026-10・11 に計測）:

| データ | 表示 | 処理 | ファイル |
|---|---|---|---|
| 6662 原子 × 30003 フレーム（DCD 2.4 GB） | 水素なし 3363 原子 × 50 フレーム | 0.1 秒 | 2.2 MB |
| 同上 | 水素なし × 200 フレーム | 5.6 秒 | 6.2 MB |
| ALA2（22 原子 × 250000 フレーム） | 100 フレーム | 0.3 秒 | 0.6 MB |
| 3C91（46578 原子）+ EMD-1733（144³） | マップを 72³ に | 1.6 秒 | 4.9 MB |

ブラウザでの描画の重さは計測していない。再生が重いときは `selection` を絞る（例: `name CA`）か `max_frames` を減らす。

## 制限

- 二次構造（cartoon の螺旋・シート）は最初のフレームで決めたものを全フレームに使う。
- 軌道の表面（surface）は、再生中は消え、止めるとそのフレームで作り直す。
- 周期境界の補正は「残基が順に繋がっている」ことを前提にする。鎖が複数ある系では鎖どうしの配置が
  寄せられることがある（複合体がバラバラに見えたら `pbc=false` で比べる）。
- 水・イオン・脂質は既定では表示しない（`selection` や `layers` で指定すれば出る）。
- 密度マップは静止構造にだけ重ねられる（軌道とは重ねない）。格子が直交していないマップは読めない。
- 時刻の表示はファイルの時刻情報をそのまま使う。DCD など単位が曖昧な形式では ps の値が合わないことがある
  （フレーム番号は常に正しい）。
