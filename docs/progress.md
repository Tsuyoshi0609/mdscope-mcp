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

目標 1・2 とも、本線の 2 経路（floyd の Claude Code → Artifact、floyd の Codex → 会話内 MCP App / URL）で
ユーザー確認済み。目標 1 は ChatGPT デスクトップでも確認済み。

Day 3（公開準備）を実施し、**v0.1.0 として push できる状態**。push はユーザーの指示を待つ。
残りの確認:

- ブラウザ側の再生速度（ATLAS 1cvr_A、3363 重原子 × 50 フレーム、2.2 MB）が実用的か。
  サーバー側の実測は [mechanism.md](mechanism.md)。
- `docs/setup.md` を別の端末で追試していない（wheel に `viewer/` と LICENSE が入ることだけ確認）。

## 最大の問題

- 目標 2 の判定「10 万原子・1 万フレーム」級はサーバー側で未計測（floyd に該当データが無い）。
  `max_payload_mb=8` でフレーム数を自動で減らすので HTML は出るが、ブラウザ描画の重さは不明。
- ChatGPT デスクトップでの初回表示が遅い（原因はモデル側の探索。サーバー起動は約 1.6 秒）。
- Codex 経路の `url` は `--serve` の常駐と SSH ポート転送が前提。会話内描画が効く Codex デスクトップでは不要。

## 次にやること

1. ユーザーの指示で `git push origin main`（GitHub 公開 v0.1.0）。
2. Day 4（目標 3）: `surface` 表現、部分選択ごとの表現の重ね合わせ（例: リガンド周り 5 Å を sticks）、
   ラベル。ビューア内のメニューも同じ項目に揃える。
3. Day 6（目標 4）: `view_density`（`mrcfile` → 間引き → 3Dmol の等値面）。

細かい日程は `docs/local/IMPLEMENTATION_PLAN.md`。
