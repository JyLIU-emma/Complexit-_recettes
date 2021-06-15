"""
le script principale sert à annoter un répertoire de fichiers xml de recettes
"""

import glob
import re
import os
from oper_utils import xml_to_recipe_annotated
from Ner_classifieur_annote import load_crf_model, predict_text, transform_to_xml_annote
from NER_ingredient_detector import get_content_from_xmlfile
from ComplexCalculator import ComplexCalculator


modelpath = "../ml_models/model-20210515.pkl"
ner_clf = load_crf_model(modelpath)

def annote_with_crf(filename, ner_clf):
    """
    Annoter le fichier avec CRF, renvoie une string de recette avec annotation
    """
    ingredients, text_recette = get_content_from_xmlfile(filename)
    liste = predict_text(text_recette,ner_clf)
    text_after = transform_to_xml_annote(liste)
    return text_after

def transform_doc_to_xml(doc):
    text_after = []
    for token in doc:
        if token.ent_iob_ == "O":
            text_after.append(token.text)
        elif token.ent_iob_ == "B" and token.i == doc[-1].i:
            text_after.append(f'<{token.ent_type_} id="{token.ent_kb_id_ + token.ent_id_}">' + token.text + f"</{token.ent_type_}>")
        elif token.ent_iob_ == "B" and doc[token.i+1].ent_iob_ == "I":
                text_after.append(f'<{token.ent_type_} id="{token.ent_kb_id_ + token.ent_id_}">' + token.text)
        elif token.ent_iob_ == "B" and doc[token.i+1].ent_iob_ != "I":
            text_after.append(f'<{token.ent_type_} id="{token.ent_kb_id_ + token.ent_id_}">' + token.text + f"</{token.ent_type_}>")
        elif token.ent_iob_ == "I" and token.i == doc[-1].i:
            text_after.append(token.text + f"</{token.ent_type_}>")
        elif token.ent_iob_ == "I" and doc[token.i+1].ent_iob_ == "I":
            text_after.append(token.text)
        elif token.ent_iob_ == "I" and doc[token.i+1].ent_iob_ != "I":
            text_after.append(token.text + f"</{token.ent_type_}>")
    text_after = " ".join(text_after)
    text_after = re.sub("' ", "'", text_after)
    text_after = re.sub(r" (,|\.)", "\\1", text_after)
    return text_after


def parcours_corpus_annote(corpus_path, output_dir, liste=False):
    if not liste:
        fics = glob.glob(f"{corpus_path}\*.xml")
        # fics = glob.glob(f"{corpus_path}{os.sep}*.xml")
    else:
        fics = corpus_path
    for fic in fics:
        try:
            fic_name = fic.split(f'{os.sep}')[-1]
            recette_annote_crf = annote_with_crf(fic, ner_clf)

            recette_doc_spacy, dico_ingreds, dico_opers = xml_to_recipe_annotated(fic)
            recette_annote_rules = transform_doc_to_xml(recette_doc_spacy)

            calculator = ComplexCalculator(dico_ingreds, dico_opers)
            complex_temps = calculator.get_O_temps()
            complex_espace = calculator.O_espace_f()

            ingreds = dico_ingreds_to_xml(dico_ingreds)
            opers = dico_opers_to_xml(dico_opers)

            ## add to xmlfile
            with open(fic,encoding="utf8") as f:
                xml_text = f.read()

            recette_xml_rules = '\n  <annotation methode="symbolique">\n  '+ recette_annote_rules + '\n  </annotation>'
            recette_xml_crf = '\n  <annotation methode="crf">\n  '+ recette_annote_crf + '\n  </annotation>'
            complexite_t = '\n  <complexite>\n    <temps>' + complex_temps + '</temps>\n  <complexite>'
            complexite_e = '\n  <complexite>\n    <espace>' + complex_espace + '</espace>\n  <complexite>'
            xml_text = re.sub("(</preparation>)", "\\1" + recette_xml_rules + recette_xml_crf + complexite_t + complexite_e + ingreds + opers, xml_text)

            with open(output_dir + os.sep + fic_name, "w", encoding="utf8") as f:
                f.write(xml_text)

        except Exception:
            print(f"Rencontrer problème pour: {fic}")



def dico_ingreds_to_xml(dico_ingreds):
    liste = []
    for ingred in dico_ingreds.values():
        formate = f'ingredient:{ingred["ingredient"]}\t id:{ingred["id"]}\t quantité:{ingred["quantite"]}\t unité:{ingred["unit"]}\t denombrable:{ingred["denombrable"]}\t recipient:{ingred["recipient"]}\n'
        liste.append(formate)
    liste = "".join(liste)
    liste = "\n<ingredients_trouve>\n<![CDATA[\n" + liste + "]]>\n</ingredients_trouve>"
    return liste

def dico_opers_to_xml(dico_opers):
    liste = []
    for oper_id,oper in dico_opers.items():
        formate = f'operation:{oper["action"]}\t id:{oper_id}\t ingrédients_ralatifs:{oper["ingreds"]}\t nombre_opération_atomique:{oper["nb_oper"]}\t temps:{oper["temps"]}\t recipient:{oper["recipient"]}\n'
        liste.append(formate)
    liste = "".join(liste)
    liste = "\n<operation_trouve>\n<![CDATA[\n" + liste + "]]>\n</operation_trouve>"
    return liste


if __name__ == "__main__":
    corpus_path = "../corpus_recettes/corpus_for_final"
    output = "../corpus_recettes/out_put"
    
    parcours_corpus_annote(corpus_path, output)