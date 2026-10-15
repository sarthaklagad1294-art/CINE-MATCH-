"""Generate a compact 240-row CineMatch catalog for offline demos.

The real TMDB 5000 files can replace these CSVs at any time. The bundled catalog
uses varied, coherent story seeds so the NLP pipeline is meaningful on first run.
"""

from __future__ import annotations

import csv
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MOVIES_PATH = ROOT / "movies.csv"
CREDITS_PATH = ROOT / "credits.csv"
POSTERS_DIR = ROOT.parent / "static" / "images" / "posters"

VARIANTS = [
    "The Unseen Chapter",
    "Beyond the Horizon",
    "Legacy of Fire",
    "Final Signal",
]

SEEDS = [
    ("Avatar", "A marine explores a lush alien moon and must choose between a military mission and defending a new family.", ["Action", "Adventure", "Science Fiction"], ["space", "aliens", "forest", "family"], ["Sam Worthington", "Zoe Saldana", "Sigourney Weaver"], "James Cameron", 7.6, 92.0, "2009-12-10"),
    ("The Dark Knight", "A masked vigilante faces a chaotic criminal mastermind while a city struggles to keep its moral center.", ["Drama", "Action", "Crime"], ["hero", "villain", "city", "justice"], ["Christian Bale", "Heath Ledger", "Gary Oldman"], "Christopher Nolan", 8.5, 98.0, "2008-07-16"),
    ("Toy Story", "A group of toys discover friendship, jealousy, and courage when a new space-ranger figure arrives.", ["Animation", "Comedy", "Family"], ["toys", "friendship", "childhood", "adventure"], ["Tom Hanks", "Tim Allen", "Annie Potts"], "John Lasseter", 8.0, 85.0, "1995-10-30"),
    ("Inception", "A skilled dream thief is offered one impossible mission: plant an idea inside a powerful mind.", ["Action", "Science Fiction", "Thriller"], ["dream", "heist", "memory", "reality"], ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"], "Christopher Nolan", 8.4, 94.0, "2010-07-15"),
    ("Interstellar", "Explorers travel through a wormhole to find a future home for humanity while time reshapes their families.", ["Adventure", "Drama", "Science Fiction"], ["space", "wormhole", "time", "family"], ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"], "Christopher Nolan", 8.4, 90.0, "2014-11-05"),
    ("The Matrix", "A programmer learns that reality is a simulation and joins a rebellion against intelligent machines.", ["Action", "Science Fiction"], ["simulation", "machines", "rebellion", "identity"], ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"], "Lana Wachowski", 8.2, 88.0, "1999-03-30"),
    ("The Lord of the Rings", "A quiet guardian carries a dangerous ring across a mythical land with a fellowship of unlikely heroes.", ["Adventure", "Fantasy", "Drama"], ["ring", "quest", "magic", "fellowship"], ["Elijah Wood", "Ian McKellen", "Viggo Mortensen"], "Peter Jackson", 8.8, 95.0, "2001-12-18"),
    ("Jurassic Park", "Scientists open a dinosaur theme park, then fight to survive when the ancient creatures break free.", ["Adventure", "Science Fiction", "Thriller"], ["dinosaurs", "island", "science", "survival"], ["Sam Neill", "Laura Dern", "Jeff Goldblum"], "Steven Spielberg", 8.1, 89.0, "1993-06-11"),
    ("The Shawshank Redemption", "A patient banker builds an unlikely friendship and a quiet plan for freedom inside a harsh prison.", ["Drama", "Crime"], ["prison", "hope", "friendship", "freedom"], ["Tim Robbins", "Morgan Freeman", "Bob Gunton"], "Frank Darabont", 8.7, 84.0, "1994-09-23"),
    ("The Godfather", "A reluctant son is drawn into his family's crime empire and must balance loyalty, power, and love.", ["Drama", "Crime"], ["family", "mafia", "power", "loyalty"], ["Marlon Brando", "Al Pacino", "James Caan"], "Francis Ford Coppola", 8.7, 82.0, "1972-03-14"),
    ("Mad Max Fury Road", "A rebellious driver and a determined survivor race across a desert wasteland toward a safer future.", ["Action", "Adventure", "Science Fiction"], ["desert", "chase", "rebellion", "survival"], ["Tom Hardy", "Charlize Theron", "Nicholas Hoult"], "George Miller", 8.1, 87.0, "2015-05-07"),
    ("The Martian", "An astronaut stranded on Mars uses science, humor, and stubborn optimism to stay alive until rescue.", ["Drama", "Adventure", "Science Fiction"], ["mars", "astronaut", "science", "survival"], ["Matt Damon", "Jessica Chastain", "Chiwetel Ejiofor"], "Ridley Scott", 7.7, 80.0, "2015-10-02"),
    ("Guardians of the Galaxy", "A group of outlaws become an unlikely team when a cosmic artifact puts a galaxy in danger.", ["Action", "Adventure", "Comedy"], ["space", "team", "music", "aliens"], ["Chris Pratt", "Zoe Saldana", "Dave Bautista"], "James Gunn", 7.9, 91.0, "2014-07-30"),
    ("Spider-Man Into the Spider-Verse", "A teenager discovers that courage can connect heroes from different dimensions.", ["Animation", "Action", "Adventure"], ["spider", "hero", "multiverse", "teenager"], ["Shameik Moore", "Jake Johnson", "Hailee Steinfeld"], "Bob Persichetti", 8.4, 86.0, "2018-12-06"),
    ("Black Panther", "A new king protects a hidden nation while an old rival challenges his vision of the future.", ["Action", "Adventure", "Science Fiction"], ["king", "africa", "technology", "identity"], ["Chadwick Boseman", "Michael B. Jordan", "Lupita Nyong'o"], "Ryan Coogler", 7.3, 93.0, "2018-02-13"),
    ("Wonder Woman", "An Amazon warrior leaves her island to confront a war and discover the limits of her own power.", ["Action", "Adventure", "Fantasy"], ["war", "hero", "amazon", "myth"], ["Gal Gadot", "Chris Pine", "Robin Wright"], "Patty Jenkins", 7.4, 83.0, "2017-05-30"),
    ("The Grand Budapest Hotel", "A legendary concierge and his lobby boy become entangled in a stolen painting and a family fortune.", ["Comedy", "Drama", "Adventure"], ["hotel", "friendship", "art", "eccentric"], ["Ralph Fiennes", "Tony Revolori", "Saoirse Ronan"], "Wes Anderson", 8.0, 78.0, "2014-02-26"),
    ("La La Land", "Two artists in Los Angeles fall in love while pursuing ambitious dreams and learning what success costs.", ["Comedy", "Drama", "Romance"], ["music", "dance", "dreams", "los angeles"], ["Ryan Gosling", "Emma Stone", "John Legend"], "Damien Chazelle", 7.9, 88.0, "2016-11-29"),
    ("Whiplash", "A young drummer enters a brutal mentorship that tests the line between excellence and obsession.", ["Drama", "Music"], ["drummer", "mentor", "ambition", "jazz"], ["Miles Teller", "J.K. Simmons", "Melissa Benoist"], "Damien Chazelle", 8.3, 81.0, "2014-10-10"),
    ("The Silence of the Lambs", "A trainee investigator seeks help from a brilliant imprisoned killer to catch another dangerous criminal.", ["Crime", "Drama", "Thriller"], ["investigator", "serial killer", "psychology", "crime"], ["Jodie Foster", "Anthony Hopkins", "Scott Glenn"], "Jonathan Demme", 8.6, 79.0, "1991-02-13"),
    ("Gone Girl", "A writer becomes the focus of a media storm when his wife disappears and every secret surfaces.", ["Mystery", "Thriller", "Drama"], ["marriage", "mystery", "media", "secrets"], ["Ben Affleck", "Rosamund Pike", "Neil Patrick Harris"], "David Fincher", 7.9, 76.0, "2014-10-01"),
    ("Arrival", "A linguist works with an international team to understand visitors whose language changes how humans see time.", ["Drama", "Science Fiction", "Mystery"], ["aliens", "language", "time", "communication"], ["Amy Adams", "Jeremy Renner", "Forest Whitaker"], "Denis Villeneuve", 7.9, 84.0, "2016-11-10"),
    ("Blade Runner 2049", "A future detective uncovers a secret that leads him to a vanished former officer and a buried truth.", ["Science Fiction", "Drama", "Mystery"], ["future", "android", "identity", "detective"], ["Ryan Gosling", "Harrison Ford", "Ana de Armas"], "Denis Villeneuve", 8.0, 82.0, "2017-10-04"),
    ("Her", "A lonely writer begins an intimate relationship with an operating system that seems to understand him.", ["Drama", "Romance", "Science Fiction"], ["artificial intelligence", "love", "loneliness", "technology"], ["Joaquin Phoenix", "Scarlett Johansson", "Amy Adams"], "Spike Jonze", 7.9, 70.0, "2013-12-18"),
    ("Eternal Sunshine of the Spotless Mind", "A couple erases their memories of one another and discovers love can survive the procedure.", ["Science Fiction", "Drama", "Romance"], ["memory", "love", "breakup", "surreal"], ["Jim Carrey", "Kate Winslet", "Tom Wilkinson"], "Michel Gondry", 8.1, 73.0, "2004-03-19"),
    ("The Social Network", "A brilliant student builds a world-changing social network while friendships become legal battles.", ["Drama", "History"], ["technology", "friendship", "ambition", "college"], ["Jesse Eisenberg", "Andrew Garfield", "Justin Timberlake"], "David Fincher", 7.7, 75.0, "2010-10-01"),
    ("Moneyball", "A baseball manager and an analyst challenge tradition by using data to build a competitive team.", ["Drama", "Sport"], ["baseball", "data", "strategy", "underdog"], ["Brad Pitt", "Jonah Hill", "Philip Seymour Hoffman"], "Bennett Miller", 7.6, 68.0, "2011-09-09"),
    ("Rocky", "A small-time boxer gets one chance at a title fight and trains to prove he belongs in the ring.", ["Drama", "Sport"], ["boxing", "training", "underdog", "dream"], ["Sylvester Stallone", "Talia Shire", "Burt Young"], "John G. Avildsen", 7.8, 72.0, "1976-11-21"),
    ("The Incredibles", "A family of retired superheroes returns to action when a new villain targets the world.", ["Animation", "Action", "Family"], ["superhero", "family", "secret identity", "adventure"], ["Craig T. Nelson", "Holly Hunter", "Samuel L. Jackson"], "Brad Bird", 8.0, 89.0, "2004-10-27"),
    ("Finding Nemo", "A cautious father crosses the ocean to rescue his adventurous son and discovers unexpected friends.", ["Animation", "Family", "Adventure"], ["ocean", "fish", "family", "friendship"], ["Albert Brooks", "Ellen DeGeneres", "Alexander Gould"], "Andrew Stanton", 8.2, 90.0, "2003-05-30"),
    ("Spirited Away", "A young girl enters a mysterious spirit world and must find courage to save her transformed parents.", ["Animation", "Fantasy", "Adventure"], ["spirits", "magic", "girl", "family"], ["Rumi Hiiragi", "Miyu Irino", "Mari Natsuki"], "Hayao Miyazaki", 8.6, 77.0, "2001-07-20"),
    ("The Princess Bride", "A farmhand turned hero crosses a fairy-tale kingdom to rescue his true love from a forced marriage.", ["Adventure", "Comedy", "Romance"], ["fairy tale", "sword", "love", "adventure"], ["Cary Elwes", "Robin Wright", "Mandy Patinkin"], "Rob Reiner", 8.0, 74.0, "1987-09-25"),
    ("Back to the Future", "A teenager travels through time and must repair his parents' meeting before he erases his own future.", ["Adventure", "Comedy", "Science Fiction"], ["time travel", "teenager", "family", "invention"], ["Michael J. Fox", "Christopher Lloyd", "Lea Thompson"], "Robert Zemeckis", 8.3, 86.0, "1985-07-03"),
    ("The Truman Show", "A gentle man slowly realizes his entire life is a television production watched by the world.", ["Comedy", "Drama"], ["reality", "television", "identity", "freedom"], ["Jim Carrey", "Ed Harris", "Laura Linney"], "Peter Weir", 8.1, 79.0, "1998-06-04"),
    ("The Prestige", "Two rival magicians sacrifice everything to outdo one another with increasingly dangerous illusions.", ["Drama", "Mystery", "Thriller"], ["magic", "rivalry", "obsession", "illusion"], ["Hugh Jackman", "Christian Bale", "Michael Caine"], "Christopher Nolan", 8.5, 80.0, "2006-10-19"),
    ("Dune", "A young nobleman travels to a desert planet and becomes part of a prophecy that could change an empire.", ["Science Fiction", "Adventure", "Drama"], ["desert", "prophecy", "empire", "politics"], ["Timothee Chalamet", "Rebecca Ferguson", "Oscar Isaac"], "Denis Villeneuve", 8.0, 96.0, "2021-09-03"),
    ("The Hunger Games", "A teenager volunteers for a televised survival contest and becomes the symbol of a rebellion.", ["Science Fiction", "Adventure", "Action"], ["survival", "rebellion", "competition", "future"], ["Jennifer Lawrence", "Josh Hutcherson", "Liam Hemsworth"], "Gary Ross", 7.2, 92.0, "2012-03-12"),
    ("The Last Samurai", "A disillusioned soldier finds purpose and respect while living among warriors defending an old way of life.", ["Action", "Drama", "History"], ["samurai", "warrior", "honor", "culture"], ["Tom Cruise", "Ken Watanabe", "Hiroyuki Sanada"], "Edward Zwick", 7.7, 69.0, "2003-12-05"),
    ("The Green Mile", "A prison guard witnesses an extraordinary gift in a gentle inmate and questions the meaning of justice.", ["Fantasy", "Drama", "Crime"], ["prison", "miracle", "justice", "compassion"], ["Tom Hanks", "Michael Clarke Duncan", "David Morse"], "Frank Darabont", 8.6, 83.0, "1999-12-10"),
    ("A Beautiful Mind", "A gifted mathematician battles illness and learns to trust the people who stand beside him.", ["Drama", "Romance"], ["mathematics", "genius", "illness", "love"], ["Russell Crowe", "Jennifer Connelly", "Ed Harris"], "Ron Howard", 7.7, 74.0, "2001-12-11"),
    ("The Revenant", "A frontiersman survives a brutal journey through frozen wilderness after betrayal leaves him for dead.", ["Adventure", "Drama", "Western"], ["wilderness", "survival", "revenge", "frontier"], ["Leonardo DiCaprio", "Tom Hardy", "Domhnall Gleeson"], "Alejandro G. Inarritu", 7.5, 85.0, "2015-12-25"),
    ("The Wolf of Wall Street", "A charismatic stockbroker builds a lavish empire and loses himself in greed, excess, and fraud.", ["Comedy", "Crime", "Drama"], ["finance", "greed", "ambition", "fraud"], ["Leonardo DiCaprio", "Jonah Hill", "Margot Robbie"], "Martin Scorsese", 8.0, 88.0, "2013-12-25"),
    ("The Big Lebowski", "A laid-back bowler is pulled into a kidnapping mystery after being mistaken for a wealthy man.", ["Comedy", "Crime"], ["bowling", "mistaken identity", "friendship", "mystery"], ["Jeff Bridges", "John Goodman", "Julianne Moore"], "Joel Coen", 7.9, 71.0, "1998-03-06"),
    ("The Sound of Music", "A warm governess brings music and courage to a family while political danger closes in around them.", ["Drama", "Family", "Music"], ["music", "family", "love", "war"], ["Julie Andrews", "Christopher Plummer", "Eleanor Parker"], "Robert Wise", 8.0, 67.0, "1965-03-02"),
    ("The Terminator", "A soldier travels back in time to protect a future leader from an unstoppable machine assassin.", ["Action", "Science Fiction", "Thriller"], ["robots", "time travel", "future", "survival"], ["Arnold Schwarzenegger", "Linda Hamilton", "Michael Biehn"], "James Cameron", 8.1, 78.0, "1984-10-26"),
    ("The Fifth Element", "A cab driver becomes the unlikely guardian of a mysterious woman who may save the planet.", ["Action", "Adventure", "Science Fiction"], ["future", "space", "taxi", "aliens"], ["Bruce Willis", "Milla Jovovich", "Gary Oldman"], "Luc Besson", 7.6, 73.0, "1997-05-07"),
    ("The Lion King", "A young lion prince grows into his responsibility after tragedy separates him from his family.", ["Animation", "Family", "Drama"], ["lion", "king", "family", "courage"], ["Matthew Broderick", "Jeremy Irons", "James Earl Jones"], "Roger Allers", 8.5, 91.0, "1994-06-23"),
    ("How to Train Your Dragon", "A clever teenager befriends a dragon and changes the way his village sees the creatures it fears.", ["Animation", "Fantasy", "Adventure"], ["dragons", "friendship", "village", "courage"], ["Jay Baruchel", "Gerard Butler", "America Ferrera"], "Chris Sanders", 8.1, 87.0, "2010-03-18"),
    ("The Secret Life of Walter Mitty", "A quiet photo editor leaves routine behind and goes on a global adventure to find a missing image.", ["Adventure", "Comedy", "Drama"], ["travel", "dreams", "photography", "courage"], ["Ben Stiller", "Kristen Wiig", "Sean Penn"], "Ben Stiller", 7.3, 66.0, "2013-12-18"),
]

SEEDS.extend([
    ("The Conjuring", "Paranormal investigators help a family survive a haunted farmhouse where a violent presence is growing stronger.", ["Horror", "Thriller", "Mystery"], ["haunted house", "demon", "paranormal", "family", "exorcism"], ["Vera Farmiga", "Patrick Wilson", "Lili Taylor"], "James Wan", 7.5, 88.0, "2013-07-19"),
    ("A Quiet Place", "A family hides from blind creatures that hunt by sound while trying to protect their children and stay silent.", ["Horror", "Thriller", "Science Fiction"], ["silence", "creatures", "family", "survival", "invasion"], ["Emily Blunt", "John Krasinski", "Millicent Simmonds"], "John Krasinski", 7.5, 91.0, "2018-04-03"),
    ("Get Out", "A young photographer visits his girlfriend's family and uncovers a disturbing conspiracy hiding behind polite smiles.", ["Horror", "Mystery", "Thriller"], ["conspiracy", "hypnosis", "family", "escape", "suspense"], ["Daniel Kaluuya", "Allison Williams", "Bradley Whitford"], "Jordan Peele", 7.6, 87.0, "2017-02-24"),
    ("It", "A group of children face a shape-shifting predator that returns to their town whenever fear takes hold.", ["Horror", "Drama"], ["clown", "children", "fear", "friendship", "small town"], ["Jaeden Martell", "Bill Skarsgard", "Sophia Lillis"], "Andy Muschietti", 7.3, 84.0, "2017-09-05"),
    ("Alien", "A crew aboard a commercial spaceship is hunted by a perfect extraterrestrial predator after answering a mysterious signal.", ["Horror", "Science Fiction", "Thriller"], ["space", "creature", "spaceship", "survival", "isolation"], ["Sigourney Weaver", "Tom Skerritt", "John Hurt"], "Ridley Scott", 8.1, 86.0, "1979-05-25"),
    ("Scream", "A masked killer turns a quiet town into a deadly puzzle while a group of teenagers try to survive the night.", ["Horror", "Mystery", "Thriller"], ["masked killer", "teenagers", "slasher", "murder", "suspense"], ["Neve Campbell", "Courteney Cox", "David Arquette"], "Wes Craven", 7.4, 79.0, "1996-12-20"),
    ("Halloween", "A determined survivor is stalked by a silent masked killer who returns to the neighborhood on one terrifying night.", ["Horror", "Thriller"], ["masked killer", "babysitter", "stalker", "night", "survival"], ["Jamie Lee Curtis", "Donald Pleasence", "P.J. Soles"], "John Carpenter", 7.7, 76.0, "1978-10-25"),
    ("The Exorcist", "A mother seeks help when her young daughter becomes the center of a terrifying demonic possession.", ["Horror", "Drama"], ["possession", "demon", "priest", "faith", "exorcism"], ["Ellen Burstyn", "Max von Sydow", "Linda Blair"], "William Friedkin", 8.1, 71.0, "1973-12-26"),
    ("The Shining", "A writer takes a winter caretaker job at an isolated hotel where the building's secrets push him toward madness.", ["Horror", "Drama", "Mystery"], ["hotel", "isolation", "madness", "winter", "haunting"], ["Jack Nicholson", "Shelley Duvall", "Danny Lloyd"], "Stanley Kubrick", 8.4, 83.0, "1980-05-23"),
    ("Psycho", "A secretary's desperate escape leads to a remote motel and a mystery guarded by a troubled young owner.", ["Horror", "Mystery", "Thriller"], ["motel", "murder", "identity", "shower", "crime"], ["Anthony Perkins", "Janet Leigh", "Vera Miles"], "Alfred Hitchcock", 8.5, 75.0, "1960-06-16"),
    ("Hereditary", "After a grandmother dies, a family uncovers a chilling legacy of grief, secrets, and occult forces.", ["Horror", "Mystery", "Drama"], ["family", "grief", "occult", "inheritance", "ritual"], ["Toni Collette", "Alex Wolff", "Milly Shapiro"], "Ari Aster", 7.3, 78.0, "2018-06-04"),
    ("Us", "A family on vacation is confronted by terrifying doubles who force them to face a buried national secret.", ["Horror", "Thriller", "Mystery"], ["doubles", "family", "invasion", "identity", "survival"], ["Lupita Nyong'o", "Winston Duke", "Elisabeth Moss"], "Jordan Peele", 6.8, 81.0, "2019-03-22"),
    ("Train to Busan", "Passengers trapped on a moving train fight through a sudden zombie outbreak to reach a safe city.", ["Horror", "Action", "Thriller"], ["zombies", "train", "outbreak", "survival", "father"], ["Gong Yoo", "Jung Yu-mi", "Ma Dong-seok"], "Yeon Sang-ho", 7.6, 80.0, "2016-07-20"),
    ("World War Z", "A former investigator races across a collapsing world to find the source of a fast-moving zombie pandemic.", ["Action", "Horror", "Thriller"], ["zombies", "outbreak", "pandemic", "survival", "global"], ["Brad Pitt", "Mireille Enos", "Daniella Kertesz"], "Marc Forster", 7.0, 86.0, "2013-06-19"),
    ("John Wick", "A retired assassin returns to the underworld after a personal loss and faces a relentless chain of enemies.", ["Action", "Thriller", "Crime"], ["assassin", "revenge", "underworld", "gun", "fight"], ["Keanu Reeves", "Michael Nyqvist", "Alfie Allen"], "Chad Stahelski", 7.4, 90.0, "2014-10-22"),
    ("Die Hard", "A police officer trapped in a skyscraper uses wit and courage to stop an armed hostage takeover.", ["Action", "Thriller"], ["hostage", "skyscraper", "police", "terrorist", "survival"], ["Bruce Willis", "Alan Rickman", "Bonnie Bedelia"], "John McTiernan", 8.2, 85.0, "1988-07-15"),
    ("Gladiator", "A betrayed Roman general becomes a gladiator and fights for justice, memory, and the freedom of his people.", ["Action", "Drama", "History"], ["rome", "gladiator", "revenge", "empire", "warrior"], ["Russell Crowe", "Joaquin Phoenix", "Connie Nielsen"], "Ridley Scott", 8.5, 89.0, "2000-05-01"),
    ("Edge of Tomorrow", "A soldier caught in a time loop relives an alien battle and learns how to change humanity's last stand.", ["Action", "Science Fiction", "Thriller"], ["time loop", "aliens", "battle", "soldier", "future"], ["Tom Cruise", "Emily Blunt", "Bill Paxton"], "Doug Liman", 7.9, 83.0, "2014-05-27"),
    ("Se7en", "Two detectives hunt a calculating killer whose murders are staged around a terrifying moral puzzle.", ["Thriller", "Crime", "Mystery"], ["serial killer", "detective", "investigation", "crime", "suspense"], ["Brad Pitt", "Morgan Freeman", "Kevin Spacey"], "David Fincher", 8.6, 87.0, "1995-09-22"),
    ("Zodiac", "A journalist and detectives become obsessed with decoding letters from an elusive killer haunting San Francisco.", ["Thriller", "Crime", "Mystery"], ["serial killer", "investigation", "journalist", "clues", "obsession"], ["Jake Gyllenhaal", "Mark Ruffalo", "Robert Downey Jr."], "David Fincher", 7.7, 78.0, "2007-03-02"),
    ("Prisoners", "A desperate father takes matters into his own hands when two children disappear and the investigation stalls.", ["Thriller", "Crime", "Drama"], ["kidnapping", "detective", "missing child", "revenge", "mystery"], ["Hugh Jackman", "Jake Gyllenhaal", "Viola Davis"], "Denis Villeneuve", 8.1, 84.0, "2013-08-30"),
    ("Nightcrawler", "An ambitious outsider discovers the violent world of late-night crime journalism and crosses every ethical line.", ["Thriller", "Crime", "Drama"], ["journalism", "crime", "night", "ambition", "camera"], ["Jake Gyllenhaal", "Rene Russo", "Riz Ahmed"], "Dan Gilroy", 7.8, 82.0, "2014-10-31"),
    ("The Bourne Identity", "An amnesiac man with extraordinary skills races across Europe to uncover who trained him and why he is hunted.", ["Thriller", "Action", "Mystery"], ["amnesia", "spy", "conspiracy", "assassin", "escape"], ["Matt Damon", "Franka Potente", "Chris Cooper"], "Doug Liman", 7.9, 86.0, "2002-06-14"),
    ("Memento", "A man with short-term memory loss pieces together clues and tattoos to find the person who changed his life.", ["Thriller", "Mystery", "Drama"], ["memory", "revenge", "clues", "identity", "investigation"], ["Guy Pearce", "Carrie-Anne Moss", "Joe Pantoliano"], "Christopher Nolan", 8.4, 79.0, "2000-10-11"),
    ("The Fugitive", "A wrongly accused doctor escapes custody and follows a trail of evidence while a relentless marshal pursues him.", ["Thriller", "Action", "Crime"], ["fugitive", "investigation", "wrongly accused", "police", "escape"], ["Harrison Ford", "Tommy Lee Jones", "Sela Ward"], "Andrew Davis", 7.8, 74.0, "1993-08-06"),
    ("The Girl with the Dragon Tattoo", "A journalist and hacker investigate a decades-old disappearance buried inside a powerful family.", ["Thriller", "Crime", "Mystery"], ["hacker", "investigation", "missing person", "family secret", "revenge"], ["Rooney Mara", "Daniel Craig", "Christopher Plummer"], "David Fincher", 7.8, 76.0, "2011-12-20"),
])


def _poster_palette(genres: list[str], index: int) -> tuple[str, str, str]:
    """Choose a genre-led palette for deterministic offline cover artwork."""
    palettes = {
        "Science Fiction": ("#111b3b", "#5e4bb6", "#72d7d4"),
        "Fantasy": ("#231536", "#a24f98", "#f5b84b"),
        "Animation": ("#142d35", "#2a8890", "#f5b84b"),
        "Crime": ("#261922", "#9b4c55", "#f5b84b"),
        "Drama": ("#191b30", "#4e588f", "#d9b6ff"),
        "Comedy": ("#332018", "#b96f3c", "#ffe28a"),
        "Action": ("#25161e", "#9d3946", "#f5b84b"),
        "Horror": ("#180f18", "#8e2948", "#ff6f61"),
        "Thriller": ("#141722", "#384a7d", "#e5b85c"),
        "Romance": ("#2c1727", "#a94d7e", "#ffc4a3"),
    }
    return palettes.get(genres[0], ("#15172a", "#4c4b87", "#f5b84b")) if genres else ("#15172a", "#4c4b87", "#f5b84b")


def _poster_title_lines(title: str) -> list[str]:
    """Wrap a movie title into three readable SVG cover lines."""
    words = re.sub(r"[:—]", "", title).split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= 15 or not current:
            current = f"{current} {word}".strip()
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:3] or ["CINEMATCH"]


def _write_poster(movie_id: int, title: str, genres: list[str], year: str, index: int) -> None:
    """Write a lightweight, unique, source-controlled poster cover."""
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    background, accent, highlight = _poster_palette(genres, index)
    safe_title = html.escape(title)
    lines = _poster_title_lines(title)
    title_svg = "".join(
        f'<text x="44" y="{525 + (line_index * 38)}" fill="#F4F1EA" font-family="Arial, sans-serif" font-size="30" font-weight="700">{html.escape(line)}</text>'
        for line_index, line in enumerate(lines)
    )
    rotation = -8 + (index % 17)
    svg = f'''<svg width="500" height="750" viewBox="0 0 500 750" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="500" y2="750" gradientUnits="userSpaceOnUse"><stop stop-color="{background}"/><stop offset="1" stop-color="#0C0D16"/></linearGradient>
    <radialGradient id="glow" cx="0" cy="0" r="1" gradientTransform="translate({130 + (index % 5) * 55} {175 + (index % 4) * 28}) rotate(42) scale(280)"><stop stop-color="{highlight}" stop-opacity=".78"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="500" height="750" rx="28" fill="url(#bg)"/>
  <rect width="500" height="750" rx="28" fill="url(#glow)"/>
  <path d="M-40 404C90 280 210 420 560 210" stroke="{highlight}" stroke-opacity=".28" stroke-width="2"/>
  <path d="M-60 452C100 335 250 486 560 286" stroke="{accent}" stroke-opacity=".42" stroke-width="8"/>
  <g transform="rotate({rotation} 250 280)"><circle cx="250" cy="280" r="116" stroke="{highlight}" stroke-opacity=".55" stroke-width="2"/><circle cx="250" cy="280" r="74" stroke="{accent}" stroke-opacity=".8" stroke-width="7"/><path d="M215 280h70M250 245v70" stroke="{highlight}" stroke-width="5" stroke-linecap="round"/></g>
  <rect x="28" y="28" width="444" height="694" rx="20" stroke="{highlight}" stroke-opacity=".28" stroke-width="2"/>
  <text x="44" y="58" fill="{highlight}" font-family="Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="3">CINEMATCH / {year}</text>
  <text x="44" y="484" fill="#A7A7BE" font-family="Arial, sans-serif" font-size="10" letter-spacing="2">{html.escape(' · '.join(genres[:2]).upper())}</text>
  {title_svg}
  <text x="44" y="680" fill="#A7A7BE" font-family="Arial, sans-serif" font-size="10" letter-spacing="2">CONTENT SIGNAL // {movie_id}</text>
  <text x="456" y="680" fill="{highlight}" font-family="Arial, sans-serif" font-size="10" text-anchor="end" letter-spacing="2">CM</text>
</svg>'''
    (POSTERS_DIR / f"{movie_id}.svg").write_text(svg, encoding="utf-8")


def make_records() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    movies: list[dict[str, object]] = []
    credits: list[dict[str, object]] = []
    movie_id = 1001
    for seed_index, seed in enumerate(SEEDS):
        title, overview, genres, keywords, cast, director, rating, popularity, date = seed
        variants = [None, *VARIANTS]
        for variant_index, variant in enumerate(variants):
            current_title = title if variant is None else f"{title}: {variant}"
            current_overview = overview
            if variant:
                current_overview = f"{overview} The journey continues in a new chapter shaped by {variant.lower()} and difficult choices."
            current_rating = max(5.8, min(9.1, rating - (variant_index * 0.18) + ((seed_index % 3) * 0.03)))
            current_popularity = max(24.0, popularity - variant_index * 4.5 + (seed_index % 7))
            movies.append(
                {
                    "id": movie_id,
                    "title": current_title,
                    "overview": current_overview,
                    "genres": str([{"id": 10 + i, "name": genre} for i, genre in enumerate(genres)]),
                    "keywords": str([{"id": 100 + i, "name": keyword} for i, keyword in enumerate(keywords)]),
                    "popularity": round(current_popularity, 1),
                    "vote_average": round(current_rating, 1),
                    "release_date": date,
                    "runtime": 100 + ((seed_index * 7) % 50),
                    "poster_path": f"local:/static/images/posters/{movie_id}.svg",
                    "collection_key": f"seed-{seed_index}",
                }
            )
            _write_poster(movie_id, current_title, genres, date[:4], movie_id)
            credits.append(
                {
                    "movie_id": movie_id,
                    "title": current_title,
                    "cast": str([{"cast_id": i, "name": person} for i, person in enumerate(cast)]),
                    "crew": str([{"job": "Director", "name": director}]),
                }
            )
            movie_id += 1
    return movies, credits


def main() -> None:
    movies, credits = make_records()
    with MOVIES_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(movies[0]))
        writer.writeheader()
        writer.writerows(movies)
    with CREDITS_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(credits[0]))
        writer.writeheader()
        writer.writerows(credits)
    print(f"Generated {len(movies)} sample movies and {len(credits)} credit rows.")


if __name__ == "__main__":
    main()
