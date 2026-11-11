"""Chess Reader core: turns recognised scoresheet text into a legal game and PGN.

Modules:
    notation   - notation languages (German first) and parsing of written moves
    similarity - "how similar are two handwritten strings" (OCR confusions)
    sheet      - data model of what was read from the sheet(s)
    decoder    - replays the moves with python-chess and repairs errors
    pgn_export - builds the PGN text
"""
