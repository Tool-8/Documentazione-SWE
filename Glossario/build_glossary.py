from read_json import *
import os

# ritorna la stringa della sezione del glossario
def compose_section(letter: str, json_array) -> str:
    section = ""
    section += "\\section*{" + letter + "} \n" +"\\addcontentsline{toc}{section}{"+letter+"}" + "\n"
    for d in json_array[letter]:
        section += "\\subsection*{" + d["termine"] + "} \n "+"\\addcontentsline{toc}{subsection}{"+d["termine"]+"}" + "\n"
        section += d["definizione"] + "\n"
    return section

# genera le sezioni del Glossario e le mette nella cartella Contents
def build_glossario(dir: str) -> None:
    JSON_ARRAY = get_json_array_from_path(os.path.join(dir,"glossario.json"))
    for c in ALPHABET:
        section = compose_section(c, JSON_ARRAY)
        section_path = os.path.join(dir , "Contents" , (c + ".tex"))
        f = open(section_path, "w", encoding="utf8")
        f.write(section)
        f.close()