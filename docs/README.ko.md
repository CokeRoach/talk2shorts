# talk2shorts

[English](../README.md) · **한국어** · [日本語](README.ja.md) · [中文](README.zh.md) · [Português](README.pt.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md) · [Français](README.fr.md) · [Русский](README.ru.md)

가로로 찍은 강연·강의·인터뷰의 한 구간을 명령 한 줄로 세로 쇼츠로 만듭니다. 화면은 말하는 사람을 따라 잘리고, 자막은 말소리를 받아 적어 **YouTube Shorts, TikTok, Instagram Reels의 버튼에 가려지지 않는 곳**에 놓이며, 소리는 -14 LUFS로 맞춰집니다.

<p align="center">
  <img src="https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/demo.gif" width="300" alt="talk2shorts로 만든 세로 쇼츠: 우주비행사가 말하고 있고, 위쪽에 제목이, 안전 영역 안에 두 줄 자막이 있는 모습">
</p>

![왼쪽은 16:9 원본 화면, 오른쪽은 talk2shorts가 그것으로 만든 9:16 쇼츠](https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/before-after.jpg)

```
talk2shorts interview.mp4 --start 0:10 --end 0:50 --title "What it's like to live in space"
```

## 하는 일

1. **얼굴을 따라갑니다.** OpenCV의 YuNet 검출기가 1초에 다섯 번 말하는 사람을 찾습니다. 9:16 크롭은 큰 움직임은 따라가고 작은 움직임은 무시하므로, 손짓 하나하나에 화면이 흔들리지 않습니다.
2. **자막을 씁니다.** [faster-whisper](https://github.com/SYSTRAN/faster-whisper)가 해당 구간을 단어별 타이밍과 함께 받아 적고, talk2shorts가 단어들을 최대 두 줄의 균형 잡힌 자막으로 묶습니다. 말의 쉼, 문장 끝, 쉼표에서 끊으며, 한 단어만 홀로 남기지 않습니다. 직접 만든 SRT를 써도 됩니다.
3. **글자를 플레이어 화면 요소에서 비켜 둡니다.** 자막과 제목은 세 플랫폼 모두에서 가려지지 않는 영역 안에 들어갑니다. 이 영역은 [shorts-safezone](https://github.com/CokeRoach/shorts-safezone)에서 각 플랫폼의 공식 템플릿으로 측정한 구역을 사용합니다. TikTok은 아래쪽 영역이 좁아서(버튼이 오른쪽에 있음) 자막이 가운데보다 약간 왼쪽에 놓입니다. YouTube의 더 넓은 영역만 쓰려면 `--platforms youtube`를 지정하세요.
4. **소리를 맞춥니다.** 2패스 라우드니스 정규화로 -14 LUFS, 트루 피크 -1.5 dB 미만으로 맞추고, 끝에 페이드를 넣습니다.
5. **결과를 검사합니다.** 보고서에 모든 자막과 제목이 플랫폼별로 가려지지 않는지, 측정한 라우드니스, 얼굴을 찾은 비율, 제목이 얼굴을 가리는지가 담깁니다.

모든 작업은 사용자의 컴퓨터에서 실행됩니다. 아무것도 업로드되지 않습니다.

## 설치

PATH에 [ffmpeg](https://ffmpeg.org)가 있어야 합니다(대부분의 빌드처럼 libass 포함). 그다음 아래를 실행합니다.

```
pip install "talk2shorts[captions]"
```

항상 직접 만든 `--srt`를 넘길 거라면 `[captions]`는 빼도 됩니다. 얼굴 모델(230 KB, MIT 라이선스)은 처음 사용할 때 한 번 내려받으며, SHA-256으로 검증합니다.

## 사용법

```
talk2shorts talk.mp4 --start 3:33 --end 4:25
talk2shorts talk.mp4 --start 213 --end 265 --title "Where does happiness come from?" --language en
talk2shorts talk.mp4 --start 3:33 --end 4:25 --srt talk.srt          # your captions, in source time
talk2shorts talk.mp4 --start 3:33 --end 4:25 --model large-v3        # better captions, slower
talk2shorts talk.mp4 --start 3:33 --end 4:25 --platforms youtube     # only YouTube's buttons
```

결과로 `talk_short.mp4`, 자막 파일 `talk_short.srt`, 그리고 `talk_short.report.json`을 만듭니다.

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

빈 목록은 해당 플랫폼에서 가려지는 글자가 없다는 뜻입니다. 글자가 하나라도 가려지면 명령이 1로 종료되므로, 일괄 처리 스크립트의 검사 단계로 쓸 수 있습니다.

| 옵션 | 기본값 | |
| --- | --- | --- |
| `--title` | 없음 | 처음 3초 동안 위쪽에 표시됩니다. `\n`으로 줄을 바꿉니다 |
| `--srt` | 음성 인식 | 원본 영상 시간에 맞춘 직접 만든 자막 |
| `--model` | `small` | faster-whisper 모델: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--language` | 자동 감지 | 말하는 언어의 코드(예: `en`, `ko`, `ja`) |
| `--lines` | `2` | 자막 하나당 줄 수, 1 또는 2 |
| `--platforms` | `all` | `youtube`, `tiktok`, `reels`, 또는 쉼표로 구분한 목록 |
| `--font` | 문자 체계에 맞는 굵은 시스템 글꼴 | 자막과 제목에 쓸 글꼴 파일 |
| `--no-track` | 꺼짐 | 크롭을 가운데에 고정합니다 |
| `--no-captions` | 꺼짐 | 자막을 넣지 않습니다 |

faster-whisper의 CUDA 라이브러리가 설치되어 있으면 GPU로 음성 인식이 빨라집니다. 없으면 talk2shorts가 알아서 CPU로 전환합니다.

## 언어

음성 인식은 faster-whisper가 아는 언어(약 99개)를 지원합니다. 자막 글꼴은 쓰이는 문자 체계를 따르므로, 어떤 언어든 그 글자를 갖춘 굵은 글꼴이 적용됩니다.

| 문자 체계 | Windows | macOS | Linux |
| --- | --- | --- | --- |
| 한국어 | Malgun Gothic | Apple SD Gothic Neo | Noto Sans CJK |
| 일본어 | Yu Gothic | Hiragino Sans | Noto Sans CJK |
| 중국어 | Microsoft YaHei | PingFang | Noto Sans CJK |
| 힌디어(데바나가리) | Nirmala UI | Kohinoor | Noto Sans Devanagari |
| 아랍어 | Segoe UI | Geeza Pro | Noto Sans Arabic |
| 태국어 | Leelawadee UI | Thonburi | Noto Sans Thai |
| 라틴 문자, 키릴 문자 | Segoe UI | Helvetica Neue | Noto Sans |

한자만 있으면 중국어로 인식합니다. 가나 없이 쓴 일본어라면 `--language ja`를 지정하세요. 아랍어는 오른쪽에서 왼쪽으로 배치됩니다. 자막은 문장 끝과 쉼표(、와 ，도 포함) 뒤에서 줄을 바꾸고, 닫는 문장 부호로 줄을 시작하지 않으며, 태국어와 데바나가리의 모음 기호를 해당 글자와 떼어 놓지 않습니다. 원하는 글꼴을 고르려면 `--font`를 쓰세요.

## 한계

- 화면에 말하는 사람이 한 명일 때 가장 잘 동작합니다. 두 사람이 나란히 있으면 크롭은 더 큰 얼굴을 따라갑니다.
- 원본에 이미 입혀진 자막은 화면에 그대로 남습니다.
- 말하는 사람의 머리가 화면 위쪽에 가까우면 제목이 머리를 가릴 수 있으며, 이 경우 보고서에 표시됩니다(`title_covers_face`). 제목을 짧게 한 줄로 쓰면 도움이 됩니다.
- 태국어는 단어 사이를 띄어 쓰지 않고, talk2shorts에는 태국어 사전이 없어서 긴 태국어 줄은 단어 중간에서 끊길 수 있습니다.
- 음성 인식은 틀릴 수 있으며, 특히 이름에서 자주 틀립니다. `.srt`를 읽고 고친 뒤 `--srt`로 다시 렌더링하세요.

## 개발

```
python -m venv .venv
.venv/Scripts/pip install -e ".[test,captions]"     # or .venv/bin/pip on macOS and Linux
.venv/Scripts/python -m pytest
```

## 크레디트

- 데모 영상: NASA 우주비행사 Victor Glover가 2020년 12월 30일 KCAL-TV와 진행한 우주 비행 중 인터뷰([NASA Image and Video Library](https://images.nasa.gov/details/iss064m263651519_Expedition_64_Inflight%20with_KCAL_LA_201230)). NASA 자료는 퍼블릭 도메인이며, NASA는 이 프로젝트를 보증하지 않습니다.
- 얼굴 검출: [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet), MIT 라이선스.
- 음성 인식: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), MIT 라이선스.

## 라이선스

MIT
