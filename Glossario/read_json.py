import json
import os

def get_json_array_from_path(path: str):
    f = open(path, "r", encoding="utf8")
    file_content = f.read()
    json_array = json.loads(file_content)
    return json_array

            
ALPHABET = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "R", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]

# funzione utile all'automazione dei riferimenti
def get_termini_from_json(JSON_ARRAY) -> list[str]:
    termini: list[str] = []
    for c in ALPHABET:
        for d in JSON_ARRAY[c]:
            termini.append(d["termine"])
    return termini