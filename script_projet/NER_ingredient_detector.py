import glob
import re
from bs4 import BeautifulSoup
import spacy
from spacy.tokens import Span
from spacy.language import Language

# nlp = spacy.load("fr_core_news_lg")   # vite mait pas assez juste
nlp = spacy.load('fr_dep_news_trf')

# ------------------------Préparer le pipeline de NER (basé sur les règles)-------------------------------------
# NER unit
ruler = nlp.add_pipe("entity_ruler").from_disk("../resources/unite_ingredient_patterns.jsonl")

@Language.component("expand_unit_entities")
def expand_unit_entities(doc):
    """
    Englober les tokens suivants la dernière unité jusqu'à le DET "de" avant l'ingrédient, par exemple:
    tranches ==> tranches de
    tranches ==> tranches très fines de
    """
    new_ents = []
    ents_unit = [ent for ent in doc.ents if ent.label_ == "UNIT"]
    for ent in doc.ents:
        if ent.label_ == "UNIT" and ent.end == ents_unit[-1].end:
            indice = ent.end          
            # ne pas prendre en compte les unités à la fin, comme "en [UNIT]"
            if indice-1 == doc[-1].i:
                continue
            
            tokens_after = doc[indice:]
            has_de = False
            for t in tokens_after:
                indice += 1
                if t.lemma_ in ("de","à"):
                    has_de = True
                    new_ent = Span(doc, ent.start, indice, label=ent.label)
                    new_ents.append(new_ent)
                    break
            if not has_de:
                new_ents.append(ent) 
        else:
            new_ents.append(ent)
    doc.ents = new_ents
    return doc
# ajouter le composant après le processus entity_ruler
nlp.add_pipe("expand_unit_entities", after="entity_ruler")


#------------------- Obtenir les infos dans les fichiers xml -------------------------------------

def get_content_from_xmlfile(filename):
    xml_soup = BeautifulSoup(open(filename, "r", encoding="utf8"), "xml")
    text_recette = xml_soup.preparation.text
    ingredients = [x.text for x in xml_soup.ingredients.find_all('p')]
    return ingredients, text_recette

def normalisation_ingred_phrase(text):
    # supprimer les contenus entre parenthèses, qui a beaucoup de varientes
    text = re.sub(r'\(.+?\)','',text)
    text = re.sub(r'’', "'", text)
    text = re.sub(r"([0-9,/\.]+)(g|kg|oz|ml|cl|c|cm|dl|l|kilo|litre)","\\1 \\2",text)
    # eliminer ce qui n'est pas ingredients
    if text[:5] == "Pour " or "pas de" in text:
        return None
    # traitement de structure coordonnée, séparer en portions
    text = re.sub(r'\bet\b|, ','+',text)
    # supprimer les expressions de but qui pourraient causer problème
    text = re.sub(r'pour[^\+]+','',text)
    liste_portions = [i.strip() for i in text.split("+") if i != ""]
    if liste_portions == ['']:
        return None
    return liste_portions

def term_normalise(term):
    """
    un dernier vérification avant de l'ajouter dans le dico d'ingrédient
    """
    term = re.sub(r"[+@#&%!?\|{\(\[|_\)\]},\.;/:§”“'‘…]$", "", term)
    term = re.sub(r" (-|/) ", "-",term)
    term = re.sub(r"' ", "'", term)
    term = re.sub(r"^([^\"]+)\"$","\\1",term)
    return term.strip()

def formulate_ingred_from_text(text_part):
    """
    un pipeline pour récupérer le morceau d'expression de l'ingrédient à partir du syntagme fourni, et le rendre en forme
    """
    doc = nlp(text_part)
    
    # verifier l'existance du chiffre et trouver le dernier chiffre (pour trouver le début de l'ingrédient)
    num_index = []
    for token in doc:
        if token.pos_ == "NUM" and re.match(r"[0-9]",token.text):
            num_index.append(token.i)
    if num_index == []:
        quantity = "non_precis"
    else:
        quantity = doc[num_index[0]].text
        last_num_index = num_index[-1]
        # vérifier de ne pas utiliser le chiffre à la fin
        if doc[-1].i == doc[last_num_index].i:
            try:
                last_num_index = num_index[-2]
            except Exception:
                last_num_index = num_index[0]

    # ne garde que les entités UNIT
    doc.ents = [ent for ent in doc.ents if ent.label_ == "UNIT"]

    # les cas qui n'ont pas de unité dedans
    if doc.ents == ():
        unit = "non_precis"
        # ayant une quantité au debut
        if quantity != "non_precis":
            ingred_begin_index = last_num_index+1
            # essayer d'évider de choisir les déterminant avant l'ingrédient, comme quelques, un peu de...
            for token in doc[last_num_index+1:]:
                if token.pos_ not in ["ADP", "DET", "ADJ", "ADV"]:
                    ingred_begin_index = token.i
                    break         
        # pas de quantité précise
        else:
            ingred_begin_index = 0
            for token in doc:
                if token.pos_ not in ("ADP", "DET", "ADJ", "ADV"):
                    ingred_begin_index = token.i
                    break

        # pour chaque ingrédient, on formule 2 formes: 
        # une forme complète (avec ses compléments) et une forme simple (choisir le 1er token dans ce chunk comme mot central)
        # exemple: tomate cerise   et  tomate
        ingred = [token.text for token in doc[ingred_begin_index:]]
        ingred_complet = term_normalise(" ".join(ingred))
        try:
            ingred_stem = term_normalise(ingred[0])
        except Exception:
            ingred_stem = ""
            
    # ayant une unité, prendre les tokens après l'unité comme l'ingrédient
    # s'il y en a plusieurs, tout va réécrire dans le boucle donc seulement la dernière est prise en compte
    else:
        for ent in doc.ents:
            unit = ent.text
            ingred = []
            # selectionner les tokens d'ingrédients, jeter le "ou" et les tokens suivants pour évider les problèmes
            for token in doc[ent.end:]:
                if token.text != "ou" :
                    ingred.append(token.text)
                else:
                    break

            ingred_complet = term_normalise(" ".join(ingred))
            ingred_stem = ""
            for token in doc[ent.end:]:
                if doc[ent.end-1] in token.children:
                    ingred_stem = term_normalise(token.text)

    ingred_list =[]
    # choisir cette manière d'ajout c'est pour garder une priorité pour forme complète
    if ingred_complet != "":
        ingred_list.append(ingred_complet)
    if ingred_stem != ingred_complet and ingred_stem != "":
        ingred_list.append(ingred_stem)

    if ingred_list != []:
        return {"ingredient":ingred_list, "quantite":quantity, "unit":unit}
    else:
        return None



def create_ingred_lexique(train_path):
    # une liste totale de tous les ingrédients trouvés dans train
    liste_ingred_total = []
    fics = glob.glob(train_path)
    for fic in fics:
        text_ingred, recette = get_content_from_xmlfile(fic)
        liste_ingred_total.extend(text_ingred)
    
    list_global = []
    for one_line in liste_ingred_total:
        one_line_cleaned = normalisation_ingred_phrase(one_line)
        if one_line_cleaned: # verifier c'est pas None
            for part in one_line_cleaned:
                ingred_quant = formulate_ingred_from_text(part)
                if ingred_quant:
                    list_global.append(ingred_quant)
    terms = set()
    for i in list_global:
        ingreds = set(i['ingredient'])
        terms = terms|ingreds
    terms_to_remove = set()
    for term in terms:
        if re.match(r'\.|de |à |un |[0-9]',term):
            terms_to_remove.add(term)
    return terms - terms_to_remove

def get_one_recipe_ingreds(filepath):
    text_ingred, recette = get_content_from_xmlfile(filepath)
    list_ingred = []
    ingred_id = 1  #rajouter un id pour chaque ingredient
    lexique_ingred = []
    for line in text_ingred:
        line_norm = normalisation_ingred_phrase(line)
        if line_norm:
            for part in line_norm:
                ingred_quant = formulate_ingred_from_text(part)
                if ingred_quant: #rajouter seulement ceux dans lesquels ingrédients n'est pas vide
                    ingred_quant['id'] = str(ingred_id)
                    list_ingred.append(ingred_quant)
                    ingred_id += 1
    for i in list_ingred:
        ingreds = i['ingredient']
        for form in ingreds:
            lexique_ingred.append((form, i['id']))
        ingred_id += 1
    return list_ingred,lexique_ingred

def write_lexique_to_file(train_data, output_file):
    terms = create_ingred_lexique(train_data)
    print(len(terms))
    with open(output_file,"w",encoding="utf8") as f:
        for term in terms:
            print(term, file=f)
        
if __name__ == "__main__":
    # # création d'un lexique d'ingrédients et le stocker dans le disque
    # train_data = "../corpus_recettes/train/*.xml"
    # output_file = "../resources/ingreds_dict.txt"
    # write_lexique_to_file(train_data, output_file)

    # test l'output d'un seul fichier
    filepath = "../corpus_recettes/recette_14452.xml"
    ingred_list,lexique = get_one_recipe_ingreds(filepath)
    print("---info complet---")
    for i in ingred_list:
        print(i)
    print("---lexique---")
    print(lexique)
    
