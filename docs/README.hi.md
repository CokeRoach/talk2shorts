# talk2shorts

[English](../README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · [中文](README.zh.md) · [Português](README.pt.md) · **हिन्दी** · [Bahasa Indonesia](README.id.md) · [Français](README.fr.md) · [Русский](README.ru.md)

किसी हॉरिज़ॉन्टल टॉक, लेक्चर या इंटरव्यू के एक हिस्से को सिर्फ़ एक command से वर्टिकल short में बदलें। Crop बोलने वाले के साथ-साथ चलता है, captions बोली गई बातों से लिखे जाते हैं और ऐसी जगह रखे जाते हैं जहाँ **YouTube Shorts, TikTok और Instagram Reels के buttons उन्हें नहीं ढकेंगे**, और sound को -14 LUFS पर सेट किया जाता है।

<p align="center">
  <img src="https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/demo.gif" width="300" alt="talk2shorts से बना एक वर्टिकल short: बात करता हुआ एक अंतरिक्ष यात्री, ऊपर title और safe area के अंदर दो लाइन के captions">
</p>

![बाईं ओर 16:9 source frame और दाईं ओर उसी से talk2shorts द्वारा बनाया गया 9:16 short](https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/before-after.jpg)

```
talk2shorts interview.mp4 --start 0:10 --end 0:50 --title "What it's like to live in space"
```

## यह क्या करता है

1. **चेहरे को follow करता है।** OpenCV का YuNet detector एक सेकंड में पाँच बार speaker को ढूँढता है; 9:16 crop बड़ी हरकतों के साथ चलता है और छोटी हरकतों को नज़रअंदाज़ करता है, ताकि हर gesture पर frame हिले नहीं।
2. **Captions लिखता है।** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) word timings के साथ उस हिस्से को transcribe करता है, और talk2shorts शब्दों को ज़्यादा से ज़्यादा दो संतुलित लाइनों वाले captions में बाँटता है, जो pauses, वाक्य के अंत और commas पर कटते हैं, और कभी किसी एक शब्द को अकेला नहीं छोड़ते। चाहें तो अपनी SRT ख़ुद दें।
3. **Text को players के buttons से दूर रखता है।** Captions और title उस area के अंदर रखे जाते हैं जो तीनों platforms पर खाली रहता है; इसके लिए [shorts-safezone](https://github.com/CokeRoach/shorts-safezone) में हर platform के अपने templates से मापे गए zones इस्तेमाल होते हैं। TikTok पर यह area नीचे की ओर संकरा है (उसके buttons दाईं ओर होते हैं), इसलिए captions बीच से थोड़ा बाईं ओर रहते हैं; सिर्फ़ YouTube का चौड़ा area इस्तेमाल करने के लिए `--platforms youtube` दें।
4. **Sound सेट करता है।** -14 LUFS पर two-pass loudness normalisation, true peak -1.5 dB से नीचे, और आख़िर में fade।
5. **Result जाँचता है।** एक report बताती है कि हर caption और title हर platform पर साफ़ दिख रहे हैं या नहीं, मापी गई loudness कितनी है, चेहरा कितनी बार मिला, और title चेहरे को ढक रहा है या नहीं।

सब कुछ आपके कंप्यूटर पर चलता है। कुछ भी upload नहीं होता।

## Install करना

आपके PATH पर [ffmpeg](https://ffmpeg.org) होना चाहिए (libass के साथ, जैसा ज़्यादातर builds में होता है), फिर:

```
pip install "talk2shorts[captions]"
```

अगर आप हमेशा अपनी `--srt` देंगे तो `[captions]` हटा दें। Face model (230 KB, MIT licence) पहली बार इस्तेमाल करने पर एक बार download होता है और उसके SHA-256 से जाँचा जाता है।

## इस्तेमाल

```
talk2shorts talk.mp4 --start 3:33 --end 4:25
talk2shorts talk.mp4 --start 213 --end 265 --title "Where does happiness come from?" --language en
talk2shorts talk.mp4 --start 3:33 --end 4:25 --srt talk.srt          # your captions, in source time
talk2shorts talk.mp4 --start 3:33 --end 4:25 --model large-v3        # better captions, slower
talk2shorts talk.mp4 --start 3:33 --end 4:25 --platforms youtube     # only YouTube's buttons
```

यह `talk_short.mp4`, captions को `talk_short.srt` के रूप में, और `talk_short.report.json` लिखता है:

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

खाली list का मतलब है कि उस platform पर text साफ़ दिख रहा है। अगर कोई भी text ढका हो तो command 1 के साथ exit करता है, इसलिए इसे किसी batch script में जाँच के तौर पर इस्तेमाल किया जा सकता है।

| Option | Default | |
| --- | --- | --- |
| `--title` | कोई नहीं | पहले 3 सेकंड तक ऊपर दिखता है; `\n` से लाइन तोड़ें |
| `--srt` | speech recognition | आपके अपने captions, source video के समय के हिसाब से |
| `--model` | `small` | faster-whisper model: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--language` | अपने-आप पहचानी गई | बोली गई भाषा का code, जैसे `en`, `ko`, `ja` |
| `--lines` | `2` | हर caption में लाइनें, 1 या 2 |
| `--platforms` | `all` | `youtube`, `tiktok`, `reels`, या comma से अलग की गई list |
| `--font` | उस script के लिए एक bold system font | Captions और title के लिए font file |
| `--no-track` | off | Crop को बीच में ही रखें |
| `--no-captions` | off | कोई captions नहीं |

faster-whisper की CUDA libraries installed हों तो GPU speech recognition को तेज़ कर देता है; उनके बिना talk2shorts अपने-आप CPU पर चलता है।

## भाषाएँ

Speech recognition उन सभी भाषाओं को cover करता है जिन्हें faster-whisper जानता है (लगभग 99)। Caption font लिखी जा रही script के हिसाब से चुना जाता है, ताकि हर भाषा को ऐसा bold font मिले जिसमें उसके अक्षर मौजूद हों:

| Script | Windows | macOS | Linux |
| --- | --- | --- | --- |
| कोरियन | Malgun Gothic | Apple SD Gothic Neo | Noto Sans CJK |
| जापानी | Yu Gothic | Hiragino Sans | Noto Sans CJK |
| चीनी | Microsoft YaHei | PingFang | Noto Sans CJK |
| हिन्दी (देवनागरी) | Nirmala UI | Kohinoor | Noto Sans Devanagari |
| अरबी | Segoe UI | Geeza Pro | Noto Sans Arabic |
| थाई | Leelawadee UI | Thonburi | Noto Sans Thai |
| लैटिन, सिरिलिक | Segoe UI | Helvetica Neue | Noto Sans |

सिर्फ़ Han अक्षरों वाले text को चीनी माना जाता है; बिना kana के लिखी जापानी के लिए `--language ja` दें। अरबी को दाएँ से बाएँ layout किया जाता है। Captions वाक्य के अंत और commas (、 और ，भी) के बाद टूटते हैं, कभी भी लाइन को closing punctuation से शुरू नहीं करते, और थाई व देवनागरी की मात्राओं को उनके अक्षर के साथ ही रखते हैं। अपना font चुनने के लिए `--font` इस्तेमाल करें।

## सीमाएँ

- Frame में एक ही speaker हो तो सबसे अच्छा काम करता है। दो लोग अगल-बगल हों तो crop बड़े चेहरे को follow करता है।
- Source में पहले से burn किए गए subtitles picture में बने रहते हैं।
- जब speaker का सिर frame के ऊपरी किनारे के पास हो, तो title उसे ढक सकता है; report इसकी जानकारी देती है (`title_covers_face`)। छोटा, एक लाइन का title रखने से मदद मिलती है।
- थाई में शब्दों के बीच spaces नहीं होते, और talk2shorts के पास थाई dictionary नहीं है, इसलिए थाई की लंबी लाइन किसी शब्द के बीच में टूट सकती है।
- Speech recognition से गलतियाँ होती हैं, ख़ासकर नामों में। `.srt` पढ़ें, उसे ठीक करें और फिर `--srt` के साथ दोबारा render करें।

## Development

```
python -m venv .venv
.venv/Scripts/pip install -e ".[test,captions]"     # or .venv/bin/pip on macOS and Linux
.venv/Scripts/python -m pytest
```

## श्रेय (Credits)

- Demo footage: NASA अंतरिक्ष यात्री Victor Glover, KCAL-TV के साथ in-flight interview में, 30 दिसंबर 2020 ([NASA Image and Video Library](https://images.nasa.gov/details/iss064m263651519_Expedition_64_Inflight%20with_KCAL_LA_201230))। NASA की सामग्री public domain में है; NASA इस project का समर्थन (endorse) नहीं करता।
- Face detection: [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet), MIT licence।
- Speech recognition: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), MIT licence।

## लाइसेंस

MIT
