"""Authored character discussions, conservative repeat checks and source links."""
import hashlib
import html
import re

NEWS_KINDS = {"world", "elon", "deals", "rap", "crypto", "sports", "fragment"}
SIMILARITY_KINDS = {"world", "elon", "deals", "rap", "starwars", "fragment"}
STOP_WORDS = set("a an and are as at be been by for from has have in is it of on or that the this to was were will with".split())

# Each idea has one shared key, regardless of which character delivers it.
# Questions are occasional; these are not interchangeable engagement banners.
DISCUSSIONS = [
    ("presence", {
        "default": "Vader can hold a scene through stillness. The pause before he moves does a lot of the work.",
        "yoda": "Still, Vader stands. Uncomfortable, the room becomes. Much can a pause accomplish.",
        "lukeskywalker": "Vader hardly needs to move to change a scene. That confidence makes every small movement count.",
        "chewbacca": "Rrroww. Vader standing completely still is somehow the loudest thing in the room.",
        "brucewayne": "Vader controls the space before the fight begins. Watch how the other characters react to his silence.",
        "chucky": "The cape arrives, the room goes quiet. That is an entrance with excellent timing.",
        "darthvader": "A measured pause can command more attention than a speech.",
    }),
    ("redemption", {
        "default": "Luke reaching Anakin beneath the armor gives Vader's ending its emotional weight.",
        "yoda": "Reach Anakin, Luke could. Patient, that hope remained.",
        "lukeskywalker": "Luke keeps seeing his father beneath the armor. That hope is what makes the ending work for me.",
        "chewbacca": "Luke kept a place for his father. That is the part of Vader's ending that stays with me.",
        "brucewayne": "Vader's final choice changes how the earlier scenes land. Consequences give the ending its weight.",
        "chucky": "Vader's final choice still lands. All that armor, and the ending turns on something personal.",
        "darthvader": "The armor carries a reputation. The final choice carries the legacy.",
    }),
    ("loyalty", {
        "default": "Chewbacca's loyalty gives the group a steady center when everything around them falls apart.",
        "yoda": "Steady, Chewbacca remains. Trust such as that, a team needs.",
        "lukeskywalker": "Chewie keeps showing up for the people around him. That steadiness holds the team together.",
        "chewbacca": "Stay close to your crew. Chewie makes that look simple.",
        "brucewayne": "Chewbacca is dependable under pressure. A team needs someone whose loyalty is already settled.",
        "chucky": "Chewie is the person you want beside you when the plan falls apart. Very sensible casting for a best friend.",
        "darthvader": "Loyalty becomes valuable when circumstances make it difficult.",
    }),
    ("wisdom", {
        "default": "Yoda's size makes his authority more striking. The scene asks you to pay attention to judgment.",
        "yoda": "Small, a teacher may appear. Listen carefully, a student must.",
        "lukeskywalker": "Yoda makes Luke slow down and listen. That lesson changes the pace of the story as much as the training.",
        "chewbacca": "Yoda gets a whole room listening without raising his voice. Rrroww, that takes skill.",
        "brucewayne": "Yoda's authority comes through patience. The restraint in those scenes is deliberate.",
        "chucky": "Tiny teacher, enormous patience. Yoda has a remarkable tolerance for impatient students.",
        "darthvader": "Patience reveals what impatience leaves exposed.",
    }),
    ("music", {
        "default": "The Imperial March gives Vader a presence before the dialogue begins. The brass does so much storytelling.",
        "yoda": "Before a word, the music speaks. Through brass, fear travels.",
        "lukeskywalker": "That first brass phrase in the Imperial March changes the mood immediately. The music carries its own warning.",
        "chewbacca": "Rrrroww. The Imperial March comes in and suddenly every corridor feels smaller.",
        "brucewayne": "Listen to the rhythm beneath the Imperial March. It gives Vader's movement a sense of inevitability.",
        "chucky": "The Imperial March is doing an outrageous amount of intimidation. Excellent entrance music.",
        "darthvader": "The Imperial March announces an arrival with remarkable efficiency.",
    }),
    ("duel_pacing", {
        "default": "The slower original-trilogy duels leave room for hesitation and expression. Which style of duel holds your attention?",
        "yoda": "Between strikes, hesitation lives. In those pauses, watch the duel unfold.",
        "lukeskywalker": "The pauses in the original-trilogy duels give the choices room to breathe. I like having time to read the faces.",
        "chewbacca": "A pause in a duel can get tense fast. Watch the feet and the distance between them.",
        "brucewayne": "Distance and timing tell a story during a duel. The pauses make intent easier to read.",
        "chucky": "A slow duel gives everybody time to realize the situation is terrible. I appreciate the suspense.",
        "darthvader": "Distance, timing, patience. A duel reveals all three.",
    }),
    ("leia_leadership", {
        "default": "Leia gives the group direction in a crisis. Her practical decisions keep the adventure moving.",
        "yoda": "In a crisis, clear a direction becomes through Leia. Valuable, that clarity is.",
        "lukeskywalker": "Leia is usually already making the next decision while everyone else is reacting. The group needs that momentum.",
        "chewbacca": "Leia gets straight to the next move. Useful quality when the room is filling with trouble.",
        "brucewayne": "Leia organizes action under pressure. That is the practical side of leadership those scenes show well.",
        "chucky": "Leia is surrounded by chaos and still gets to the next decision first. Someone has to keep the adventure on schedule.",
        "darthvader": "Leia's resolve gives her decisions unusual force.",
    }),
    ("r2_solutions", {
        "default": "R2-D2 solves so many practical problems along the way. The adventure depends on somebody getting the machinery to cooperate.",
        "yoda": "A door, a signal, a machine. Much can R2 change through small solutions.",
        "lukeskywalker": "R2 keeps turning impossible situations into practical problems. I like how much of the adventure depends on that ingenuity.",
        "chewbacca": "Keep R2 close when the machinery starts arguing. That little droid gets things done.",
        "brucewayne": "R2's contribution is often operational: access, repairs, information. Those details make the larger plan possible.",
        "chucky": "R2 spends half the adventure persuading machinery to cooperate. The little droid deserves a quieter shift.",
        "darthvader": "A small technical solution can alter an entire operation.",
    }),
    ("opening_scale", {
        "default": "The opening Star Destroyer shot establishes the Empire's scale immediately. That sense of size still works.",
        "yoda": "Across the opening frame, the Star Destroyer stretches. Small, the pursued ship feels.",
        "lukeskywalker": "The opening Star Destroyer shot tells you the size of the problem before anyone explains it.",
        "chewbacca": "That opening Star Destroyer just keeps coming across the frame. Rrroww, that is a lot of ship.",
        "brucewayne": "The opening shot communicates the balance of power through scale. It establishes the threat very economically.",
        "chucky": "The opening Star Destroyer keeps going and going. A spectacular way to announce an unfair fight.",
        "darthvader": "The opening Star Destroyer shot makes the Empire's scale unmistakable.",
    }),
    ("lightsaber_colour", {
        "default": "Red and blue lightsabers make a confrontation readable at a glance. The color contrast does quiet visual work.",
        "yoda": "Before the blades meet, their colors speak. Clear, a confrontation becomes.",
        "lukeskywalker": "The red and blue blades give the scene an immediate visual contrast. It is such an effective design choice.",
        "chewbacca": "Two bright blades in a dark room make the action easy to follow. Simple design, strong effect.",
        "brucewayne": "Lightsaber color separates the figures during a confrontation. The clarity of that design holds up.",
        "chucky": "A dark room and two glowing blades. The lighting department gets to have some fun.",
        "darthvader": "A red blade makes an immediate impression against a dark setting.",
    }),
    ("cloud_city_reveal", {
        "default": "The Cloud City reveal changes the meaning of the confrontation in the middle of the scene. That shift is the memorable part.",
        "yoda": "In Cloud City, changed the confrontation becomes. Personal, the conflict grows.",
        "lukeskywalker": "The Cloud City reveal changes what Luke thinks the fight is about while he is still in it. That is a brutal turn.",
        "chewbacca": "Cloud City turns the conflict personal in an instant. The whole scene feels different after the reveal.",
        "brucewayne": "The Cloud City reveal changes the stakes without changing the location. The scene makes that shift carry.",
        "chucky": "Cloud City delivers a family revelation at the absolute worst possible moment. Remarkable timing for a terrible day.",
        "darthvader": "Cloud City changes the terms of the confrontation in a single exchange.",
    }),
]
RAP_DISCUSSIONS = [
    ("delivery", "YoungBoy's shifts between melody and a rougher delivery are a big part of the appeal for me."),
    ("catalog", "With YoungBoy, the track I would introduce first depends on the mood. His catalog gives a fan plenty of directions to choose."),
    ("ranking", "YoungBoy is my fan pick in a GOAT discussion. Emotional delivery carries a lot of weight in that ranking."),
]


def discussion_items(kind, speaker):
    if kind == "starwars":
        return [(voices.get(speaker, voices["default"]), "discussion:starwars:" + idea)
                for idea, voices in DISCUSSIONS]
    if kind == "rap":
        return [(text, "discussion:rap:" + idea) for idea, text in RAP_DISCUSSIONS]
    return []


def signature(text):
    # Use the headline/observation, excluding URL and publisher/date formatting.
    line = html.unescape(text.splitlines()[0]).casefold().replace("’", "'")
    words = re.findall(r"\w+", line, flags=re.UNICODE)
    terms = {word for word in words if len(word) > 2 and word not in STOP_WORDS}
    short_hash = lambda word: hashlib.sha256(word.encode()).hexdigest()[:20]
    return {"terms": sorted(short_hash(word) for word in terms),
            "numbers": sorted(short_hash(word) for word in words if any(c.isdigit() for c in word)),
            "negative": bool(re.search(r"\b(no|not|never|denies|denied|cannot|isn't|won't|can't)\b", line))}


def similar(left, right):
    if left.get("numbers") != right.get("numbers") or left.get("negative") != right.get("negative"):
        return False
    a, b = set(left.get("terms", [])), set(right.get("terms", []))
    if min(len(a), len(b)) < 5:
        return a == b and len(a) >= 2
    common = len(a & b)
    return 2 * common / (len(a) + len(b)) >= 0.82


def compact_sources(text, kind):
    """Keep factual text and dates; attach the source URL to its metadata line."""
    if kind not in NEWS_KINDS:
        return text, []
    lines = text.splitlines()
    for index in range(len(lines) - 1, 0, -1):
        url = lines[index].strip()
        label = lines[index - 1]
        if not re.fullmatch(r"https://\S+", url) or not label.strip():
            continue
        prefix = "\n".join(lines[:index - 1])
        offset = len((prefix + ("\n" if prefix else "")).encode("utf-16-le")) // 2
        del lines[index]
        return "\n".join(lines), [{"type": "text_link", "offset": offset,
                                     "length": len(label.encode("utf-16-le")) // 2, "url": url}]
    return text, []
