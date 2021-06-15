"""
usage:
python Ner_classifieur_train.py path/to/train/csv path/to/test/csv
example:
python Ner_classifieur_train.py "../resources/train_sents_annote.tsv" "../resources/test_sents_annote.tsv"
"""

import pandas as pd
import numpy as np
import csv
import sys
import os
from datetime import datetime

from sklearn.metrics import classification_report
import sklearn_crfsuite
from sklearn_crfsuite import metrics
import dill as pickle


# ----------- pour restructurer les données ------------
class SentenceGetter(object):
    """
    transformer l'info dans csv à une liste des phrases, chaque phrase est une liste de tokens,
    chaque token est représenté par un tuple (token, pos, tag)
    """
    def __init__(self, data):
        self.n_sent = 1
        self.data = data
        self.empty = False
        agg_func = lambda s: [(w, p, t) for w, p, t in zip(s['word'].values.tolist(), 
                                                           s['pos'].values.tolist(), 
                                                           s['tag'].values.tolist())]
        self.grouped = self.data.groupby('sent_id').apply(agg_func)
        self.sentences = [s for s in self.grouped]
        
    def get_next(self):
        try: 
            s = self.grouped[self.n_sent]
            self.n_sent += 1
            return s 
        except:
            return None

# ---------------------- extraction des features -------------------------------

def word2features(sent, i):
    word = sent[i][0]
    postag = sent[i][1]
    
    features = {
        'bias': 1.0, 
        'word.lower()': word.lower(), 
        'word[-3:]': word[-3:],
        'word[-2:]': word[-2:],
        'word.isupper()': word.isupper(),
        'word.istitle()': word.istitle(),
        'word.isdigit()': word.isdigit(),
        'postag': postag,
        # 'postag[:2]': postag[:2],
    }
    if i > 0:
        word1 = sent[i-1][0]
        postag1 = sent[i-1][1]
        features.update({
            '-1:word.lower()': word1.lower(),
            '-1:word.istitle()': word1.istitle(),
            '-1:word.isupper()': word1.isupper(),
            '-1:postag': postag1,
            # '-1:postag[:2]': postag1[:2],
        })
    else:
        features['BOS'] = True
    if i < len(sent)-1:
        word1 = sent[i+1][0]
        postag1 = sent[i+1][1]
        features.update({
            '+1:word.lower()': word1.lower(),
            '+1:word.istitle()': word1.istitle(),
            '+1:word.isupper()': word1.isupper(),
            '+1:postag': postag1,
            # '+1:postag[:2]': postag1[:2],
        })
    else:
        features['EOS'] = True
    return features

def sent2features(sent):
    return [word2features(sent, i) for i in range(len(sent))]

def sent2labels(sent):
    return [label for token, postag, label in sent]

def sent2tokens(sent):
    return [token for token, postag, label in sent]


#------------- préparation des données -----------------------
def prepare_data(data_path,nb_lines="all"):
    df = pd.read_csv(data_path, sep='\t', header=0, quoting=csv.QUOTE_NONE, encoding="utf8")
    if nb_lines != "all":
        df = df[:nb_lines]
    df = df.fillna(" ")
    getter = SentenceGetter(df)
    sentences = getter.sentences
    X = [sent2features(s) for s in sentences]
    y = [sent2labels(s) for s in sentences]
    return X,y

# ----------- sauvegarde du modèle ----------------------------
def save(model: any, path: str) -> None:
    time = datetime.now()
    time = time.strftime('%Y%m%d')
    model_name = f'model-{time}.pkl'
    path = f'{path}{os.sep}{model_name}'
    with open(path, 'wb') as save_file:
        pickle.dump(model, save_file)

def main():
    train_data = sys.argv[1]
    test_data = sys.argv[2]
    X_train, y_train = prepare_data(train_data, 50000)
    X_test, y_test = prepare_data(test_data, 10000)

    crf = sklearn_crfsuite.CRF(
        algorithm='lbfgs',
        c1=0.1,
        c2=0.1,
        max_iterations=100,
        all_possible_transitions=True
    )

    crf.fit(X_train, y_train)
    y_pred = crf.predict(X_test)

    report = metrics.flat_classification_report(y_test, y_pred, labels=['B-INGRED','I-INGRED'])  #ne veut pas qu'il calculer aussi la classe O
    print(report)
    stockage = input("Sauvegarder le modèle ? (Y/N)")
    if stockage == "Y":
        save(crf, "../ml_models")

if __name__ == "__main__":
    main()



