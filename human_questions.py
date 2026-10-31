"""Bounded fan questions and explicit requests for sourced updates.

These authored replies are fictional viewpoints, not personal experiences or
open-ended language-model answers. Unknown questions do not fall back to a feed.
"""
import re


MARS_CHOICES = {
    "hitman": ("I would want the complete route and a working return plan before deciding. A launch is only one stage of the trip.", "Show me the whole trip first. Getting there is only half of it."),
    "assassin": ("A return plan would be my first question. A distant horizon is tempting, but the way home deserves just as much thought.",
                 "A new horizon sounds good. Show me the way home first."),
    "brucewayne": (
        "Only with a credible plan for getting back. A dramatic launch is the easy part to get excited about; the return matters too.",
        "Only with a way back. The launch is cool, but so is getting home."),
    "yoda": (
        "A way home, first I would ask about. Exciting, a new world may be; enough reason to rush, excitement alone is not.",
        "A way home, is there? Ask that first, I would."),
    "chewbacca": (
        "Rrroww. Give the crew a solid way home and the idea gets interesting. A shiny rocket alone is not the whole plan.",
        "Rrroww. Round trip? Maybe. A one-way ticket needs a lot more thought."),
    "lukeskywalker": (
        "For a round trip, I'd be tempted. Exploring a new world sounds exciting; leaving with no way home changes the whole choice.",
        "A round trip? I'd be tempted. A one-way ticket? That's a much harder choice."),
    "chucky": (
        "Mars gets my attention. The ticket needs a return date, though. 'We'll figure that out later' is a terrible ending to the sales pitch.",
        "Show me the return ticket first. 'Good luck out there' is not a travel plan."),
    "tonysoprano": (
        "Before the big launch speech, show me the return plan. A new world sounds interesting; every detail after takeoff still matters.",
        "Mars? Maybe. Show me how the return trip works before the big speech."),
    "killer": (
        "The return plan decides the answer. Exploring is interesting when the excitement does not replace thinking through the consequences.",
        "Only with a clear way back. Think past the launch."),
}
DEFAULT_MARS = (
    "As a fictional what-if, the return plan would decide my answer. A new world is exciting; a one-way trip is a different choice.",
    "For this what-if, I'd ask about a way home first." )


def fan_question_key(text):
    text = text.casefold().replace("’", "'")
    if not re.search(r"\bmars\b", text):
        return None
    # A factual question about a real launch must never become an invented trip.
    if re.search(r"\bwould\s+(?:you|u|y'all|you all|everyone|everybody)\b", text) and re.search(
            r"\b(go|travel|visit|take|live|move|fly|join|accept)\b", text):
        return "mars_trip_choice"
    return None


def fan_reply(text, speaker, style="analytical", content_key=None):
    key = content_key.removeprefix("question:") if content_key else fan_question_key(text)
    if key != "mars_trip_choice":
        return None
    lines = MARS_CHOICES.get(speaker, DEFAULT_MARS)
    return lines[int(style == "plain")], "question:" + key


def requests_update(text, kind):
    """Recognize a request for an update, not merely a topic name in a question."""
    text = text.casefold().replace("’", "'")
    if re.search(r"\b(should (?:i|we|you)|would (?:you|u)|do you think|your (?:opinion|take)|"
                 r"worth (?:it|buying)|a buy|good investment)\b", text):
        return False
    if re.search(r"\b(news|headlines?|updates?|latest|fresh|recent|newest)\b|"
                 r"\bwhat(?:'s| is)? (?:new|happening|going on)\b", text):
        return True
    patterns = {
        "crypto": r"\b(prices?|quotes?|figures?|trading|how much)\b|\bwhat\b.+\bworth\b",
        "sports": r"\b(scores?|results?|fixtures?|schedule|scheduled|who won|who's playing|who is playing)\b",
        "fragment": r"\b(sales?|sold|who bought|auction results?)\b",
    }
    return bool(re.search(patterns.get(kind, r"(?!)"), text))


SUBJECTS = (
    r"\btesla\b", r"\bspacex\b", r"\bstarlink\b", r"\bxai\b", r"\bgrok\b", r"\bmars\b",
    r"\bnba\b", r"\bnhl\b", r"\bmlb\b", r"\bnfl\b", r"\bmls\b", r"\bwnba\b",
)


def matches_requested_subject(text, question):
    subjects = [pattern for pattern in SUBJECTS if re.search(pattern, question, re.I)]
    usernames = re.findall(r"(?<!\w)@[A-Za-z0-9_]{2,32}\b", question)
    # Addressing a bot chooses a voice; it is not a request for a username sale.
    if not re.search(r"\b(fragment|username|sales?|sold|bought)\b", question, re.I):
        usernames = []
    return (all(re.search(pattern, text, re.I) for pattern in subjects)
            and all(re.search(re.escape(name) + r"\b", text, re.I) for name in usernames))
