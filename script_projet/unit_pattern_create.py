# transform ingredients' units list to spacy patterns file
# for later use in rule-based NER of ingredients' unit

import spacy
# nlp = spacy.load("fr_core_news_lg")
nlp = spacy.load('fr_dep_news_trf')
ruler = nlp.add_pipe("entity_ruler")

with open("../resources/unite_ingredient.txt", encoding="utf8") as f:
    liste_unit = f.read().split("\n")
unit_pattern_list = []
for unit in liste_unit:
    tokens = unit.split(" ")
    pattern_tokens = [{"LEMMA":tokens[0]}]
    if len(tokens) > 1:
        for t in tokens[1:]:
            pattern_tokens.append({"ORTH":t})
    ner_pattern = {"label":"UNIT", "pattern":pattern_tokens}
    unit_pattern_list.append(ner_pattern)

ruler.add_patterns(unit_pattern_list)
ruler.to_disk("../resources/unite_ingredient_patterns.jsonl")