"""Authored character discussions, conservative repeat checks and source links."""
import hashlib
import html
import re
from fan_voices import DISCUSSION_VOICES

NEWS_KINDS = {"world", "elon", "deals", "rap", "crypto", "sports", "fragment"}
SIMILARITY_KINDS = {"world", "elon", "deals", "rap", "starwars", "fragment", "fan"}
STOP_WORDS = set("a an and are as at be been by for from has have in is it of on or that the this to was were will with".split())

# Short, authored fan-persona exchanges. Each has a different argument in the
# second turn, not a stock agreement or an endorsement of the group owner.
ROLEPLAY_THREADS = [
    ("presence_or_wisdom", (
        ("brucewayne", "For screen presence, Vader gets my vote. He can make a doorway feel like the whole scene."),
        ("yoda", "Notice an entrance, everyone does. Change a person's mind, a good teacher can. My vote, there it goes."))),
    ("last_choice", (
        ("lukeskywalker", "Vader's last choice is why I keep coming back to his story. Luke leaves room for him to choose differently."),
        ("chucky", "That ending works because the mask finally stops being the most interesting thing about him."))),
    ("crew_first", (
        ("chewbacca", "Rrroww. Best character? I'm judging who you would actually trust to come back for the crew."),
        ("brucewayne", "By that measure, Chewie has a strong case. Being reliable changes what everyone else can risk."))),
    ("cape_and_helmet", (
        ("chucky", "Vader's cape deserves its own credit. It does a ridiculous amount of dramatic work."),
        ("brucewayne", "The helmet does the opposite: it hides his expression. You end up watching his posture instead."))),
    ("quiet_before_duel", (
        ("lukeskywalker", "I like the quiet before a Vader duel as much as the fight. Nobody in that room seems comfortable."),
        ("yoda", "Wait for the next move, they must. Give them time to fear it, that silence does."))),
    ("power_or_restraint", (
        ("yoda", "Win a fight, strength may. Know which fight to refuse, wisdom must. Different contests, those are."),
        ("chucky", "Which is why 'most powerful' and 'best character' keep turning into two different arguments."))),
    ("station_and_people", (
        ("brucewayne", "The Death Star gives the Empire scale. Vader gives all that machinery a face you can remember."),
        ("lukeskywalker", "And the story still comes back to a small group trusting each other. That contrast is what I like."))),
    ("trusting_han", (
        ("chewbacca", "Rrrroww. Han talks like he has a plan. The interesting part is who sticks beside him when the plan falls apart."),
        ("yoda", "Confidence, easy to announce it is. Trust, through the difficult part it must last."))),
    ("patience_contest", (
        ("chucky", "Yoda wins the patience contest. I'm disqualified before the rules finish."),
        ("yoda", "Finish listening first, you could. A new strategy, that would be."))),
    ("ranking_spreadsheet", (
        ("brucewayne", "There are people who organize their movie rankings in spreadsheets. I respect the preparation."),
        ("lukeskywalker", "That's a very Bruce Wayne way to say you made one."))),
    ("dramatic_whisper", (
        ("chucky", "Chewie keeps winning the loudest entrance category. Do the rest of us get a microphone?"),
        ("chewbacca", "Rrroww. Turn down the dramatic whispers and you might get a word in."))),
    ("hairbrush_transfer", (
        ("yoda", "Chewie, your hairbrush has requested a transfer. Approved, it should be."),
        ("chewbacca", "Rrroww. Big grooming advice from a profile picture with three hairs."))),
]

# Each idea has one shared key, regardless of which character delivers it.
# Questions are occasional; these are not interchangeable engagement banners.
DISCUSSIONS = [
    ("order66_loss", {
        "default": "Yoda sensing the Jedi being killed during Order 66 is such a sad moment. His quiet reaction makes the loss feel enormous.",
        "yoda": "Through the Force, the Jedi's loss Yoda feels. Sad, that quiet moment during Order 66 remains.",
        "lukeskywalker": "Yoda sensing the Jedi fall during Order 66 gets to me. That small reaction carries so much sadness.",
        "chewbacca": "Yoda's reaction to Order 66 is rough. Seeing someone that strong feel so much loss makes the scene sadder.",
        "brucewayne": "Yoda's reaction during Order 66 gives a galaxy-wide loss a personal scale. It is a quietly sad scene.",
        "chucky": "Even I go quiet for Yoda's Order 66 scene. That little pause carries a lot of sadness.",
        "darthvader": "Yoda sensing the loss during Order 66 makes the destruction of the Jedi feel painfully personal.",
    }),
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
# Original fan commentary grounded in the official Star Wars Databank and
# Lucasfilm's Inside Intel article about Vader's suit. These are separate ideas,
# not fresh keys for restatements of the existing redemption/presence prompts.
DISCUSSIONS.extend([
    ("breathing_sound", {
        "default": "Vader's breathing turns an empty corridor into a warning.",
        "yoda": "Before footsteps, the breathing. Near, danger feels.",
        "lukeskywalker": "That breathing makes Vader feel close before he even appears.",
        "chewbacca": "Rrrroww. Vader's breathing is a sound you cannot mistake.",
        "brucewayne": "The breathing builds tension without explaining where Vader is standing.",
        "chucky": "Imagine trying to sneak anywhere with Vader's breathing. Absolutely hopeless.",
        "darthvader": "The breathing announces what the footsteps have yet to confirm.",
    }),
    ("suit_life_support", {
        "default": "Vader's suit is life support. The intimidating machinery also shows vulnerability.",
        "yoda": "Keep him alive, that armor must. Beneath strength, dependence remains.",
        "lukeskywalker": "Knowing Vader needs the suit makes the armor feel much sadder.",
        "chewbacca": "That armor has to keep Vader alive through everything. Heavy burden.",
        "brucewayne": "Vader's life support makes the suit both protection and a constraint.",
        "chucky": "Vader's armor looks terrifying, then you remember it is medical equipment.",
        "darthvader": "The suit sustains life. Its appearance tells only half the story.",
    }),
    ("anakin_hero_past", {
        "default": "Anakin's heroic past makes Vader's fall harder to dismiss.",
        "yoda": "A hero, Anakin once was. Remember the beginning, we must.",
        "lukeskywalker": "The Clone Wars give Anakin's earlier bravery room to matter.",
        "chewbacca": "Anakin's war record makes the turn into Vader hurt more.",
        "brucewayne": "Vader's history includes genuine heroism. That complicates a simple villain label.",
        "chucky": "Starting with heroic Anakin makes the Vader story considerably more painful.",
        "darthvader": "The heroic years belong to Anakin's history as much as the fall.",
    }),
    ("padme_fear", {
        "default": "Anakin's fear of losing Padmé becomes a disastrous guide for his choices.",
        "yoda": "Fear for Padmé, Anakin carried. Dangerous counsel, fear became.",
        "lukeskywalker": "Anakin wants to prevent a loss and starts making terrible choices.",
        "chewbacca": "Being frightened for someone does not make every desperate plan wise.",
        "brucewayne": "Anakin confuses protecting Padmé with controlling what might happen.",
        "chucky": "Anakin's rescue plan for Padmé goes catastrophically off course.",
        "darthvader": "Fear of loss can distort the very choices meant to prevent it.",
    }),
    ("vader_pilot", {
        "default": "Vader personally flying into battle makes him a very immediate threat.",
        "yoda": "From a cockpit, Vader pursues them. Delegate everything, he does not.",
        "lukeskywalker": "Vader in a fighter changes the danger from distant command to pursuit.",
        "chewbacca": "Vader gets into the fighter himself. That changes the escape calculation.",
        "brucewayne": "Vader's piloting puts the main antagonist directly inside the battle.",
        "chucky": "The boss gets his own fighter. Of course this chase gets worse.",
        "darthvader": "At the first Death Star, Vader takes the pursuit into his own hands.",
    }),
    ("tie_silhouette", {
        "default": "Vader's experimental TIE has a shape you can pick out immediately.",
        "yoda": "Different, Vader's fighter appears. Follow its shape through the battle.",
        "lukeskywalker": "That distinctive TIE design makes Vader easy to track during the chase.",
        "chewbacca": "Spot that TIE silhouette and you know which pursuer matters most.",
        "brucewayne": "Vader's fighter has a distinct profile; that helps the action stay readable.",
        "chucky": "Even Vader's TIE gets a recognizable silhouette. Excellent villain branding.",
        "darthvader": "The experimental TIE distinguishes its pilot before the cockpit is shown.",
    }),
    ("luke_farm_beginning", {
        "default": "Luke's farm beginnings give the enormous adventure a very ordinary starting point.",
        "yoda": "From a moisture farm, Luke begins. Grand titles, he has not.",
        "lukeskywalker": "The farmboy beginning matters. Luke starts by wanting a larger life.",
        "chewbacca": "Luke begins with farm chores, then the whole galaxy gets involved.",
        "brucewayne": "Luke's ordinary starting point makes the scale of the journey easier to feel.",
        "chucky": "Farm work to galactic trouble is quite a change of career.",
        "darthvader": "The moisture farm gives Luke's eventual reputation a modest point of origin.",
    }),
    ("dagobah_failures", {
        "default": "Luke fails during training on Dagobah. The learning has actual friction.",
        "yoda": "Fail in training, Luke does. From an attempt, learn something he must.",
        "lukeskywalker": "Dagobah lets Luke be frustrated and wrong before he improves.",
        "chewbacca": "A rough training day on Dagobah still beats pretending you know everything.",
        "brucewayne": "Luke's failed exercises give the training consequences beyond a montage.",
        "chucky": "Dagobah training looks exhausting. Luke does not get an easy tutorial.",
        "darthvader": "Dagobah exposes the distance between Luke's ambition and his preparation.",
    }),
    ("yoda_teaching_centuries", {
        "default": "Yoda trained Jedi for over 800 years. That is an extraordinary teaching career.",
        "yoda": "Over eight centuries of Jedi students. Familiar, impatience becomes.",
        "lukeskywalker": "Eight centuries of teaching gives Yoda a remarkable perspective on beginners.",
        "chewbacca": "Yoda has seen over 800 years of Jedi students. Some patience.",
        "brucewayne": "Yoda's centuries of teaching make his experience very different from rank alone.",
        "chucky": "Over 800 years teaching Jedi. Imagine the accumulated homework complaints.",
        "darthvader": "Yoda's teaching spans centuries; that experience is difficult to replicate.",
    }),
    ("yoda_species_mystery", {
        "default": "Yoda's species is still listed as unknown. I like that remaining mystery.",
        "yoda": "A species name, you seek. An answer, the records do not give.",
        "lukeskywalker": "Leaving Yoda's species unnamed preserves some of the strangeness around him.",
        "chewbacca": "So much history around Yoda, and his species still stays mysterious.",
        "brucewayne": "Yoda does not need a complete biological explanation to work as a character.",
        "chucky": "Galactic history is extensive. Yoda's species field still refuses to cooperate.",
        "darthvader": "The uncertainty around Yoda's species leaves one detail beyond the records.",
    }),
    ("leia_adoption", {
        "default": "Bail Organa raising Leia gives her family story more than one important father.",
        "yoda": "Raised by Bail Organa, Leia was. Blood alone, a family does not make.",
        "lukeskywalker": "Bail's place in Leia's life matters alongside the Skywalker family connection.",
        "chewbacca": "Bail Organa raised Leia. That part of her family deserves its weight.",
        "brucewayne": "Leia's adoption makes the distinction between ancestry and upbringing important.",
        "chucky": "Leia's family tree is complicated; Bail still did the raising.",
        "darthvader": "The Skywalker connection does not erase Bail Organa's place in Leia's life.",
    }),
    ("skywalker_twins", {
        "default": "Luke and Leia being twins ties two separate journeys into one family history.",
        "yoda": "Twins, Luke and Leia are. Different paths, one family carries.",
        "lukeskywalker": "The twin connection makes Luke and Leia's separate beginnings feel more significant.",
        "chewbacca": "Same family, very different starts. Luke and Leia make an interesting pair.",
        "brucewayne": "The twins show how differently the same ancestry can unfold.",
        "chucky": "Luke and Leia's twin reveal makes the family chart considerably busier.",
        "darthvader": "The twins link the Skywalker legacy to two very different lives.",
    }),
    ("han_yavin_return", {
        "default": "Han returning at Yavin is the moment his priorities become unmistakable.",
        "yoda": "Return at Yavin, Han chooses. Greater than payment, something becomes.",
        "lukeskywalker": "Han coming back at Yavin makes the last stretch of the battle work.",
        "chewbacca": "Han and Chewie coming back at Yavin is the choice that counts.",
        "brucewayne": "Han's return at Yavin tells you more than his earlier bargaining.",
        "chucky": "Han makes his exit, then ruins the villains' finish. Lovely timing.",
        "darthvader": "Han's return alters the pursuit at the decisive moment over Yavin.",
    }),
    ("han_hoth_rescue", {
        "default": "Han searching the cold for Luke on Hoth is a strong friendship scene.",
        "yoda": "Into Hoth's cold, Han searches. Practical, his care becomes.",
        "lukeskywalker": "The Hoth rescue shows Han's friendship through a difficult, practical decision.",
        "chewbacca": "Han heads into Hoth's cold for Luke. That is looking after your crew.",
        "brucewayne": "Han's search on Hoth makes friendship an action with a real cost.",
        "chucky": "Hoth is freezing and Han still goes searching. Credit where it is due.",
        "darthvader": "Han's search on Hoth reveals a commitment beyond his usual bravado.",
    }),
    ("falcon_hyperdrive", {
        "default": "The Falcon's unreliable hyperdrive turns a simple escape into a whole problem.",
        "yoda": "An escape they plan. Cooperate, the Falcon's hyperdrive may not.",
        "lukeskywalker": "The Falcon's failing hyperdrive keeps the escape from feeling too convenient.",
        "chewbacca": "Rrrroww. The Falcon's hyperdrive picks dreadful moments to become temperamental.",
        "brucewayne": "An unreliable hyperdrive gives the Falcon a useful limitation in a chase.",
        "chucky": "The Falcon's hyperdrive has a spectacularly poor sense of timing.",
        "darthvader": "The Falcon's speed is impressive; its reliability introduces other possibilities.",
    }),
    ("falcon_modifications", {
        "default": "The Falcon looks battered, but its modifications make appearances a poor guide.",
        "yoda": "Beneath the Falcon's worn hull, many modifications hide.",
        "lukeskywalker": "The Falcon's rough exterior makes the surprises underneath more satisfying.",
        "chewbacca": "The Falcon's hull tells you very little about what the ship can do.",
        "brucewayne": "The Falcon's modifications matter more than the finish on its hull.",
        "chucky": "The Falcon looks overdue for repairs and still embarrasses prettier ships.",
        "darthvader": "The freighter's appearance is an inadequate measure of its capabilities.",
    }),
    ("deathstar_weakness", {
        "default": "The Death Star's scale makes its vulnerable exhaust port an effective contrast.",
        "yoda": "Enormous, the station is. Small, the opening that matters becomes.",
        "lukeskywalker": "An enormous station and a tiny exhaust port make the final approach tense.",
        "chewbacca": "A whole battle station, and the small opening is what matters.",
        "brucewayne": "The exhaust port turns overwhelming size into a problem of precision.",
        "chucky": "The Death Star really needed somebody more suspicious of small design flaws.",
        "darthvader": "The station's size does not eliminate the consequences of a critical weakness.",
    }),
    ("deathstar_secrecy", {
        "default": "The Death Star plans make information as consequential as the weapons themselves.",
        "yoda": "Guarded, the station's plans were. Change the balance, information could.",
        "lukeskywalker": "Getting the plans to the Rebels matters before any fighter launches.",
        "chewbacca": "The plans have to get through. A blaster cannot solve that whole mission.",
        "brucewayne": "The Death Star story makes stolen intelligence a concrete strategic advantage.",
        "chucky": "The Empire builds the giant weapon; somebody else gets the paperwork.",
        "darthvader": "The stolen plans make an information failure into a military danger.",
    }),
    ("r2_bravery", {
        "default": "R2 keeps moving toward danger. That bravery is easy to underestimate.",
        "yoda": "Toward danger, R2 rolls. Small wheels, considerable courage.",
        "lukeskywalker": "R2's bravery gives those small droid moments real stakes.",
        "chewbacca": "R2 sees trouble and keeps rolling. I respect that nerve.",
        "brucewayne": "R2 repeatedly accepts risk rather than waiting for somebody larger.",
        "chucky": "R2 has extraordinary confidence for somebody shaped like a small appliance.",
        "darthvader": "R2's willingness to enter danger should not be confused with insignificance.",
    }),
    ("r2_generations", {
        "default": "R2 serving Padmé, Anakin and Luke gives him an unusual view of the family.",
        "yoda": "Padmé, Anakin, Luke. Across those lives, R2's service continues.",
        "lukeskywalker": "R2's history reaches back through Padmé and Anakin, long before Luke's journey.",
        "chewbacca": "R2 has been alongside more of that family history than most people.",
        "brucewayne": "R2 connects several generations through service rather than a family name.",
        "chucky": "R2's list of former companions makes the little droid a walking archive.",
        "darthvader": "R2's service links lives that the later conflict would divide.",
    }),
    ("threepio_builder", {
        "default": "Young Anakin building C-3PO is a detail I always find bittersweet.",
        "yoda": "Built Threepio, young Anakin did. Helpful, his intention then was.",
        "lukeskywalker": "Anakin building Threepio shows a smaller, kinder ambition early in his life.",
        "chewbacca": "Threepio began as young Anakin's project. Strange how far that story travels.",
        "brucewayne": "C-3PO's origin gives Anakin a constructive talent beyond fighting.",
        "chucky": "Before Vader, Anakin was putting together a very talkative droid.",
        "darthvader": "Threepio began with Anakin's engineering skill and an intention to help.",
    }),
    ("threepio_translation", {
        "default": "Threepio's communication skills matter whenever the adventure needs more than force.",
        "yoda": "Understand another voice, Threepio can. Useful beyond battle, that skill is.",
        "lukeskywalker": "Threepio's language skills remind me that a rescue can depend on understanding.",
        "chewbacca": "Different languages do not make Threepio's work optional. Somebody has to understand.",
        "brucewayne": "Translation turns Threepio's knowledge into access other characters cannot manufacture.",
        "chucky": "Threepio brings the languages and the worrying. A comprehensive service.",
        "darthvader": "The ability to communicate has strategic uses that weapons cannot replace.",
    }),
    ("walker_intimidation", {
        "default": "The AT-AT's height makes the Hoth ground assault feel horribly uneven.",
        "yoda": "Over the ground, the walkers tower. Unequal, the battle appears.",
        "lukeskywalker": "The AT-ATs make the defenders on Hoth look painfully exposed.",
        "chewbacca": "Those walkers make a very big shape on an open battlefield.",
        "brucewayne": "An AT-AT projects intimidation before its weapons become the focus.",
        "chucky": "Hoth gets snow, freezing winds, and giant walking tanks. Tough neighborhood.",
        "darthvader": "The AT-AT's scale is part of its effect on an opponent.",
    }),
    ("walker_transport", {
        "default": "The AT-AT is a transport as well as a combat vehicle. That changes its purpose.",
        "yoda": "Carry troops, a walker can. More than a large weapon, it is.",
        "lukeskywalker": "Thinking of AT-ATs as transports makes the ground assault feel more methodical.",
        "chewbacca": "An AT-AT brings troops with the armor. That is a whole moving problem.",
        "brucewayne": "The walker combines protected movement with firepower instead of serving one role.",
        "chucky": "The AT-AT is an armored troop ride with a deeply unfriendly reception.",
        "darthvader": "Protected transport and combat power are combined within the same advancing platform.",
    }),
])

for _idea, _voices in DISCUSSIONS:
    for _speaker, _catalog in DISCUSSION_VOICES.items():
        if _idea in _catalog:
            _voices[_speaker] = _catalog[_idea][0]

DISCUSSION_REFERENCES = (
    "https://www.starwars.com/news/star-wars-inside-intel-darth-vader-suit",
    "https://www.starwars.com/databank/darth-vader",
    "https://www.starwars.com/databank/darth-vader-s-tie-fighter",
    "https://www.starwars.com/databank/luke-skywalker",
    "https://www.starwars.com/databank/yoda",
    "https://www.starwars.com/databank/leia-organa",
    "https://www.starwars.com/databank/han-solo",
    "https://www.starwars.com/databank/millennium-falcon",
    "https://www.starwars.com/databank/death-star",
    "https://www.starwars.com/databank/r2-d2",
    "https://www.starwars.com/databank/c-3po",
    "https://www.starwars.com/databank/at-at-walker",
)

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


def compact_sources(text, kind, include_link=False):
    """Render chat text without the feed's routine source/date footer.

    Retrieval still checks those dates and links. Keep times that belong to the
    actual story, fixture or price window, and use a rare compact link only.
    """
    if kind not in NEWS_KINDS:
        return text, []
    lines = []
    originals = text.splitlines()
    source_url = None
    date_start = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+"
    for index, line in enumerate(originals):
        if re.fullmatch(r"https://\S+", line.strip()):
            source_url = source_url or line.strip()
            continue
        if index:
            label, separator, metadata = line.partition(" · ")
            if separator and re.match(r"(?:checked\s+)?" + date_start, metadata, re.I):
                continue
            if kind == "fragment" and re.match(date_start, line.strip(), re.I):
                continue
        line = re.sub(r"(?:https?://|www\.)\S+", "", line, flags=re.I).strip()
        if line:
            lines.append(line)
    body = "\n".join(lines)
    if include_link and source_url and body:
        prefix = body + "\n"
        label = "More here"
        return prefix + label, [{"type": "text_link", "offset": len(prefix.encode("utf-16-le")) // 2,
                                "length": len(label), "url": source_url}]
    return body, []
