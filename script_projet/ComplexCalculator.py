"""
Classe utilisée pour le calcul des complexités en temps et en espace
"""
from sympy import symbols

class ComplexCalculator:

    def __init__(self, dico_ingreds, dico_opers):
        self.ingreds = dico_ingreds.values()
        self.opers = dico_opers.values()
        self.X = symbols("X")
    

    def calcul_nb_ingreds(self):
        """
        calculer le nombre total des ingrédient de la recette, avec variable X
        """
        X = self.X
        result = []
        for ingred in self.ingreds:
            if ingred['denombrable'] == "True":
                n = ingred['quantite'] + "*X"
            else:
                n = "1"
            result.append(n)
        self.nbre_ingreds = str(eval("+".join(result)))
        return self.nbre_ingreds

    def calcul_nb_opers(self):
        X = self.X
        result = []
        for oper in self.opers:
            result.append(oper['nb_oper'])
        self.nbre_opers = str(eval("+".join(result)))
        return self.nbre_opers
    
    def calcul_coef(self):
        X = 1
        coef = "(" + self.nbre_opers + ")/(" + self.nbre_ingreds + ")"
        self.coef = eval(coef)
        return self.coef
    
    def O_temps_f(self):
        X = self.X
        O_temps = f"{self.coef}*({self.nbre_ingreds})"
        self.O_temps = str(eval(O_temps))
        return "f(X) = " + self.O_temps
    
    def calcul_avg_temps_opb(self):
        X = 1
        result = []
        for oper in self.opers:
            result.append(oper['temps'])
        self.temps_estime = eval("+".join(result))
        nb_opb = eval(self.nbre_opers)
        self.avg_t_oper = self.temps_estime / nb_opb
        return self.avg_t_oper
    
    def temps_estime_X(self,X):
        result = eval(f"{self.O_temps}*{self.avg_t_oper}")
        return result
    
    def O_espace_f(self):
        X = self.X
        result = []
        for oper in self.opers:
            result.append(oper['recipient'])
        for ingred in self.ingreds:
            result.append(ingred['recipient'])
        self.O_espace = str(eval("+".join(result)))
        return "f(X) = " + self.O_espace
    
    def get_O_temps(self):
        self.calcul_nb_ingreds()
        self.calcul_nb_opers()
        self.calcul_coef()
        return self.O_temps_f()
        
