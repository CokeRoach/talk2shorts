# talk2shorts

[English](../README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **中文** · [Português](README.pt.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md) · [Français](README.fr.md) · [Русский](README.ru.md)

一条命令，就能把横屏演讲、讲座或访谈中的一段剪成竖屏短视频。画面裁切会跟随说话人，字幕根据语音自动生成，并放在 **YouTube Shorts、TikTok 和 Instagram Reels 的按钮不会遮挡的位置**，音量统一调整到 -14 LUFS。

<p align="center">
  <img src="https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/demo.gif" width="300" alt="用 talk2shorts 制作的竖屏短视频：一位宇航员正在讲话，顶部是标题，安全区域内是两行字幕">
</p>

![左边是 16:9 的原始画面，右边是 talk2shorts 据此生成的 9:16 短视频](https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/before-after.jpg)

```
talk2shorts interview.mp4 --start 0:10 --end 0:50 --title "What it's like to live in space"
```

## 功能

1. **跟随人脸。** OpenCV 的 YuNet 检测器每秒检测五次说话人位置；9:16 裁切框只跟随较大的移动，忽略细小的晃动，因此不会随每个手势而抖动。
2. **生成字幕。** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 对该片段进行转写并给出逐词时间戳，talk2shorts 再把词语组合成最多两行、长度均衡的字幕，在停顿、句末和逗号处断开，绝不会让一个词单独成行。你也可以使用自己的 SRT。
3. **让文字避开播放器界面。** 字幕和标题都放在三个平台上都不会被遮挡的区域内，所用的区域数据来自 [shorts-safezone](https://github.com/CokeRoach/shorts-safezone)，是根据各平台官方模板实测得出的。TikTok 的这一区域在底部较窄（它的按钮位于右侧），因此字幕会略微偏左；传入 `--platforms youtube` 则只使用 YouTube 更宽的区域。
4. **调整音量。** 两遍响度标准化到 -14 LUFS，真峰值低于 -1.5 dB，并在结尾淡出。
5. **检查结果。** 生成一份报告，说明每条字幕和标题在各个平台上是否都未被遮挡、实测响度、检测到人脸的比例，以及标题是否遮住了人脸。

所有处理都在你的电脑上完成，不会上传任何内容。

## 安装

你需要在 PATH 中提供 [ffmpeg](https://ffmpeg.org)（需带 libass，大多数构建版本都已包含），然后运行：

```
pip install "talk2shorts[captions]"
```

如果你始终会通过 `--srt` 提供自己的字幕，可以去掉 `[captions]`。人脸模型（230 KB，MIT 许可证）会在首次使用时下载一次，并校验其 SHA-256。

## 用法

```
talk2shorts talk.mp4 --start 3:33 --end 4:25
talk2shorts talk.mp4 --start 213 --end 265 --title "Where does happiness come from?" --language en
talk2shorts talk.mp4 --start 3:33 --end 4:25 --srt talk.srt          # your captions, in source time
talk2shorts talk.mp4 --start 3:33 --end 4:25 --model large-v3        # better captions, slower
talk2shorts talk.mp4 --start 3:33 --end 4:25 --platforms youtube     # only YouTube's buttons
```

它会输出 `talk_short.mp4`、字幕文件 `talk_short.srt`，以及 `talk_short.report.json`：

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

空列表表示在该平台上没有遮挡。只要有任何文字被遮挡，命令就会以 1 退出，因此可以用来把关批处理脚本。

| 选项 | 默认值 | |
| --- | --- | --- |
| `--title` | 无 | 在开头 3 秒显示于顶部；`\n` 用于换行 |
| `--srt` | 语音识别 | 你自己的字幕，时间轴对应原视频 |
| `--model` | `small` | faster-whisper 模型：`tiny`、`base`、`small`、`medium`、`large-v3` |
| `--language` | 自动检测 | 语音的语言代码，例如 `en`、`ko`、`ja` |
| `--lines` | `2` | 每条字幕的行数，1 或 2 |
| `--platforms` | `all` | `youtube`、`tiktok`、`reels`，或用逗号分隔的列表 |
| `--font` | 适合该文字的系统粗体字体 | 用于字幕和标题的字体文件 |
| `--no-track` | 关闭 | 裁切框保持居中 |
| `--no-captions` | 关闭 | 不添加字幕 |

如果安装了 faster-whisper 的 CUDA 库，GPU 可以加快语音识别；没有这些库时，talk2shorts 会自动退回到 CPU。

## 语言

语音识别支持 faster-whisper 所支持的语言（约 99 种）。字幕字体会根据所书写的文字自动选择，因此每种语言都能用上包含其字符的粗体字体：

| 文字 | Windows | macOS | Linux |
| --- | --- | --- | --- |
| 韩文 | Malgun Gothic | Apple SD Gothic Neo | Noto Sans CJK |
| 日文 | Yu Gothic | Hiragino Sans | Noto Sans CJK |
| 中文 | Microsoft YaHei | PingFang | Noto Sans CJK |
| 印地文（天城文） | Nirmala UI | Kohinoor | Noto Sans Devanagari |
| 阿拉伯文 | Segoe UI | Geeza Pro | Noto Sans Arabic |
| 泰文 | Leelawadee UI | Thonburi | Noto Sans Thai |
| 拉丁字母、西里尔字母 | Segoe UI | Helvetica Neue | Noto Sans |

只含汉字的文本会被识别为中文；对于不含假名的日文，请传入 `--language ja`。阿拉伯文按从右到左排版。字幕会在句末和逗号（包括 、 和 ，）之后断行，绝不会让行首出现闭合标点，并且会让泰文和天城文的元音符号与其所属字母保持在一起。可以用 `--font` 选择你自己的字体。

## 局限

- 画面中只有一位说话人时效果最好。如果两个人并排出现，裁切框会跟随较大的那张脸。
- 原视频中已经烧录的字幕会保留在画面里。
- 当说话人的头部靠近画面顶部时，标题可能会遮住它；报告中会指出这一点（`title_covers_face`）。使用更短的单行标题会有帮助。
- 泰文的词与词之间没有空格，而 talk2shorts 没有泰文词典，因此较长的泰文行可能会在词语中间断开。
- 语音识别会出错，尤其是人名。请检查 `.srt`，修改后用 `--srt` 重新渲染。

## 开发

```
python -m venv .venv
.venv/Scripts/pip install -e ".[test,captions]"     # or .venv/bin/pip on macOS and Linux
.venv/Scripts/python -m pytest
```

## 致谢

- 演示素材：NASA 宇航员 Victor Glover 于 2020 年 12 月 30 日接受 KCAL-TV 的在轨采访（[NASA Image and Video Library](https://images.nasa.gov/details/iss064m263651519_Expedition_64_Inflight%20with_KCAL_LA_201230)）。NASA 素材属于公有领域；NASA 不为本项目背书。
- 人脸检测：[YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)，MIT 许可证。
- 语音识别：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)，MIT 许可证。

## 许可证

MIT
