"""Pseudo Clinic core logic.

No printing and no input in this file, so the command line version
(pseudo_clinic.py) and the phone app (main.py) can share it.

All knowledge lives in content.json. When online, the app can download a newer
content.json and keep it as content_cache.json. The chat only answers from this
checked content, so it cannot make things up.
"""

import difflib
import json
import os
import random
import re
import ssl
import urllib.request

# The app checks this link for newer advice. It is a public repo that holds only content.json.
CONTENT_URL = os.environ.get(
    "CLINIC_CONTENT_URL",
    "https://raw.githubusercontent.com/kingmarch520-dev/pseudo-clinic-content/main/content.json",
)

APP_NAME = "Pseudo Clinic"
TAGLINE = "The clinic that tells you to go to a real clinic."

DISCLAIMER = (
    "This app gives general guidance only. It cannot diagnose you.\n"
    "If you are worried, go to the clinic. Worry is a good enough reason."
)

URGENT_MESSAGE = (
    "URGENT: Go to the nearest clinic or hospital now.\n"
    "Ask someone to take you. Do not wait to see if it passes."
)

SELF_HARM_MESSAGE = (
    "I am sorry you feel this way. You deserve support right now.\n"
    "Please tell someone you trust, or go to the nearest clinic or hospital today.\n"
    "Do not stay alone with these thoughts."
)

NOT_FOUND_MESSAGE = (
    "I do not have a checked answer for that.\n"
    "Please ask at your clinic or a pharmacist, especially if you feel unwell."
)

# The app celebrates that you feel better, but it never confirms that you are well.
RECOVERY_MESSAGE = (
    "That is lovely to hear, I am really glad you feel better.\n\n"
    "A few things so it stays that way:\n"
    " - Only a clinic can confirm you are fully well, so I cannot say it for you.\n"
    " - If a clinic gave you medicine, finish it as told, even when you feel fine.\n"
    " - Keep any follow-up visit you were given.\n"
    " - Go back to the clinic if the symptoms return or get worse."
)

NOT_BETTER_MESSAGE = (
    "I am sorry you do not feel better yet.\n"
    "If you are not improving, or you feel worse, please visit a clinic. "
    "They can check what is going on and treat it properly."
)

RECOVERY_PHRASES = [
    "i feel better", "i feel much better", "i am better", "i'm better", "im better",
    "feeling better", "feeling much better", "all better", "i am well", "i'm well",
    "im well", "i am cured", "i'm cured", "i am healed", "i have recovered",
    "i recovered", "i am fine now", "i'm fine now", "im fine now", "i feel fine now",
    "i feel well", "got better", "no more pain", "am better now", "i am okay now",
    "i'm okay now",
]

NOT_BETTER_PHRASES = [
    "not better", "no better", "not feeling better", "not feel better",
    "don't feel better", "dont feel better", "isn't better", "isnt better",
    "not getting better", "not well", "not cured", "not fine", "not all better",
    "not recovered",
]

MIXED_WORDS = ("but", "still", "except", "however", "though")

# Used only if both content files are missing or damaged.
EMERGENCY_FALLBACK = {
    "version": 0,
    "urgent": ["chest pain", "cannot breathe", "can't breathe", "heavy bleeding",
               "unconscious", "seizure", "convulsion", "snake", "poison"],
    "self_harm": ["want to die", "kill myself", "hurt myself", "suicid"],
    "clinic_soon": [],
    "hygiene": {"Handwashing": [
        "Wash hands with soap and clean water for at least 20 seconds."]},
    "faq": [],
}

REQUIRED = ("version", "urgent", "self_harm", "clinic_soon", "hygiene", "faq")


# ---------- content files ----------

def valid(data):
    """Check a content file is well formed before we trust it."""
    if not isinstance(data, dict) or any(k not in data for k in REQUIRED):
        return False
    if not isinstance(data["version"], int):
        return False
    for key in ("urgent", "self_harm", "clinic_soon"):
        if not isinstance(data[key], list) or not all(isinstance(x, str) for x in data[key]):
            return False
    # A bad update must never remove the safety warnings.
    if not data["urgent"] or not data["self_harm"]:
        return False
    if not isinstance(data["hygiene"], dict):
        return False
    for tips in data["hygiene"].values():
        if not isinstance(tips, list) or not all(isinstance(t, str) for t in tips):
            return False
    if not isinstance(data["faq"], list):
        return False
    for item in data["faq"]:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("title"), str) or not isinstance(item.get("answer"), str):
            return False
        if not isinstance(item.get("keywords"), list):
            return False
        if not all(isinstance(k, str) for k in item["keywords"]):
            return False
    return True


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if valid(data) else None
    except (OSError, ValueError):
        return None


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


# ---------- text matching ----------

def phrase_in(text, phrase):
    phrase = phrase.lower().strip()
    if not phrase:
        return False
    pattern = r"\b" + re.escape(phrase)
    if len(phrase) <= 4:
        pattern += r"s?\b"
    return re.search(pattern, text) is not None


def any_phrase(text, phrases):
    return any(phrase_in(text, p) for p in phrases)


def is_not_better(text):
    return any_phrase(text.lower(), NOT_BETTER_PHRASES)


def is_recovery(text):
    """True only for a clear 'I feel better' with no 'but still...' in it."""
    low = text.lower()
    if is_not_better(low):
        return False
    if any(w in MIXED_WORDS for w in re.findall(r"[a-z']+", low)):
        return False
    return any_phrase(low, RECOVERY_PHRASES)


def stem(word):
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def keyword_hit(keyword, text, stems):
    kw = keyword.lower().strip()
    if " " in kw:
        return kw in text
    k = stem(kw)
    if k in stems:
        return True
    if len(k) >= 5:  # forgive small spelling mistakes in longer words
        return bool(difflib.get_close_matches(k, stems, n=1, cutoff=0.85))
    return False


# ---------- the engine ----------

class Engine:
    def __init__(self, bundled_path, cache_dir, content_url=""):
        self.bundled = bundled_path
        self.url = content_url
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            pass
        self.cache = os.path.join(cache_dir, "content_cache.json")
        self.content = self._load()

    def _load(self):
        options = [d for d in (read_json(self.cache), read_json(self.bundled)) if d]
        if not options:
            return EMERGENCY_FALLBACK
        return max(options, key=lambda d: d["version"])

    @property
    def version(self):
        return self.content["version"]

    def update(self):
        """Download a newer content.json if one exists. Returns (changed, message)."""
        if not self.url:
            return False, "No update link is set yet."
        try:
            with urllib.request.urlopen(self.url, timeout=8, context=_ssl_context()) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return False, "Could not reach the update link. You are probably offline. Saved content still works."
        if not valid(data):
            return False, "The downloaded file looked wrong, so it was ignored."
        if data["version"] <= self.version:
            return False, "Content is already up to date (version " + str(self.version) + ")."
        try:
            tmp = self.cache + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, self.cache)
        except OSError:
            return False, "Downloaded an update but could not save it on this device."
        self.content = data
        return True, "Updated to content version " + str(data["version"]) + "."

    # --- safety, run on every message ---

    def safety(self, text):
        """Returns a message to show if the text needs urgent help, otherwise None."""
        low = text.lower()
        if any_phrase(low, self.content["self_harm"]):
            return SELF_HARM_MESSAGE
        if any_phrase(low, self.content["urgent"]):
            return URGENT_MESSAGE
        return None

    # --- chat ---

    def find_answers(self, text):
        low = text.lower()
        stems = [stem(t) for t in re.findall(r"[a-z']+", low)]
        scored = []
        for item in self.content["faq"]:
            score = sum(1 for kw in item["keywords"] if keyword_hit(kw, low, stems))
            if score:
                scored.append((score, item))
        scored.sort(key=lambda s: -s[0])
        return [item for _, item in scored]

    def respond(self, text):
        """Returns (reply text, mascot mood). Safety is always checked first."""
        urgent = self.safety(text)
        if urgent:
            return urgent, ("caring" if urgent == SELF_HARM_MESSAGE else "alarmed")
        if is_not_better(text):
            return NOT_BETTER_MESSAGE, "worried"
        if is_recovery(text):
            return RECOVERY_MESSAGE, "celebrate"
        matches = self.find_answers(text)
        if not matches:
            return NOT_FOUND_MESSAGE, "thinking"
        out = format_faq(matches[0])
        related = [m["title"] for m in matches[1:3]]
        if related:
            out += "\n\nYou can also ask about: " + ", ".join(related)
        return out, "happy"

    def reply(self, text):
        """Full chat reply as plain text."""
        return self.respond(text)[0]

    # --- symptom check ---

    def assess(self, text, days, fever, worse, risk):
        """Returns (urgent_message_or_None, reasons). Empty reasons means mild."""
        urgent = self.safety(text)
        if urgent:
            return urgent, []
        reasons = []
        if any_phrase(text.lower(), self.content["clinic_soon"]):
            reasons.append("You described a symptom that needs a proper check")
        if days >= 3:
            reasons.append("It has lasted 3 days or more")
        if fever and days >= 2:
            reasons.append("Fever for 2 days or more")
        if worse:
            reasons.append("It is getting worse")
        if risk and days >= 1:
            reasons.append("Children under 5, pregnant women and older people can get worse quickly")
        return None, reasons

    # --- hygiene ---

    def topics(self):
        return list(self.content["hygiene"])

    def tips(self, topic):
        return self.content["hygiene"].get(topic, [])

    def random_tip(self):
        topic = random.choice(self.topics())
        return topic, random.choice(self.tips(topic))


# ---------- formatting shared by both versions ----------

def format_faq(item):
    out = item["title"] + "\n\n" + item["answer"]
    if item.get("clinic_if"):
        out += "\n\nGo to a clinic if: " + item["clinic_if"]
    out += "\n\nIf you are unsure or it gets worse, visit a clinic."
    return out


def format_assessment(reasons):
    if reasons:
        out = "Please visit a clinic in the next day or two. Reasons:\n"
        out += "\n".join(" - " + r for r in reasons)
    else:
        out = ("This sounds mild, but I cannot be sure. For now:\n"
               " - Rest and drink plenty of clean, safe water.\n"
               " - Go to the clinic if it lasts more than 2 days, gets worse, or you feel unsure.")
    out += ("\n\nSee a clinic straight away if you develop trouble breathing, chest pain, "
            "confusion, fits, or bleeding that will not stop.")
    return out


def format_tips(topic, tips):
    return topic + "\n\n" + "\n".join(" - " + t for t in tips)
