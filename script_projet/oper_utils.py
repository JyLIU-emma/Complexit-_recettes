"""
Script sert à annoter les opérations et les lier avec les ingrédients
"""
import re
import csv
from spacy.tokens import Span
from NER_ingredient_annotator import annotate_one_xml_to_doc
from ComplexCalculator import ComplexCalculator

# préparer les listes des non opérations et des opérations
with open("../resources/non_operation.csv", encoding="utf8") as f:
    no_operation = f.readlines()
no_operation = {i.strip() for i in no_operation}

with open("../resources/operations.csv", encoding="utf8") as f:
    reader = csv.DictReader(f, delimiter=",")
    operations = [row for row in reader]

# reformuler la liste de lexique d'opérations à un dico
dict_opers_all = {}
for o in operations:
    o['influence_ingred'] = False if o['influence_ingred'] == "0" else True
    o['espace'] = False if o['espace'] == "0" else True
    o['temps_moyenne'] = int(o['temps_moyenne'])
    dict_opers_all[o['lemma']] = o




def is_countable(ingred_info_dico):
    """
    décider si un ingrédient est dénombrable ou non : dénombrable == True   indénombrable == False
    format d'entrée: e.g. {'ingredient': ['sel'], 'quantite': '1', 'unit': 'pincée de'}
    règle:
        sans quantité  --> indénombrable
        avec quantité:
            sans unité --> dénombrable
            avec unité --> dénombrable si unité n'est pas ml,g,l,etc. ou quantité n'est pas un fraction
    """
    quantite = ingred_info_dico['quantite']
    unit = ingred_info_dico['unit']
    if quantite == "non_precis":
        return False
    elif quantite != "non_precis" and unit == "non_precis":
        return True
    elif re.match(r"(g|gr|gramme|kg|kilo|kilogramme|oz|ml|cl|c|cm|dl|l|litre)\b",unit):
        return False
    elif re.match(r"[0-9]+ ?/ ?[0-9]+", quantite):
        return False
    else:
        return True

def is_operation(token):
    """
    décider si un token est une opération, on ne prends que les impératifs ou infinitifs
    et qui ne situe pas après "pour" ou "ou"
    Args:
        spacy token type
    """
    if token.lemma_ in no_operation:
        return False
    elif "Imp" in token.morph.get("Mood") or "Inf" in token.morph.get("VerbForm"):
        arbre = token.subtree
        for child in arbre:
            if child.lemma_ in ["pour", "ou"] and child.head == token:
                return False
        return True
    else:
        return False

def find_operation_and_related_ingred(doc):
    """
    Trouver les opérations et leurs ingrédients relatifs dans le doc
    Args:
        doc: recette annotée des ingrédients, type spacy classe Doc
    Returns:
        operations: dictionnaire des opérations, format exemple:
            {'o_1': {'token_id': 1, 'action': 'couper', 'ingreds': ['1', '2']}}
        doc: recette annotée des ingrédients et des opérations
            id de niveau token: ent_id_ pour INGRED   et   ent_kb_id_ pour OPER
    """
    operations = {}
    oper_id = 1
    for token in doc:
        if is_operation(token):
            oper_ent_id = f"o_{oper_id}"

            # annoter l'opération with kb_id
            oper_ent = Span(doc, token.i, token.i+1, label="OPER", kb_id= oper_ent_id)
            doc.set_ents([oper_ent], default="unmodified")

            reletif_ingreds = []
            arbre = token.subtree
            for child in arbre:
                if child.ent_type_ == "INGRED" and child.ent_iob_ == "B":
                    reletif_ingreds.append(child.ent_id_)
            operations[oper_ent_id] = {"token_id":token.i,"action":token.lemma_, "ingreds":reletif_ingreds}
            oper_id += 1

    return operations, doc


def add_info_for_calcul_ingred(list_ingreds):
    """
    Rajouter l'info de dénombrabilité et de nombre de récipient dans la liste d'info
    Reformuler la liste à un dico, ayant l'id d'ingrédient comme la clé
    """
    dico_ingreds = {}
    for ingred in list_ingreds:
        if is_countable(ingred):
            ingred['denombrable'] = 'True'
            if re.match(r"[0-9]+ ?(/|,|\.) ?[0-9]+", ingred['quantite']):
                ingred['recipient'] = "1*X"
            else:
                ingred['recipient'] = ingred['quantite'] + "*X"
        else:
            ingred['denombrable'] = 'False'
            ingred['recipient'] = "1"
        dico_ingreds[ingred['id']] = ingred
    return dico_ingreds



def add_info_for_calcul_oper(dico_ingreds, dico_oper):
    """
    Rajouter dans le dictionnaire d'opérations de la recette: 
        1) nombre d'opération atomique pour chaque opération détectée
        2) le temps estimé pour chaque opération détectée
        3) le nombre de récipient qu'il a besoin pour cette opération (0 ou 1)
    Returns:
        dico_oper complété
    """
    for oper in dico_oper.values():
        # existe dans le lexique
        if oper['action'] in dict_opers_all:
            avg_time = dict_opers_all[oper['action']]['temps_moyenne']

            # trouver l'ingrédient relatif
            if oper['ingreds'] != []:
                # il est influencé par l'ingrédient 
                if dict_opers_all[oper['action']]['influence_ingred']:

                    #### temps estimé
                    real_time = ""
                    for ingred_found in oper['ingreds']:
                        n = dico_ingreds[ingred_found]['quantite'] if is_countable(dico_ingreds[ingred_found]) else "1"
                        real_time += n + "*X*" + str(avg_time) + "+"
                    real_time = real_time[:-1]
                    oper["temps"] = real_time

                    #### nombre d'opérations atomique
                    # il a trouver combien d'ingrédients
                    # un trouvé
                    if len(oper['ingreds']) == 1:
                        # si l'ingredient est indénombrable
                        if is_countable(dico_ingreds[oper['ingreds'][0]]): 
                            oper["nb_oper"] = "1"                       
                        # si l'ingrédient est dénombrable
                        else:
                            quantite = dico_ingreds[oper['ingreds'][0]]['quantite']
                            quantite = re.sub(r"([0-9]+) ?(\.|,|/) ?[0-9]+", "\\1", quantite) #ne prendre que la partie d'entier
                            oper["nb_oper"] = quantite + "*X"
                    # plusieurs trouvés, calculer la somme
                    else:
                        nb_oper = ""
                        for ingred_found in oper['ingreds']:
                            if is_countable(dico_ingreds[ingred_found]):
                                n = dico_ingreds[ingred_found]['quantite']
                                nb_oper = nb_oper + n + "*X+"
                            else:
                                n = "1+"
                                nb_oper = nb_oper + n
                        nb_oper = nb_oper[:-1]
                        oper["nb_oper"] = nb_oper

                # pas d'influence d'ingrédient
                else:
                    oper["nb_oper"] = "1"
                    oper["temps"] = str(avg_time)

            # ne pas trouver l'ingrédient relatif
            else:
                #### nombre d'opérations atomique
                oper["nb_oper"] = "1"

                #### temps estimé
                # influencé par l'ingrédient
                if dict_opers_all[oper['action']]['influence_ingred']:
                    oper["temps"] = str(avg_time) + "*X"
                else:
                    oper["temps"] = str(avg_time)
            
            ### info récipient
            if dict_opers_all[oper['action']]['espace']:
                oper["recipient"] = "1"
            else:
                oper["recipient"] = "0"
        
        # n'existe pas dans le lexique
        else:
            oper["temps"] = "1"
            oper["nb_oper"] = "1"
            oper["recipient"] = "0"    
    return dico_oper



def xml_to_recipe_annotated(filepath):
    """
    Annotation d'un xml
    Args:
        chemin vers le fichier xml
    Returns:
        doc : spacy classe Doc, la partie recette (preparation) annotée
        dico_ingreds : un dico des ingrédients de la recette
        dico_opers : un dico des opérations détectées dans la recette
    """
    list_ingreds, doc = annotate_one_xml_to_doc(filepath)
    dico_opers, doc = find_operation_and_related_ingred(doc)
    dico_ingreds = add_info_for_calcul_ingred(list_ingreds)
    dico_opers = add_info_for_calcul_oper(dico_ingreds, dico_opers)
    return doc, dico_ingreds, dico_opers



if __name__ == "__main__":

    xmlpath = "../corpus_recettes/recette_27440.xml"
    doc, dico_ingreds, dico_opers = xml_to_recipe_annotated(xmlpath)
    print("---------dico ingredients----------")
    print(dico_ingreds)
    print("---------dico operations----------")
    print(dico_opers)
    print("---------calcul complexite temps----------")
    calculator = ComplexCalculator(dico_ingreds,dico_opers)
    print(calculator.get_O_temps())



