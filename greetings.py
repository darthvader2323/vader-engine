"""Short greetings for the disclosed characters, never a crowd response."""
import re


LINES = {
    "brucewayne": ("Hey, welcome in 👋", "Hello there. Good to have you here.", "Hey! What's on your mind?"),
    "yoda": ("Welcome, you are 👋", "Good to have you here, it is.", "Hello there. Join the conversation, you can."),
    "chewbacca": ("Rrroww! Hey, welcome in 👋", "Hey there. Room for one more.", "Rrroww. What's good?"),
    "lukeskywalker": ("Hey, glad you stopped by 👋", "Welcome in. Good to have you here.", "Hey there! Pull up a seat."),
    "chucky": ("Yo! Welcome to the room 👋", "Hey, you made it. Pull up a seat.", "What's up! Good to have you here."),
}


def is_greeting(text, addresses=()):
    """Match a standalone greeting, not a service request or substantive comment."""
    text = text.strip().casefold().replace("’", "'")
    for address in sorted(set(addresses), key=len, reverse=True):
        match = re.match(r"^" + re.escape(address.casefold()) + r"[\s,!?:]+", text)
        if match:
            text = text[match.end():].strip()
            break
    text = re.sub(r"[!?.,…👋🙂😊]+$", "", text).strip()
    return bool(re.fullmatch(
        r"(?:/hello|hey+|hi+|hello|yo+|sup|what'?s up|what'?s good|"
        r"good (?:morning|afternoon|evening))(?:\s+(?:everyone|everybody|all|guys))?", text))


def greeting_line(speaker, number):
    lines = LINES.get(speaker, ("Hey, welcome in 👋", "Hello there. Good to have you here."))
    return lines[number % len(lines)]
