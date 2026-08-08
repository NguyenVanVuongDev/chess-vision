"""A small curated set of well-known opening main lines used by the
opening trainer. Each entry is a short SAN sequence (not a full theory
tree) that the trainer follows move-by-move against the player.
"""

OPENINGS = [
    {"name": "Ruy Lopez", "eco": "C60", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5"]},
    {"name": "Italian Game", "eco": "C50", "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4"]},
    {"name": "Scotch Game", "eco": "C44", "moves": ["e4", "e5", "Nf3", "Nc6", "d4"]},
    {"name": "Petrov's Defense", "eco": "C42", "moves": ["e4", "e5", "Nf3", "Nf6"]},
    {
        "name": "Sicilian Defense: Najdorf",
        "eco": "B90",
        "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
    },
    {
        "name": "Sicilian Defense: Dragon",
        "eco": "B70",
        "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "g6"],
    },
    {"name": "French Defense", "eco": "C00", "moves": ["e4", "e6", "d4", "d5"]},
    {"name": "Caro-Kann Defense", "eco": "B10", "moves": ["e4", "c6", "d4", "d5"]},
    {"name": "Pirc Defense", "eco": "B07", "moves": ["e4", "d6", "d4", "Nf6", "Nc3", "g6"]},
    {"name": "Scandinavian Defense", "eco": "B01", "moves": ["e4", "d5", "exd5", "Qxd5"]},
    {"name": "Alekhine Defense", "eco": "B02", "moves": ["e4", "Nf6", "e5", "Nd5", "d4", "d6"]},
    {"name": "Modern Defense", "eco": "B06", "moves": ["e4", "g6", "d4", "Bg7"]},
    {"name": "Queen's Gambit Declined", "eco": "D30", "moves": ["d4", "d5", "c4", "e6"]},
    {"name": "Queen's Gambit Accepted", "eco": "D20", "moves": ["d4", "d5", "c4", "dxc4"]},
    {"name": "Slav Defense", "eco": "D10", "moves": ["d4", "d5", "c4", "c6"]},
    {"name": "King's Indian Defense", "eco": "E60", "moves": ["d4", "Nf6", "c4", "g6"]},
    {"name": "Nimzo-Indian Defense", "eco": "E20", "moves": ["d4", "Nf6", "c4", "e6", "Nc3", "Bb4"]},
    {"name": "Grünfeld Defense", "eco": "D80", "moves": ["d4", "Nf6", "c4", "g6", "Nc3", "d5"]},
    {"name": "Catalan Opening", "eco": "E00", "moves": ["d4", "Nf6", "c4", "e6", "g3", "d5", "Bg2"]},
    {"name": "London System", "eco": "D02", "moves": ["d4", "d5", "Nf3", "Nf6", "Bf4"]},
    {"name": "English Opening", "eco": "A10", "moves": ["c4", "e5", "Nc3", "Nf6", "Nf3", "Nc6"]},
    {"name": "Reti Opening", "eco": "A04", "moves": ["Nf3", "d5", "c4", "c6"]},
    {"name": "Vienna Game", "eco": "C25", "moves": ["e4", "e5", "Nc3", "Nf6", "f4"]},
    {"name": "King's Gambit", "eco": "C30", "moves": ["e4", "e5", "f4", "exf4"]},
]
