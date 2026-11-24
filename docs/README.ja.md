# talk2shorts

[English](../README.md) · [한국어](README.ko.md) · **日本語** · [中文](README.zh.md) · [Português](README.pt.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md) · [Français](README.fr.md) · [Русский](README.ru.md)

横長のトーク・講義・インタビューの一部分を、コマンド1つで縦型のショート動画にします。クロップは話し手を追いかけ、字幕は音声から書き起こして **YouTube Shorts、TikTok、Instagram Reels のボタンに隠れない位置** に配置し、音量は -14 LUFS に揃えます。

<p align="center">
  <img src="https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/demo.gif" width="300" alt="talk2shorts で作った縦型ショート動画：話している宇宙飛行士、上部にタイトル、セーフエリア内に2行の字幕">
</p>

![左は 16:9 の元動画のフレーム、右はそこから talk2shorts が作った 9:16 のショート動画](https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/before-after.jpg)

```
talk2shorts interview.mp4 --start 0:10 --end 0:50 --title "What it's like to live in space"
```

## できること

1. **顔を追いかけます。** OpenCV の YuNet 検出器が1秒に5回話し手を探します。9:16 のクロップは大きな動きには追従し、小さな動きは無視するので、身ぶりのたびに画面が揺れることはありません。
2. **字幕を作ります。** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) がその区間を単語ごとのタイミング付きで書き起こし、talk2shorts が単語をまとめて最大2行のバランスの取れた字幕にします。区切りは話の間、文末、読点で入れ、1語だけが取り残されることはありません。自分で用意した SRT を使うこともできます。
3. **文字をプレーヤーの UI から避けます。** 字幕とタイトルは、3つのプラットフォームすべてで隠れない領域の中に配置されます。この領域には、[shorts-safezone](https://github.com/CokeRoach/shorts-safezone) で各プラットフォームの公式テンプレートから測定したゾーンを使います。TikTok ではこの領域が下の方で狭い（ボタンが右側にある）ため、字幕は中央よりやや左に置かれます。YouTube のより広い領域だけを使うには `--platforms youtube` を指定してください。
4. **音量を整えます。** 2パスのラウドネス正規化で -14 LUFS、トゥルーピーク -1.5 dB 未満に揃え、最後にフェードを入れます。
5. **結果をチェックします。** レポートには、すべての字幕とタイトルが各プラットフォームで隠れていないか、測定したラウドネス、顔が見つかった割合、タイトルが顔にかぶっていないかが記録されます。

すべての処理はお使いのコンピューター上で行われます。何もアップロードされません。

## インストール

PATH に [ffmpeg](https://ffmpeg.org) が必要です（多くのビルドと同様に libass 付き）。そのうえで次を実行します。

```
pip install "talk2shorts[captions]"
```

常に自分の `--srt` を渡すのであれば、`[captions]` は省略できます。顔検出モデル（230 KB、MIT ライセンス）は初回使用時に一度だけダウンロードされ、SHA-256 で検証されます。

## 使い方

```
talk2shorts talk.mp4 --start 3:33 --end 4:25
talk2shorts talk.mp4 --start 213 --end 265 --title "Where does happiness come from?" --language en
talk2shorts talk.mp4 --start 3:33 --end 4:25 --srt talk.srt          # your captions, in source time
talk2shorts talk.mp4 --start 3:33 --end 4:25 --model large-v3        # better captions, slower
talk2shorts talk.mp4 --start 3:33 --end 4:25 --platforms youtube     # only YouTube's buttons
```

`talk_short.mp4`、字幕ファイル `talk_short.srt`、そして `talk_short.report.json` を書き出します。

```json
{
  "face_found_share": 1.0,
  "captions": 22,
  "caption_safe": { "youtube": [], "tiktok": [], "reels": [] },
  "title_safe":   { "youtube": [], "tiktok": [], "reels": [] },
  "title_covers_face": true,
  "loudness": { "source": -23.05, "output": -14.05 }
}
```

空のリストは、そのプラットフォームで隠れている文字がないことを意味します。どこかの文字が隠れているとコマンドは終了コード 1 で終わるので、バッチスクリプトのチェックとして使えます。

| オプション | デフォルト | |
| --- | --- | --- |
| `--title` | なし | 最初の3秒間、上部に表示されます。`\n` で改行します |
| `--srt` | 音声認識 | 元動画の時間に合わせた自分の字幕 |
| `--model` | `small` | faster-whisper のモデル：`tiny`, `base`, `small`, `medium`, `large-v3` |
| `--language` | 自動検出 | 話されている言語のコード（例：`en`, `ko`, `ja`） |
| `--lines` | `2` | 字幕1つあたりの行数。1 または 2 |
| `--platforms` | `all` | `youtube`, `tiktok`, `reels`、またはカンマ区切りのリスト |
| `--font` | 文字体系に合った太字のシステムフォント | 字幕とタイトルに使うフォントファイル |
| `--no-track` | オフ | クロップを中央に固定します |
| `--no-captions` | オフ | 字幕を入れません |

faster-whisper の CUDA ライブラリがインストールされていれば、GPU で音声認識が速くなります。ない場合、talk2shorts は自動的に CPU に切り替えます。

## 言語

音声認識は faster-whisper が対応する言語（約99言語）をカバーします。字幕フォントは書かれる文字体系に合わせて選ばれるので、どの言語でもその文字を収録した太字フォントが使われます。

| 文字体系 | Windows | macOS | Linux |
| --- | --- | --- | --- |
| 韓国語 | Malgun Gothic | Apple SD Gothic Neo | Noto Sans CJK |
| 日本語 | Yu Gothic | Hiragino Sans | Noto Sans CJK |
| 中国語 | Microsoft YaHei | PingFang | Noto Sans CJK |
| ヒンディー語（デーヴァナーガリー） | Nirmala UI | Kohinoor | Noto Sans Devanagari |
| アラビア語 | Segoe UI | Geeza Pro | Noto Sans Arabic |
| タイ語 | Leelawadee UI | Thonburi | Noto Sans Thai |
| ラテン文字、キリル文字 | Segoe UI | Helvetica Neue | Noto Sans |

漢字だけの場合は中国語として扱われます。かなを使わずに書かれた日本語には `--language ja` を指定してください。アラビア語は右から左へレイアウトされます。字幕は文末と読点（、や ，も含む）の後で改行し、閉じ側の約物で行を始めることはなく、タイ語とデーヴァナーガリーの母音記号を元の文字から切り離しません。フォントを自分で選ぶには `--font` を使います。

## 制限事項

- 画面に話し手が1人の場合に最もうまく動作します。2人が並んでいる場合、クロップは大きい方の顔を追いかけます。
- 元動画にすでに焼き込まれている字幕は、映像に残ります。
- 話し手の頭が画面の上端に近いと、タイトルが頭にかぶることがあります。その場合はレポートに記録されます（`title_covers_face`）。短い1行のタイトルにすると改善します。
- タイ語は単語の間にスペースを入れずに書かれ、talk2shorts にはタイ語の辞書がないため、長いタイ語の行は単語の途中で改行されることがあります。
- 音声認識は間違えることがあり、特に人名で起こりがちです。`.srt` を読んで修正し、`--srt` で再レンダリングしてください。

## 開発

```
python -m venv .venv
.venv/Scripts/pip install -e ".[test,captions]"     # or .venv/bin/pip on macOS and Linux
.venv/Scripts/python -m pytest
```

## クレジット

- デモ映像：NASA の宇宙飛行士 Victor Glover による KCAL-TV との宇宙飛行中のインタビュー、2020年12月30日（[NASA Image and Video Library](https://images.nasa.gov/details/iss064m263651519_Expedition_64_Inflight%20with_KCAL_LA_201230)）。NASA の素材はパブリックドメインです。NASA はこのプロジェクトを推奨・保証していません。
- 顔検出：[YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)、MIT ライセンス。
- 音声認識：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、MIT ライセンス。

## ライセンス

MIT
