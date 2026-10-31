"""Daily reading styles for disclosed fan personas; facts and idea keys stay fixed."""
import re
from fan_voices import DISCUSSION_VOICES
from human_questions import fan_reply


def daily_styles(speakers, day):
    """A balanced split that reverses each local day, independent of input order."""
    names = sorted(set(speakers))
    return {name: ("analytical" if index % 2 == day.toordinal() % 2 else "plain")
            for index, name in enumerate(names)}


# Same discussion ideas as conversation.py, with shorter authored wording.
# Changing reading style never creates a new content key or resets used history.
PLAIN_NAMES = ("brucewayne", "yoda", "chewbacca", "lukeskywalker", "chucky")
PLAIN_DISCUSSIONS = {
    "order66_loss": (
        "Yoda feels the Jedi dying during Order 66. That scene is so sad.",
        "Sad, that Order 66 scene is. The Jedi's loss, Yoda feels.",
        "Yoda looks so sad during Order 66. That part is hard to watch.",
        "Yoda feels the loss during Order 66. It is a sad, quiet moment.",
        "Yoda's Order 66 scene is sad. Even I stop joking for that part."),
    "presence": (
        "Vader stands still and the whole room watches. That is control.",
        "Still, Vader stands. Nervous, everyone else gets.",
        "Rrroww. Vader does nothing and somehow owns the room.",
        "Vader barely moves. It makes his next move matter more.",
        "The cape shows up. Everyone gets quiet. Nice trick."),
    "redemption": (
        "Vader's last choice matters more to me than his power.",
        "His father, Luke still sees. Give up, he will not.",
        "Luke never gives up on his dad. That part stays with me.",
        "Luke still sees good in his father. That is why the ending works.",
        "All that armor, and the ending is about his son."),
    "loyalty": (
        "Chewie comes back for his friends. I would want him on my team.",
        "There for his friends, Chewie stays. Trust him, you can.",
        "Stay with your crew. Chewie gets it.",
        "Chewie keeps his friends safe. The team needs that.",
        "Bad plan? Take Chewie. At least he will have your back."),
    "wisdom": (
        "Yoda gets people to listen without shouting. I respect that.",
        "Small, a teacher can be. Listen first, you should.",
        "Yoda gets the room to listen. No roaring needed.",
        "Yoda makes Luke slow down and listen. He needs that lesson.",
        "Tiny teacher. Very long patience. Luke is lucky."),
    "music": (
        "The Imperial March sets the mood before Vader even talks.",
        "Before words, the music speaks. Fear, you can hear.",
        "Rrroww. That Vader music makes any hallway feel scary.",
        "The Imperial March starts and the whole scene changes.",
        "Vader has great entrance music. Hard to beat that."),
    "duel_pacing": (
        "I watch the pauses in a duel. That is when the next move gets tense.",
        "Between strikes, watch closely. Much, a pause can show.",
        "A slow duel can still be tense. Watch their feet.",
        "I like having time to read their faces during a duel.",
        "A slow duel gives everyone time to worry. Works for me."),
    "leia_leadership": (
        "When things go wrong, Leia makes a plan. The team needs her.",
        "In trouble, a clear plan Leia makes. Useful, that is.",
        "Leia gets straight to the plan. No time wasted.",
        "Leia is planning the next move while everyone else reacts.",
        "Everyone panics. Leia gets things done. Good system."),
    "r2_solutions": (
        "R2 gets doors and machines to work. Big plans need those small fixes.",
        "A door opens. A machine works. Much, R2 can change.",
        "Machine trouble? Keep R2 close.",
        "R2 finds small fixes when the whole plan seems stuck.",
        "R2 spends the trip fixing things. Give that droid a break."),
    "opening_scale": (
        "That first Star Destroyer shot shows how big the danger is.",
        "Huge, that first Star Destroyer looks. Small, the other ship feels.",
        "Rrroww. That first Star Destroyer just keeps going.",
        "The opening ship shot tells you the odds before anyone speaks.",
        "That giant ship enters and keeps entering. We get it, Empire."),
    "lightsaber_colour": (
        "Red and blue blades make a fight easy to follow.",
        "Red and blue, the blades glow. Easy to follow, the fight is.",
        "Bright blades in a dark room. Easy to see who is where.",
        "I like the red and blue blades against a dark room.",
        "Two glowing blades. Dark room. Great way to light a fight."),
    "cloud_city_reveal": (
        "The Cloud City reveal changes what the whole fight means.",
        "In Cloud City, personal the fight becomes. Changed, everything feels.",
        "Cloud City turns the whole fight into a family problem.",
        "Luke learns the truth in the middle of a fight. Rough timing.",
        "Cloud City is a very bad day for a family talk."),
    "breathing_sound": (
        "Vader's breathing warns you before he shows up.",
        "Hear the breathing, you do. Close, Vader must be.",
        "Rrroww. Hear that breathing? Trouble is close.",
        "You hear Vader before you see him. That still works.",
        "That breathing is a warning. No speech needed."),
    "suit_life_support": (
        "Vader needs that suit to stay alive. His armor has a cost.",
        "Alive, the suit keeps Vader. Need it, he does.",
        "That armor keeps Vader alive. It is more than a tough look.",
        "Vader looks strong, but he needs his suit to live.",
        "The scary armor is also keeping him alive. That part matters."),
    "anakin_hero_past": (
        "Anakin was a hero before Vader. His fall hits harder that way.",
        "A hero, Anakin once was. Harder, his fall feels.",
        "Anakin used to help people. That makes Vader's story sadder.",
        "Seeing Anakin as a hero makes his later choices hurt more.",
        "Anakin had a good side long before that black cape."),
    "padme_fear": (
        "Anakin fears losing Padmé. That fear leads him into bad choices.",
        "Lose Padmé, Anakin fears. Bad choices, that fear brings.",
        "Anakin is so scared of losing Padmé that he makes things worse.",
        "Anakin wants to save Padmé. Fear gets in the way of good choices.",
        "Anakin lets fear drive. That goes badly."),
    "vader_pilot": (
        "Vader flies into battle himself. He does more than give orders.",
        "Into battle, Vader flies. Give orders only, he does not.",
        "Vader goes out and flies the fight himself. That is a threat.",
        "Vader taking the controls puts him right in the fight.",
        "Vader can fly too. As if the cape was not enough."),
    "tie_silhouette": (
        "Vader's TIE fighter has a shape you can spot right away.",
        "Different, Vader's fighter looks. Spot it quickly, you can.",
        "Vader's fighter stands out. Hard to miss that shape.",
        "I can pick Vader's TIE out right away. Great design.",
        "Even Vader's ship needs its own look. Of course it does."),
    "luke_farm_beginning": (
        "Luke starts on a farm. It gives that huge story a small start.",
        "On a farm, Luke starts. Far, the story takes him.",
        "Luke goes from farm work to all that. Big change.",
        "Luke starting on a farm makes the big adventure feel closer.",
        "Luke had farm chores. Then the galaxy got involved."),
    "dagobah_failures": (
        "Luke fails during training. Learning takes work, even for him.",
        "Fail in training, Luke does. Keep learning, he must.",
        "Luke gets training wrong too. He has to keep at it.",
        "Luke struggles on Dagobah. I like that learning is hard for him.",
        "Luke does not ace every lesson. Yoda has work to do."),
    "yoda_teaching_centuries": (
        "Yoda trained Jedi for over 800 years. That is a lot of students.",
        "For over 800 years, Jedi Yoda trained. Many students, that is.",
        "Over 800 years of teaching Jedi. Yoda has seen a lot.",
        "Yoda taught Jedi for over 800 years. That is some patience.",
        "Over 800 years teaching Jedi. Imagine the homework pile."),
    "yoda_species_mystery": (
        "Yoda's species is still unknown. I like keeping some mystery.",
        "Unknown, Yoda's species remains. Some mystery, keep we can.",
        "We still do not know Yoda's species. That is part of the fun.",
        "I like that we do not have every answer about Yoda.",
        "Yoda keeps his species a mystery. Fair enough, little guy."),
    "leia_adoption": (
        "Bail Organa raised Leia. Her family story matters too.",
        "Raised Leia, Bail Organa did. Important, that bond is.",
        "Bail raised Leia. Family is more than a name.",
        "Bail Organa is the dad who raised Leia. I would not leave him out.",
        "Big family tree. Bail still did the parenting."),
    "skywalker_twins": (
        "Luke and Leia are twins. Two paths lead back to one family.",
        "Twins, Luke and Leia are. Different, their paths become.",
        "Luke and Leia share a family. They still take different paths.",
        "Luke and Leia grow up apart. Their stories still come together.",
        "Same family. Very different starts. Those twins had a lot to catch up on."),
    "han_yavin_return": (
        "Han comes back at Yavin. His choice shows who matters to him.",
        "Return at Yavin, Han does. His friends, he chooses.",
        "Han comes back for the fight at Yavin. That says a lot.",
        "Han returning at Yavin is when his choice becomes clear to me.",
        "Han talks tough. Then he comes back at Yavin. Good move."),
    "han_hoth_rescue": (
        "Han goes into Hoth's cold for Luke. That is a good friend.",
        "Into Hoth's cold, Han goes. Find Luke, he must.",
        "Han goes out in that cold for Luke. He looks after his crew.",
        "Han risking the cold to find Luke is a great friendship scene.",
        "Hoth weather is awful. Han still goes out for Luke."),
    "falcon_hyperdrive": (
        "The Falcon's hyperdrive fails when they need it. Escape gets harder.",
        "Fail, the Falcon's hyperdrive does. Easy, escape will not be.",
        "Rrroww. That hyperdrive picks the worst time to quit.",
        "The Falcon's bad hyperdrive keeps an easy escape out of reach.",
        "The Falcon's hyperdrive has terrible timing. Every trip is a project."),
    "falcon_modifications": (
        "The Falcon looks worn out. Its upgrades tell a different story.",
        "Old, the Falcon looks. More than its looks, it can do.",
        "Do not judge the Falcon by its dents. There is more under the hull.",
        "I like that the Falcon can do more than its looks suggest.",
        "The Falcon looks rough. The upgrades are doing the work."),
    "deathstar_weakness": (
        "A huge Death Star has one small weak point. Size is not everything.",
        "Huge, the Death Star is. A small weak point, it still has.",
        "All that Death Star armor. One small opening still matters.",
        "The Death Star is huge, but its weak point is small. I like that contrast.",
        "Huge space station. Tiny weak point. Expensive mistake."),
    "deathstar_secrecy": (
        "The Death Star plans can change the fight. Information has power.",
        "Change the fight, those plans can. Powerful, knowledge is.",
        "Those Death Star plans matter as much as a weapon.",
        "Getting the Death Star plans changes what the rebels can do.",
        "The Empire builds a giant weapon. The plans become a huge problem."),
    "r2_bravery": (
        "R2 rolls toward danger. Small does not mean scared.",
        "Toward danger, R2 rolls. Brave, that little droid is.",
        "R2 sees danger and keeps rolling. That takes nerve.",
        "R2 keeps helping even when it is risky. I respect that.",
        "Little wheels. Big courage. R2 does not hide."),
    "r2_generations": (
        "R2 served Padmé, Anakin and Luke. He links their stories.",
        "Padmé, Anakin and Luke, R2 served. Much history, he knows.",
        "R2 was there for Padmé, Anakin and Luke. He has seen a lot.",
        "R2 knew Padmé and Anakin before he ever met Luke.",
        "R2 knows more family history than most of that family."),
    "threepio_builder": (
        "Young Anakin built C-3PO. He had a talent for making things.",
        "Built C-3PO, young Anakin did. Help people, he wanted to.",
        "Anakin built C-3PO as a kid. That is a neat part of his story.",
        "Young Anakin builds Threepio to help. It is a kind side of him.",
        "Before the cape, Anakin built a very chatty droid."),
    "threepio_translation": (
        "Threepio knows languages. Some problems need words, not weapons.",
        "Other voices, Threepio understands. A useful skill, that is.",
        "Threepio helps people understand each other. The team needs that.",
        "Threepio's languages can help where a weapon cannot.",
        "Threepio brings the languages. And all the worrying."),
    "walker_intimidation": (
        "The AT-ATs tower over Hoth. The defenders look exposed.",
        "Tall, the AT-ATs stand. Small, the defenders look.",
        "Those giant walkers make Hoth a rough place to stand.",
        "The AT-ATs make the people defending Hoth look so small.",
        "Snow, cold, giant walking tanks. Hoth has a lot going on."),
    "walker_transport": (
        "An AT-AT carries troops and fights. It has more than one job.",
        "Carry troops and fight, an AT-AT can. Two jobs, it has.",
        "The AT-AT brings troops with the armor. Big moving problem.",
        "AT-ATs carry troops too. That changes how I see the attack.",
        "An AT-AT is a troop ride with weapons. Very unfriendly bus."),
}

# The shared idea key stays unchanged when a new daily reading style is used.
from vader_discussions import CATALOG as FRESH_VADER
PLAIN_DISCUSSIONS.update({key: tuple(voices[name][1] for name in PLAIN_NAMES)
                          for key, voices in FRESH_VADER.items()})

PLAIN_THREADS = {
    "wookiee_alarm": (
        "A Chewie alarm clock would make snooze a scary button.",
        "Rrroww. A Chucky clock would make people move out. Different customers."),
    "yoda_waiting_room": (
        "A waiting room run by Yoda sounds like a very long visit.",
        "A magazine, read. Six words, the advice may take. Quick enough, that is."),
    "presence_or_wisdom": (
        "Vader walks in and owns the scene. That gets my vote.",
        "Notice a doorway, you do. Learn from a good teacher, you can. My pick, Yoda is."),
    "last_choice": (
        "Vader's last choice is why I like his story. Luke still gives him a chance.",
        "That ending works. The man under the mask matters most."),
    "crew_first": (
        "Rrroww. Best character? Pick the one who comes back for his friends.",
        "Then Chewie has a strong case. The crew can count on him."),
    "cape_and_helmet": (
        "Vader's cape needs its own credit. So dramatic.",
        "The helmet hides his face. That makes me watch how he moves."),
    "quiet_before_duel": (
        "I like the silence before a Vader fight. Everyone looks worried.",
        "Wait for his next move, they must. Scary, that pause gets."),
    "power_or_restraint": (
        "Win a fight, strength can. Pick the right fight, wisdom must.",
        "So strongest and best character are two different things. Fair."),
    "station_and_people": (
        "The Death Star shows how big the Empire is. Vader makes it feel close.",
        "And a few friends still stand up to it. That is the part I like."),
    "trusting_han": (
        "Rrroww. Han says he has a plan. Watch who stays when it goes wrong.",
        "Sound sure, anyone can. Stay with your friends, harder that is."),
    "patience_contest": (
        "Yoda wins at patience. I lose before the rules end.",
        "Listen to the rules first, you could. A start, that would be."),
    "ranking_spreadsheet": (
        "Some people put their movie rankings in a chart. I like the effort.",
        "That sounds like your way of saying you made one, Bruce."),
    "dramatic_whisper": (
        "Chewie wins the loud entrance prize. Can the rest of us get a mic?",
        "Rrroww. Quit the spooky whispers and speak up."),
    "hairbrush_transfer": (
        "Chewie, your hairbrush wants a new job. Blame it, I do not.",
        "Rrroww. Hair tips from a picture with three hairs. Thanks."),
}

PLAIN_RAP = {
    "delivery": "YoungBoy can switch from singing to a rough voice. I like that mix.",
    "catalog": "My first YoungBoy song pick depends on the mood. He has a lot to choose from.",
    "ranking": "YoungBoy is my fan pick for the best. The feeling in his voice is a big reason.",
}

# Small, meaning-preserving substitutions, only in an unquoted headline.
# Do not rewrite names, numbers, uncertainty, status, dates, sources or links.
PLAIN_WORDS = {
    "approximately": "about", "additional": "more", "assistance": "help",
    "commences": "starts", "commenced": "started", "commence": "start",
    "subsequently": "later",
    "prior to": "before", "in order to": "to", "numerous": "many",
    "utilizes": "uses", "utilized": "used", "utilize": "use",
    "utilises": "uses", "utilised": "used", "utilise": "use",
}
PLAIN_BUSINESS = {"acquires": "buys", "acquired": "bought", "acquire": "buy",
                  "acquisition of": "purchase of"}


def _plain_headline(line, kind):
    # Preserve quoted wording verbatim. Apostrophes in contractions are fine.
    parts = re.split(r'''("[^"]*"|“[^”]*”|‘[^’]*’|(?<!\w)'[^'\n]+'(?!\w))''', line)
    words = dict(PLAIN_WORDS)
    if kind == "deals":
        words.update(PLAIN_BUSINESS)
    pattern = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b", re.I)
    def replace(match):
        if match.start() and match.group()[0].isupper():
            return match.group()
        value = words[match.group().casefold()]
        return value.capitalize() if match.group()[0].isupper() else value
    return "".join(part if index % 2 else pattern.sub(replace, part)
                   for index, part in enumerate(parts))


def render_style(text, kind, content_key, speaker, style):
    """Render one idea. Service/pin routing and factual uncertainty are unchanged."""
    if kind in ("service", "pin", "general"):
        return text
    if kind == "fan":
        item = fan_reply(text, speaker, style, content_key)
        return item[0] if item else text
    if kind == "crypto":
        def quote(match):
            symbol, price, change = match.groups()
            name = {"BTC": "Bitcoin", "ETH": "Ethereum"}.get(symbol, symbol) if style == "plain" else symbol
            amount = change.lstrip("+-")
            if float(change) == 0:
                return f"{name} is at ${price}, unchanged over 24 hours ({amount}%)."
            direction = "down" if change.startswith("-") else "up"
            variant = (sum(text.encode()) + ("TON", "BTC", "ETH").index(symbol)) % 3
            if speaker == "yoda" and symbol == "TON":
                return f"At ${price}, {name} sits. {direction.capitalize()} {amount}% over 24 hours, it is."
            if style == "plain":
                choices = (f"{name} is at ${price}, {direction} {amount}% over 24 hours.",
                           f"{name}'s at ${price}. That's {amount}% {'lower' if direction == 'down' else 'higher'} over 24 hours.",
                           f"${price} for {name}, {direction} {amount}% over 24 hours.")
            else:
                choices = (f"{name}'s at ${price} — {change}% over 24h.",
                           f"{name} is trading at ${price}, {direction} {amount}% in 24h.",
                           f"${price} for {name}; its 24h move is {change}%.")
            return choices[variant]
        return re.sub(r"^(TON|BTC|ETH) \$([\d,]+\.\d+) · 24h ([+-]\d+\.\d+)%$",
                      quote, text, flags=re.M)
    if kind in ("world", "elon", "deals", "rap") and not (content_key or "").startswith("discussion:"):
        lines = text.splitlines()
        if lines:
            line = _plain_headline(lines[0], kind) if style == "plain" else lines[0]
            # A headline's 'to acquire' announces a plan, not a completed deal.
            # Restrict this rewrite to unquoted, affirmative company headlines.
            if kind == "deals" and not re.search(r'''["“”‘’]|(?<!\w)'[^'\n]+'(?!\w)''', line):
                planned = re.match(r"^(.+?)\s+to\s+(?:acquire|buy)\s+(.+)$", line, re.I)
                if planned and not re.search(r"\b(how|why|whether|plans?|wants?|hopes?|seeks?|may|might|not|denies?|reportedly|claims?)\b", planned[1], re.I):
                    line = planned[1] + " plans to buy " + planned[2].rstrip(".") + "."
                line = re.sub(r"(\$[\d,.]+)\s+(Million|Billion)\b", lambda m: m[1] + " " + m[2].lower(), line)
            lines[0] = line
        return "\n".join(lines)
    if style != "plain":
        return text
    key = content_key or ""
    prefix = "discussion:starwars:"
    if key.startswith(prefix):
        catalog = DISCUSSION_VOICES.get(speaker, {})
        if key[len(prefix):] in catalog:
            return catalog[key[len(prefix):]][1]
        row = PLAIN_DISCUSSIONS.get(key[len(prefix):])
        if row and speaker in PLAIN_NAMES:
            return row[PLAIN_NAMES.index(speaker)]
    if key.startswith("roleplay:"):
        parts = key.split(":")
        if len(parts) == 3:
            row = PLAIN_THREADS.get(parts[1])
            if row and parts[2] in ("0", "1"):
                return row[int(parts[2])]
    if key.startswith("discussion:rap:"):
        body = PLAIN_RAP.get(key.rsplit(":", 1)[-1])
        if body:
            return body
    return text
