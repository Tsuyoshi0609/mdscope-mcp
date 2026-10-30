# 進捗

## 目標

floyd 上の構造ファイル・MD 軌道を、Claude Code / Codex のチャットから「見せて」で確認できる。

| 優先 | 目標 | 判定 |
|---|---|---|
| 1 必須 | 構造ファイルをインタラクティブに見る | 回転・ズームできる cartoon が手元の画面に出る |
| 2 必須 | MD 軌道をインタラクティブに見る | スライダーと再生。10 万原子・1 万フレームでも 1 分以内 |
| 3 できれば | 表現の変更 | sticks / spheres / surface、配色、ハイライト |
| 4 余力 | 密度マップ（`.mrc` / `.map`） | 等値面を構造に重ねる |

2 まで動いたら GitHub 公開。

## いま何をしているか（2026-10-30）

目標 1 は 3 経路（floyd の Claude Code → Artifact、floyd の Codex → URL、ChatGPT デスクトップ → 会話内）
すべてで確認済み。本線は前 2 つ（floyd 上で起動した Claude Code / Codex をデスクトップアプリで確認する）。

Day 2（軌道）の実装が終わり、**ユーザー確認 B の途中**:

- 済: Claude Code（`ssh floyd-remote` → `claude --remote-control`）で ALA2 の軌道を再生できた。
- 済: Codex デスクトップが `view_structure` の結果を会話内に MCP App として描画することを確認。
- 待ち: Codex を立ち上げ直してから
  「`example/alanine-dipeptide-nowater.pdb` と `example/alanine-dipeptide-0-250ns-nowater.xtc` を再生して見せて」
  → 会話内（または `url` を Safari で開いて）▶ とスライダーで再生できる。
  判定: 千切れ・飛びが無い、表示まで 1 分以内。

自動テスト 22 件（`pytest`）は通っている。

## 最大の問題

- 大きな系での再生の重さが未計測（10 万原子級）。`max_payload_mb=8` の上限でフレーム数を自動で減らすが、
  3Dmol 側の描画時間は測っていない。
- ChatGPT デスクトップでの初回表示が遅い（原因はモデル側の探索。サーバー起動は約 1.6 秒）。
- Codex 経路は `--serve` の常駐と SSH ポート転送が前提。どちらかが落ちていると `url` は返るが開けない。

## 次にやること

1. 確認 B が通らなければ、ブラウザのコンソールのエラーを貼ってもらい `viewer/core.js` を直す。
2. Day 3: 大きな系での実測（floyd 上の実データ、`protein and not name H*` と `name CA` での時間とサイズ）、
   README の状態表の更新、`docs/setup.md` を新しい端末で追試 → GitHub 公開（push は指示を受けてから）。

細かい日程は `docs/local/IMPLEMENTATION_PLAN.md`。
