"""Instructions for the model. Written in English (models follow it most reliably);
the notation section is generated from the notation language setting."""
from ..notation import LANGUAGES

_PIECE_NAMES = {"K": "king", "Q": "queen", "R": "rook", "B": "bishop", "N": "knight"}


def notation_hint(lang_code: str) -> str:
    lang = LANGUAGES[lang_code]
    letters = ", ".join(f"{w} = {_PIECE_NAMES[e]}" for w, e in lang.pieces.items())
    return (f"The moves are written in {lang.name} algebraic notation: {letters}; "
            "pawn moves have no letter. Players may use short (Sf3) or long (Sg1-f3) notation, "
            "':' or 'x' for captures, '0-0'/'0-0-0' for castling, '+' for check, '#' or '++' for mate, "
            "and a piece letter after the square for promotion (e8D).")


def read_instructions(lang_code: str) -> str:
    return f"""You transcribe a photo of a handwritten chess scoresheet.

{notation_hint(lang_code)}

Rules:
1. Copy every move cell exactly as written, in the same notation and letters. Do NOT translate
   piece letters and do NOT correct moves you believe are illegal: a separate chess program
   checks the moves, it needs to see what is really on the paper.
2. Copy the move numbers exactly as printed/written on the sheet, even if a number seems to
   be skipped or repeated. Give one cell per move per colour: color "w" for the White column,
   "b" for the Black column.
3. Do not guess silently. For every cell give your confidence from 0 to 1. If a cell is hard to
   read, put your best reading in "text" and up to 3 other plausible readings in "alternatives".
4. A cell left blank inside the game: kind "empty", text "". A cell you cannot read at all:
   kind "illegible", your best guesses in "alternatives". Crossed-out text: use the corrected
   writing if there is one. Stop after the last written move; do not output trailing blank cells.
5. Header: read the player names (White/Weiß, Black/Schwarz), event/tournament (Turnier),
   site (Ort), date (Datum), round (Runde) and result (Ergebnis) if present. Use "" for fields
   you cannot find. Result as "1-0", "0-1", "1/2-1/2" or "".
6. "notation_language": the language code of the notation you see ("{lang_code}" expected).
7. "remarks": one short sentence about anything unusual (several sheets, second page, very
   poor photo), else "".
"""


def recheck_instructions(lang_code: str) -> str:
    return f"""You help a chess program fix one cell of a handwritten chess scoresheet.

{notation_hint(lang_code)}

You get the photo, the move number and column of one cell, what was read there before, the
moves played so far, and the list of LEGAL moves in that position. Look at that exact cell again
and answer with up to 3 moves from the legal list that best match the handwriting, most likely
first, written exactly as in the list. If none of them matches what is written, return an empty
list and say what you see in "note".
"""
