from bs4 import BeautifulSoup
import re
import shutil
import glob
# from MainAnnotator import parcours_corpus_annote     # à décommenter si on veut lancer l'annotation
from sympy import symbols


def get_liste_of_niveau():
    liste_f = []
    liste_tf = []
    liste_d = []
    liste_md = []
    liste = [liste_tf, liste_f, liste_md, liste_d]
    l_name = ["tf", "f", "md", "d"]

    for fic in glob.glob("..\corpus_recettes\output_correlation\*.xml"):
        xml_soup = BeautifulSoup(open(fic, "r", encoding="utf8"), "xml")
        niveau = xml_soup.niveau.text
        if niveau == "Facile":
            liste_f.append(fic)
        elif niveau == "Moyennement difficile":
            liste_md.append(fic)
        elif niveau == "Très facile":
            liste_tf.append(fic)
        else:
            liste_d.append(fic)
    print(len(liste_tf), len(liste_f), len(liste_md), len(liste_d))



def annote_xml_files():
    l_name = ["tf", "f", "md", "d"]
    liste_file = []
    for i in range(len(l_name)):
        with open(f"decompte_{l_name[i]}.txt", "r", encoding="utf8") as f:
            l = f.readlines()
        l = [i.strip() for i in l]
        liste_file.extend(l[:80])
    print("ready")
    parcours_corpus_annote(liste_file,"..\corpus_recettes\output_correlation", liste=True)

def calcul_corelation():
    liste_f = []
    liste_tf = []
    liste_d = []
    liste_md = []
    liste = [liste_tf, liste_f, liste_md, liste_d]
    l_name = ["tf", "f", "md", "d"]
    result_t = []
    result_s = []
    X = 1
    for fic in glob.glob("..\corpus_recettes\output_correlation\*.xml"):
        xml_soup = BeautifulSoup(open(fic, "r", encoding="utf8"), "xml")
        niveau = xml_soup.niveau.text
        complex_temps = xml_soup.temps.text[7:]
        complex_temps = eval(complex_temps)
        complex_espace = xml_soup.espace.text[7:]
        complex_espace = eval(complex_espace)
        if niveau == "Facile":
            liste_f.append((complex_temps,complex_espace))
        elif niveau == "Moyennement difficile":
            liste_md.append((complex_temps,complex_espace))
        elif niveau == "Très facile":
            liste_tf.append((complex_temps,complex_espace))
        else:
            liste_d.append((complex_temps,complex_espace))

    for i in range(len(liste)):
        c_temps = sum([t[0] for t in liste[i]])/len(liste[i])
        c_espace = sum([t[1] for t in liste[i]])/len(liste[i])
        result_t.append(round(c_temps,2))
        result_s.append(round(c_espace,2))

    print(*l_name, sep = "\t")
    print(len(liste_tf), len(liste_f), len(liste_md), len(liste_d), sep = "\t")
    print(*result_t, sep = "\t")
    print(*result_s, sep = "\t")
    print(*[(result_t[i]+result_s[i]) for i in range(4)], sep="\t")


if __name__ == "__main__":
    #-----------chercher dans le plus grand corpus le------------------
    # get_liste_of_niveau()   # 8647 7123 1116 84
    #-------annoter les fichiers trouvés et les mettre dans output_correlation------
    # annote_xml_files()
    #-------------calculer la corrélation dans ce répertoire-----------------------------
    calcul_corelation()    # 84 76 74 77   nombre de fichiers sous l'ordre: tf f md d

    