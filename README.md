# The Morning Circuit 🎙️

毎朝、前日の英語ニュース（エンタメ系テック・ロボット・IT）を集めて約30分の英語ラジオ番組に仕立て、ポッドキャストとしてスマホで聴けるようにする自動パイプライン。GitHub だけで完結し、ほぼ無料で動きます。

```
GitHub Actions (cron 20:00 UTC = 翌05:00 JST)
  → collect (RSS収集)  → script (Claude API で原稿)  → tts (Google TTS で音声)
  → docs/episodes/ に mp3 を commit  → feed.xml 更新  → GitHub Pages が配信
        → スマホの Podcast アプリが購読・自動DL・オフライン再生
```

## 仕組み

| 段 | ファイル | 内容 |
|---|---|---|
| 収集 | `src/collect.py` | `config/sources.yaml` の RSS から前日(JST)分を取得 |
| 原稿 | `src/script.py` | Claude API (`claude-opus-4-8`) で約30分尺の番組原稿を生成 |
| 音声 | `src/tts.py` | Google Cloud TTS で MP3 化（5000バイト制限のため分割合成） |
| 配信 | `src/feed.py` | `docs/episodes/` から `docs/feed.xml`（Podcast RSS）を生成 |
| 統括 | `src/pipeline.py` | 上記を順に実行し、古い回を間引いて commit 対象を作る |

## セットアップ

### 1. APIキーの準備
- **Anthropic**: [console](https://console.anthropic.com/) で API キーを発行
- **Google Cloud TTS**: プロジェクトで Text-to-Speech API を有効化 → サービスアカウントを作成し JSON キーをダウンロード（無料枠：Neural2 音声で月100万字まで）

### 2. ローカルで試す
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 値を埋める
set -a; source .env; set +a

python src/collect.py        # 収集だけ確認（APIキー不要）
python src/preview.py        # 試し書き出し（短尺・samples/ に保存、本番には触れない）
python src/preview.py 4300   # 本番尺(約30分)で試し書き出し
python src/pipeline.py       # 本番: 収集→原稿→音声→docs/episodes/→feed
```

`preview.py` の出力は `samples/`（gitignore済み）に `preview_<日時>.{txt,mp3}` として保存されます。`pipeline.py` だけが `docs/episodes/` と `feed.xml` を更新します。

### 3. GitHub で自動化
1. このリポジトリを GitHub に push
2. **Settings → Secrets and variables → Actions** で登録：
   - Secrets: `ANTHROPIC_API_KEY`, `GCP_SA_KEY`(JSONキーの中身を丸ごと貼り付け)
   - Variables: `PODCAST_BASE_URL`(下記Pages URL), 任意で `CLAUDE_MODEL` 等
3. **Settings → Pages** で Source を `main` ブランチの `/docs` に設定 → 公開URLが `https://<user>.github.io/<repo>/` になる。これを `PODCAST_BASE_URL` に（末尾スラッシュ付き）
4. **Actions** タブで `Daily episode` を手動実行(`Run workflow`)してテスト
5. 生成された `feed.xml` の URL（`<PODCAST_BASE_URL>feed.xml`）をスマホの Podcast アプリに「URLで購読」追加

以降は毎朝 05:00 JST 頃に新しい回が自動で増えます。

## カスタマイズ
- **ニュースソース**: `config/sources.yaml` の `feeds` を編集
- **声・速度**: `TTS_VOICE`（例 `en-US-Neural2-D`）, `TTS_RATE`
- **尺**: `TARGET_WORDS`（約150語/分）
- **保持数**: `KEEP_EPISODES`（リポジトリに残す回数）
- **モデル/コスト**: `CLAUDE_MODEL` を `claude-sonnet-4-6` / `claude-haiku-4-5` に

## コスト目安
GitHub Actions・GitHub Pages は無料枠。Google TTS は月100万字まで無料（30分≒2.7万字/日なので収まる）。実費は Claude API の数円/日程度。
