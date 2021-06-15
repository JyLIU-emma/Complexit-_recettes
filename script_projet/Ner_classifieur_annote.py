"""
pour voir le test, lancer:
python Ner_classifieur_annote.py
"""
from Ner_classifieur_train import sent2features, sent2tokens
import dill as pickle
import re
import spacy
nlp = spacy.load("fr_core_news_lg")

def load_crf_model(modelpath):
    with open(modelpath, "rb") as model_file:
        return pickle.load(model_file)

def pretraite_text(text):
    text = re.sub(r"\n", " ",text.strip())
    text = re.sub(r" +", " ",text)
    doc = nlp(text)
    text_listform = []
    for sent in doc.sents:
        tokens = []
        for token in sent:
            tokens.append((token.text, token.pos_, "NoValue"))
        text_listform.append(tokens)
    return text_listform

def predict_text(text, clf):
    text_listform = pretraite_text(text)
    text_to_pred = [sent2features(s) for s in text_listform]
    text_tokens = [sent2tokens(s) for s in text_listform]
    text_annote_label = clf.predict(text_to_pred)

    token_list = []
    for i in range(len(text_tokens)):
        sent = text_tokens[i]
        for j in range(len(sent)):
            token = (sent[j], text_annote_label[i][j])
            token_list.append(token)
    return token_list

def transform_to_xml_annote(liste):
    text_after = []
    for i in range(len(liste)-1):
        if liste[i][1] == "O":
            text_after.append(liste[i][0])
        elif liste[i][1] == "B-INGRED" and liste[i+1][1] == "I-INGRED":
            text_after.append("<INGRED>" + liste[i][0])
        elif liste[i][1] == "B-INGRED" and liste[i+1][1] != "I-INGRED":
            text_after.append("<INGRED>" + liste[i][0] + "</INGRED>")
        elif liste[i][1] == "I-INGRED" and liste[i+1][1] == "I-INGRED":
            text_after.append(liste[i][0])
        elif liste[i][1] == "I-INGRED" and liste[i+1][1] != "I-INGRED":
            text_after.append(liste[i][0] + "</INGRED>")
    if liste[-1][1] == "O":
        text_after.append(liste[-1][0])
    elif liste[-1][1] == "B-INGRED":
        text_after.append("<INGRED>" + liste[-1][0] + "</INGRED>")
    else:
        text_after.append(liste[-1][0] + "</INGRED>")
        
    text_after = " ".join(text_after)
    text_after = re.sub("' ", "'", text_after)
    text_after = re.sub(r" (,|\.)", "\\1", text_after)
    return text_after



if __name__ == "__main__":
    # exemple
    text = """
    Éplucher et tailler en lamelle les aubergines, les mettre à dégorger en saupoudrant d'un peu de sel entre chaque tranche. Laisser 30 min.
        Pendant ce temps désosser l’épaule d'agneaux et le détailler en très petit morceaux.
        Émincer les oignons, faire cuire à la poêle dans de l'huile d'olive, très doucement, ajouter la viande, le sel, le poivre, le cumin, le thym, remuer laisser 5 à 7 min et réserver.
        Essuyer les aubergines avec un papier absorbant, les faire revenir dans de l'huile d'olive dans une poêle. Mettre à égoutter sur du papier absorbant.
        Dans un plat allant au four, disposer une couche d'aubergine, poivre, une couche de viande, une couche de tomate découpées en fines rondelles, émietter la moitié de la fêta.
        Faire une autre couche en terminant avec une couche d'aubergine et émietter le reste de fêta.
        Mettre au four à 180°C (thermostat 6), 40 min.
    """
    modelpath = "../ml_models/model-20210515.pkl"
    ner_clf = load_crf_model(modelpath)
    liste = predict_text(text,ner_clf)
    text_after = transform_to_xml_annote(liste)
    print(text_after)