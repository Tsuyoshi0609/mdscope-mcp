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

Day 1 の実装が終わり、**ユーザー確認 A 待ち**:

- 済: Codex → `url` → Safari で表示できた（確認 A の Codex 経路）。
- 待ち: Claude Code（登録済み）で「`example/alanine-dipeptide-nowater.pdb` を見せて」→ Artifact が開いて回せるか。
- 待ち: **ChatGPT デスクトップで会話内に描画されるか**（MCP Apps 対応を実装済み、[setup.md](setup.md) §5）。
  `ui://mdscope/viewer/v1.html` の postMessage ハンドシェイクと `window.openai` 経路はブラウザで未確認。

## 最大の問題

- ChatGPT デスクトップ（Mac）から floyd のサーバーへは SSH stdio で繋ぐしかなく、その構成を実機で通していない。
- Codex 経路は `--serve` の常駐と SSH ポート転送が前提。どちらかが落ちていると `url` は返るが開けない。

## 次にやること

1. 確認 A が通ったら Day 2: 軌道対応（選択・間引き・PBC 補正・`int16` 座標、ビューアのスライダーと再生）。
   テストデータは `MDAnalysisTests` の GRO+XTC と PRMTOP+NC、実データは `example/` の ALA2 250 ns。
2. 通らなければ、ブラウザのコンソールのエラーをそのまま貼ってもらい `template.html` を直す。

細かい日程は `docs/local/IMPLEMENTATION_PLAN.md`。
