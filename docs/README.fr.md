# talk2shorts

[English](../README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · [中文](README.zh.md) · [Português](README.pt.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md) · **Français** · [Русский](README.ru.md)

Transformez un passage d'une conférence, d'un cours ou d'une interview au format horizontal en un short vertical, en une seule commande. Le recadrage suit l'intervenant, les sous-titres sont rédigés à partir de la parole et placés là où **les boutons de YouTube Shorts, TikTok et Instagram Reels ne les masqueront pas**, et le son est réglé à -14 LUFS.

<p align="center">
  <img src="https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/demo.gif" width="300" alt="Un short vertical réalisé avec talk2shorts : un astronaute qui parle, avec un titre en haut et des sous-titres sur deux lignes dans la zone sûre">
</p>

![L'image source en 16:9 à gauche et le short en 9:16 que talk2shorts en a tiré à droite](https://raw.githubusercontent.com/CokeRoach/talk2shorts/main/docs/before-after.jpg)

```
talk2shorts interview.mp4 --start 0:10 --end 0:50 --title "What it's like to live in space"
```

## Ce que fait l'outil

1. **Il suit le visage.** Le détecteur YuNet d'OpenCV repère l'intervenant cinq fois par seconde ; le recadrage 9:16 suit les grands déplacements et ignore les petits, si bien qu'il ne tremble pas à chaque geste.
2. **Il rédige les sous-titres.** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) transcrit le passage avec l'horodatage de chaque mot, et talk2shorts regroupe les mots en sous-titres d'au plus deux lignes équilibrées, coupés aux pauses, aux fins de phrase et aux virgules, sans jamais laisser un mot isolé. Vous pouvez aussi fournir votre propre fichier SRT.
3. **Il tient le texte à l'écart des éléments des lecteurs.** Les sous-titres et le titre sont placés dans la zone dégagée sur les trois plateformes, d'après les zones mesurées à partir des modèles propres à chaque plateforme dans [shorts-safezone](https://github.com/CokeRoach/shorts-safezone). Sur TikTok, cette zone est étroite en bas (ses boutons se trouvent à droite) : les sous-titres sont donc légèrement décalés à gauche du centre ; passez `--platforms youtube` pour utiliser uniquement la zone plus large de YouTube.
4. **Il règle le son.** Normalisation de la sonie en deux passes à -14 LUFS, crête vraie (true peak) sous -1.5 dB, avec un fondu en fin de vidéo.
5. **Il vérifie le résultat.** Un rapport indique si chaque sous-titre et le titre sont dégagés sur chaque plateforme, la sonie mesurée, la fréquence à laquelle un visage a été détecté et si le titre recouvre le visage.

Tout s'exécute sur votre ordinateur. Rien n'est envoyé en ligne.

## Installation

Il vous faut [ffmpeg](https://ffmpeg.org) dans votre PATH (avec libass, comme dans la plupart des builds), puis :

```
pip install "talk2shorts[captions]"
```

Omettez `[captions]` si vous fournissez toujours votre propre `--srt`. Le modèle de détection de visage (230 KB, licence MIT) est téléchargé une seule fois, lors de la première utilisation, et vérifié à l'aide de son empreinte SHA-256.

## Utilisation

```
talk2shorts talk.mp4 --start 3:33 --end 4:25
talk2shorts talk.mp4 --start 213 --end 265 --title "Where does happiness come from?" --language en
talk2shorts talk.mp4 --start 3:33 --end 4:25 --srt talk.srt          # your captions, in source time
talk2shorts talk.mp4 --start 3:33 --end 4:25 --model large-v3        # better captions, slower
talk2shorts talk.mp4 --start 3:33 --end 4:25 --platforms youtube     # only YouTube's buttons
```

La commande produit `talk_short.mp4`, les sous-titres dans `talk_short.srt`, ainsi que `talk_short.report.json` :

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

Une liste vide signifie que le texte est dégagé sur cette plateforme. La commande se termine avec le code 1 dès qu'un texte est masqué, ce qui permet de l'utiliser comme garde-fou dans un script de traitement par lots.

| Option | Par défaut | |
| --- | --- | --- |
| `--title` | aucun | Affiché en haut pendant les 3 premières secondes ; `\n` insère un saut de ligne |
| `--srt` | reconnaissance vocale | Vos propres sous-titres, synchronisés sur la vidéo source |
| `--model` | `small` | Modèle faster-whisper : `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--language` | détectée | Code de la langue parlée, par exemple `en`, `ko`, `ja` |
| `--lines` | `2` | Nombre de lignes par sous-titre, 1 ou 2 |
| `--platforms` | `all` | `youtube`, `tiktok`, `reels`, ou une liste séparée par des virgules |
| `--font` | une police système en gras adaptée à l'écriture | Un fichier de police pour les sous-titres et le titre |
| `--no-track` | désactivé | Garder le recadrage centré |
| `--no-captions` | désactivé | Aucun sous-titre |

Un GPU accélère la reconnaissance vocale lorsque les bibliothèques CUDA de faster-whisper sont installées ; sans elles, talk2shorts bascule automatiquement sur le CPU.

## Langues

La reconnaissance vocale couvre les langues prises en charge par faster-whisper (environ 99). La police des sous-titres s'adapte à l'écriture utilisée, de sorte que chaque langue dispose d'une police en gras qui contient ses caractères :

| Écriture | Windows | macOS | Linux |
| --- | --- | --- | --- |
| Coréen | Malgun Gothic | Apple SD Gothic Neo | Noto Sans CJK |
| Japonais | Yu Gothic | Hiragino Sans | Noto Sans CJK |
| Chinois | Microsoft YaHei | PingFang | Noto Sans CJK |
| Hindi (devanagari) | Nirmala UI | Kohinoor | Noto Sans Devanagari |
| Arabe | Segoe UI | Geeza Pro | Noto Sans Arabic |
| Thaï | Leelawadee UI | Thonburi | Noto Sans Thai |
| Latin, cyrillique | Segoe UI | Helvetica Neue | Noto Sans |

Un texte composé uniquement de caractères Han est interprété comme du chinois ; passez `--language ja` pour du japonais écrit sans kana. L'arabe est mis en page de droite à gauche. Les sous-titres sont coupés après les fins de phrase et les virgules (y compris 、 et ，), ne commencent jamais une ligne par une ponctuation fermante, et gardent les signes vocaliques thaïs et devanagari attachés à leur lettre. Utilisez `--font` pour choisir votre propre police.

## Limites

- Les meilleurs résultats s'obtiennent avec un seul intervenant à l'image. Avec deux personnes côte à côte, le recadrage suit le visage le plus grand.
- Les sous-titres déjà incrustés dans la vidéo source restent visibles à l'image.
- Lorsque la tête de l'intervenant est proche du haut du cadre, le titre peut la recouvrir ; le rapport le signale (`title_covers_face`). Un titre plus court, sur une seule ligne, permet d'y remédier.
- Le thaï s'écrit sans espaces entre les mots et talk2shorts ne dispose pas de dictionnaire thaï : une longue ligne en thaï peut donc être coupée au milieu d'un mot.
- La reconnaissance vocale commet des erreurs, en particulier sur les noms propres. Relisez le `.srt`, corrigez-le, puis relancez le rendu avec `--srt`.

## Développement

```
python -m venv .venv
.venv/Scripts/pip install -e ".[test,captions]"     # or .venv/bin/pip on macOS and Linux
.venv/Scripts/python -m pytest
```

## Crédits

- Séquence de démonstration : l'astronaute de la NASA Victor Glover lors d'une interview en vol avec KCAL-TV, le 30 décembre 2020 ([NASA Image and Video Library](https://images.nasa.gov/details/iss064m263651519_Expedition_64_Inflight%20with_KCAL_LA_201230)). Les contenus de la NASA relèvent du domaine public ; la NASA ne cautionne pas ce projet.
- Détection de visage : [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet), licence MIT.
- Reconnaissance vocale : [faster-whisper](https://github.com/SYSTRAN/faster-whisper), licence MIT.

## Licence

MIT
