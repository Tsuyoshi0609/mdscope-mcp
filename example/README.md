# example データ

このフォルダのデータは git で追跡しない。以下の手順で取得してここに置く。

## ALA2（アラニンジペプチド）

出典: mdshare の ALA2 ページ
<https://markovmodel.github.io/mdshare/ALA2/#alanine-dipeptide>

ブラウザで次の 2 ファイルをダウンロードし、`example/` 直下に置く。

| ファイル | 内容 |
|---|---|
| `alanine-dipeptide-nowater.pdb` | トポロジ（22 原子、水なし） |
| `alanine-dipeptide-0-250ns-nowater.xtc` | 軌道 250 ns、約 41 MB |

同ページには別の 2 本の軌道（`-1-`, `-2-`）と重原子のみの版もある。必要なら同じ場所に置く。

## アデニル酸キナーゼ（AdK）

PDB の [1AKE](https://www.rcsb.org/structure/1AKE) を取得して MD を実行し、次の 2 ファイルとして置く
（MD の条件は問わない。表現の切り替えを試すための、ある程度大きなタンパク質）。

| ファイル | 内容 |
|---|---|
| `adenylate_kinase.pdb` | トポロジ |
| `adenylate_kinase.dcd` | 軌道 |
