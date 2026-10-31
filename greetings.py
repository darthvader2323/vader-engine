"""Short greetings for the disclosed characters, never a crowd response."""
import re


LINES = {
    "brucewayne": (
        "Hey, welcome in 👋", "Hello there. Good to have you here.",
        "Hey! What's on your mind?", "Aye, welcome to the room. How's it going?",
        "Hey, glad you found us. What's good?", "Welcome aboard. How's your day been?",
        "Come on in. What are we talking about today?", "Hey there. Make yourself at home."),
    "yoda": (
        "Welcome, you are 👋", "Good to have you here, it is.",
        "Hello there. Join the conversation, you can.", "Aye, arrived you have. How goes your day?",
        "A seat for you, we have. What's good?", "New to the room, you are. Say hello, you can.",
        "Come in, you should. A good chat, we can have.", "Among friends of the saga, welcome you are."),
    "chewbacca": (
        "Rrroww! Hey, welcome in 👋", "Hey there. Room for one more.",
        "Rrroww. What's good?", "Aye gang, welcome! How are you doing?",
        "Rrroww! Come hang with the crew.", "Hey, you made it. How's your day going?",
        "Welcome aboard the chat. Rrroww!", "Good to see a new face. Pull up a seat."),
    "lukeskywalker": (
        "Hey, glad you stopped by 👋", "Welcome in. Good to have you here.",
        "Hey there! Pull up a seat.", "Yo, welcome to the chat. What's up with you?",
        "Glad you found the room. How's everything?", "Hey, jump in whenever you're ready.",
        "Welcome, you picked a good time to join.", "Hey there, how's your day been so far?"),
    "chucky": (
        "Yo! Welcome to the room 👋", "Hey, you made it. Pull up a seat.",
        "What's up! Good to have you here.", "Aye g, welcome in. How are you?",
        "Yo, another seat at the table. What's good?", "Hey, come hang out. We were just getting started.",
        "Welcome to the room. Bring your best Star Wars take.", "There you are! How's life treating you?"),
    "tonysoprano": (
        "Hey, come on in. What's on your mind?", "There you are. Pull up a chair 👋",
        "Hey. Good to have you at the table.", "Aye, welcome g. How's everything?",
        "Come sit down. What've you got for the room?", "Hey, glad you made it. How are you doing?",
        "Welcome in. There's always room for another Star Wars argument.", "Yo, take a seat. What's good today?"),
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
