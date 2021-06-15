import re
import glob
import spacy
from NER_ingredient_detector import get_content_from_xmlfile, get_one_recipe_ingreds

# nlp = spacy.load("fr_core_news_lg")
nlp = spacy.load('fr_dep_news_trf')
ruler = nlp.add_pipe("entity_ruler")

#----------------Préparer doc pour le calcul de la complexité --------------------

def annotate_one_xml_to_doc(filepath):
    """
    Annoter l'ingrédients dans le fichiers
    Args:
        le chemin vers le fichier à annoter
        la base de nombre de phrases à incrémenter
    Returns:
        liste: une liste des ingredients de document, format exemple :
            [{'ingredient': ['farine'], 'quantite': '550', 'unit': 'g de', 'id': '1'}]
        doc: la recette annotée de l'ingrédient, spacy classe Doc
    """
    # preparer ruler avec lexique d'ingrédients trouvés
    liste,lexique = get_one_recipe_ingreds(filepath)
    patterns = []
    for term in lexique:
        patterns.append({"label":"INGRED", "pattern":term[0], "id":term[1]})
    ruler.initialize(lambda: [], nlp=nlp, patterns=patterns)

    # obtenir le texte à annoter
    ingredients, recette = get_content_from_xmlfile(filepath)
    # nettoyer le texte
    text = recette.strip()
    text = re.sub(r"\n", " ",text)
    text = re.sub(r" +", " ",text)

    # annotation : doc
    doc = nlp(text)
    doc.ents = [ent for ent in doc.ents if ent.label_ == "INGRED"]

    return liste,doc


#----------------Préparer fichiers pour l'entrainement de l'annotateur CRF --------------------

def annotate_one_xml(filepath, sent_id):
    """
    Annoter l'ingrédients dans le fichiers
    Args:
        le chemin vers le fichier à annoter
        la base de nombre de phrases à incrémenter
    Returns:
        lines: une liste des tokens de document, un token par éléments dans la liste, chaque ligne contient sent_id, forme de token, token pos tag et le label de entité nommée (BIO) de ce token
        sent_id : nouveau nombre de phrases accumulées
    """
    # preparer ruler
    liste,lexique = get_one_recipe_ingreds(filepath)
    patterns = []
    for term in lexique:
        patterns.append({"label":"INGRED", "pattern":term[0], "id":term[1]})
    ruler.initialize(lambda: [], nlp=nlp, patterns=patterns)

    # obtenir le texte à annoter
    ingredients, recette = get_content_from_xmlfile(filepath)
    # nettoyer le texte
    text = recette.strip()
    text = re.sub(r"\n", " ",text)
    text = re.sub(r" +", " ",text)

    # annotation et transformation: un token par élément
    lines = []
    doc = nlp(text)
    doc.ents = [ent for ent in doc.ents if ent.label_ == "INGRED"]
    for sent in doc.sents:
        for token in sent:
            ne_label = token.ent_iob_ if token.ent_iob_ == "O" else token.ent_iob_+"-"+token.ent_type_
            lines.append([str(sent_id), token.text, token.pos_, ne_label])
        sent_id += 1

    return lines, sent_id


def annotate_a_corpus_dir(dir_path, output_path):
    """
    Boucler la phase d'annotation d'un xml, obtenir un fichier tsv englobe tous les recettes annotées, un token par ligne
    Returns:
        la liste de cet ensemble de tokens
    """
    lines_total = []
    all_file_path = glob.glob(dir_path + "/*.xml")
    counter = 1
    sent_id = 1
    for one_file in all_file_path:
        try:
            print(f"fichier en cours d'annoter: {one_file}\tprogrès: {counter/len(all_file_path)}\r",end="",flush=True)
            lines, sent_id = annotate_one_xml(one_file, sent_id=sent_id)
            lines_total.extend(lines)
            counter += 1

            # rajouter dans le fichier
            new_lines = ["\t".join(i) for i in lines]
            new_text = "\n".join(new_lines)
            with open(output_path,"a", encoding="utf8") as csvfile:
                csvfile.write("sent_id\tword\tpos\ttag\n" + new_text + "\n")
        except KeyboardInterrupt:
            break
        except Exception:
            print()
            print(f"!! Problème : {one_file}")
    print()
    print(f"{counter} fichiers annotés avec succès!")
    return lines_total

            
if __name__ == "__main__":
    # préparer un fichier pour l'entraînement du crf
    data_path = "../corpus_recettes/test"
    # Attention: le programme va rajouter les nouvelles annotation à la fin
    tsv_path = "../resources/test_sents_annote.tsv"
    annotate_a_corpus_dir(data_path, tsv_path)

    # filepath = "../corpus_recettes/train2/recette_10697.xml"
    # lines,sent_id = annotate_one_xml(filepath,1)
    # # regarder le format de sortie
    # print("-"*30)
    # for l in lines:
    #     print(l)



