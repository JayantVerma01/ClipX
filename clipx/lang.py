"""Spoken-language helpers: Hinglish (romanised Hindi) captions and caption-safe word masking.

GTA-Auto-Clipper's rule, which suits an Indian audience: English speech stays English, Hindi speech is shown in Latin
letters ("Hinglish"), any other / uncertain language gets no captions. Also: once a stream is clearly Hindi, lock the
recogniser to Hindi, because Whisper re-guesses the language for every chunk and sometimes flips to English.
This file is our own implementation (own mapping + word-final schwa deletion so 'kya' is not 'kyaa').
"""
import re

_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
      "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
      "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
      "ष": "sh", "स": "s", "ह": "h", "ळ": "l", "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f"}
_V = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au"}
_M = {"ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au"}
_VIRAMA, _NUKTA = "्", "़"


def romanize_hindi(text):
    """Devanagari -> Latin letters. Pure function (unit-tested)."""
    out_words = []
    for word in str(text).split(" "):
        res, i, n = [], 0, len(word)
        while i < n:
            ch = word[i]
            if ch in _C:
                key = ch
                if i + 1 < n and word[i + 1] == _NUKTA and ch + _NUKTA in _C:
                    key, i = ch + _NUKTA, i + 1
                res.append(_C[key])
                i += 1
                if i < n and word[i] in _M:
                    res.append(_M[word[i]])
                    i += 1
                elif i < n and word[i] == _VIRAMA:
                    i += 1
                else:
                    # inherent 'a': kept inside a word, deleted at the end of a multi-letter word ("kam", "ghar")
                    if i < n or len(res) == 1:
                        res.append("a")
            elif ch in _V:
                res.append(_V[ch])
                i += 1
            elif ch in ("ं", "ँ"):
                res.append("n")
                i += 1
            elif ch == "ः":
                res.append("h")
                i += 1
            elif ch in ("।", "॥"):
                res.append(".")
                i += 1
            elif ch == _VIRAMA or ch == _NUKTA:
                i += 1
            else:
                res.append(ch)
                i += 1
        w = "".join(res)
        if len(w) >= 3 and w.endswith("aa"):          # word-final long aa is written 'a' in Hinglish: kyaa -> kya
            w = w[:-1]
        out_words.append(w)
    return " ".join(out_words)


def has_arabic_script(text):
    return any("؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ" or "ࢠ" <= c <= "ࣿ" for c in text)


def has_devanagari(text):
    return any("ऀ" <= c <= "ॿ" for c in text)


MASK = {"fuck", "fucking", "fucked", "fucker", "motherfucker", "shit", "shitty", "bullshit", "bitch", "bitches", "pussy",
        "dick", "cock", "cunt", "whore", "slut", "porn", "sex", "sexy", "asshole", "bastard", "chutiya", "madarchod",
        "bhenchod", "behenchod", "bsdk", "gandu", "randi", "lund", "bc", "mc"}


def mask_word(w):
    """F*** style masking for burned-in captions only (the audio is untouched)."""
    core = re.sub(r"[^a-z]", "", w.lower())
    if core in MASK or core.startswith(("fuck", "motherf", "shit")):
        return w[:1] + "*" * max(2, len(w) - 1)
    return w


class LanguageLock:
    """Whisper guesses the language per chunk; after `min_votes` confident chunks, if at least `share` were Hindi,
    every later chunk is forced to Hindi. Pure logic (unit-tested)."""

    def __init__(self, forced=None, min_votes=3, share=0.5):
        self.forced, self.min_votes, self.share, self.votes = forced, min_votes, share, {}

    def vote(self, lang, prob):
        if self.forced is None and prob >= 0.6:
            self.votes[lang] = self.votes.get(lang, 0) + 1

    def locked(self):
        if self.forced in ("hi", "en"):
            return self.forced
        total = sum(self.votes.values())
        if total >= self.min_votes and self.votes.get("hi", 0) / total >= self.share:
            return "hi"
        return None


def caption_language(spoken, words_text):
    """(caption_language, fallback_reason): English stays English, Hindi -> Hinglish, anything else -> no captions."""
    if spoken == "en":
        return "English", None
    if spoken == "hi":
        if has_arabic_script(words_text):
            return "none", "Hindi recognised in Arabic script; captions omitted"
        return "Hinglish", None
    return "none", "captions off: unsupported or uncertain language"
