"""
Module de gestion de stock respectant l'analyse fonctionnelle et les normes qualité.
Sépare: Stockage (FIFO + Dette), Alertes (Circulaire) et Préparation (LIFO).
"""

import logging
from collections import deque, Counter

# Configuration du journal d'événements
logging.basicConfig(level=logging.INFO, format='%(asctime)s ADMIN %(message)s')


class SystemeAlerte:
    """Gère le buffer circulaire d'alertes (Taille 3)."""

    def __init__(self):
        """Initialise le buffer vide."""
        self.historique = [None] * 3
        self.index_ecr = 0

    def noter(self, message: str):
        """Enregistre une alerte (écrasement circulaire)."""
        logging.warning(message)
        self.historique[self.index_ecr] = message
        self.index_ecr = (self.index_ecr + 1) % 3

    def afficher_tout(self):
        """Affiche les alertes du plus ancien au plus récent."""
        print("\n--- PANNEAU D'ALERTES ---")
        for i in range(3):
            pos = (self.index_ecr + i) % 3
            msg = self.historique[pos]
            etat = msg if msg else "Pas d'alerte."
            print(f"Slot {i + 1} : {etat}")


class Inventaire:
    """Gère le stock physique (FIFO) et comptable (entiers relatifs)."""

    def __init__(self, systeme_alerte: SystemeAlerte):
        """Init: _files pour le physique, _comptes pour la dette."""
        self._files = {}
        self._comptes = Counter()  # Permet les nombres négatifs (Dette)
        self._alerteur = systeme_alerte

    def ajouter(self, produit: str):
        """Entrée de stock (Ajout droite)."""
        if produit not in self._files:
            self._files[produit] = deque()
        self._files[produit].append(produit)
        self._comptes[produit] += 1

    def quantite_comptable(self, produit: str) -> int:
        """Retourne le stock réel (peut être négatif)."""
        return self._comptes[produit]

    def sortir(self, produit: str):
        """Sort un produit et décrémente le compte (crée dette si vide)."""
        self._comptes[produit] -= 1
        file_prod = self._files.get(produit)
        
        item = file_prod.popleft() if (file_prod and file_prod) else None
        
        self._verifier_seuil(produit)
        if item is None:
            self._signaler_rupture(produit)
        return item

    def _verifier_seuil(self, produit: str):
        """Alerte si le stock comptable passe sous 2."""
        restant = self._comptes[produit]
        if restant < 2:
            msg = f"ALERTE: Stock faible {produit} (Reste: {restant})"
            self._alerteur.noter(msg)

    @staticmethod
    def _signaler_rupture(produit: str):
        """Log la création d'une dette (Backorder)."""
        msg = f"!!! RUPTURE : {produit} mis en dette (Backorder)."
        print(msg)
        logging.error("Dette créée sur %s", produit)


class GestionnaireCommandes:
    """Façade : Analyse, valide et prépare les colis."""

    def __init__(self, arrivage_init: str = None):
        """Initialise les sous-systèmes."""
        self.alerteur = SystemeAlerte()
        self.inventaire = Inventaire(self.alerteur)
        if arrivage_init:
            self._traiter_arrivage(arrivage_init)

    def _traiter_arrivage(self, texte: str):
        """Injecte les produits initiaux."""
        produits = self._parser(texte)
        for prod in produits:
            self.inventaire.ajouter(prod)
        print(f"--> Arrivage traité : {len(produits)} produits.")

    def traiter_commande(self, texte: str, strict: bool = True) -> list:
        """Point d'entrée principal pour une commande."""
        demandes = self._parser(texte)
        
        if strict and not self._verifier_faisabilite(demandes):
            print("!!! COMMANDE ANNULEE : Stock insuffisant.")
            return []
            
        return self._assembler_colis(demandes)

    def _verifier_faisabilite(self, demandes: list) -> bool:
        """Vérifie si le stock couvre la demande (Stratégie 1)."""
        besoins = Counter(demandes)
        possible = True
        for prod, qte in besoins.items():
            if self.inventaire.quantite_comptable(prod) < qte:
                print(f"Manque {prod} (Requis: {qte})")
                possible = False
        return possible

    def _assembler_colis(self, demandes: list) -> list:
        """Exécute la sortie de stock (Stratégie 2)."""
        colis_brut = []
        for prod in demandes:
            item = self.inventaire.sortir(prod)
            if item:
                colis_brut.append(item)
        
        return self._trier_par_volume(colis_brut)

    def afficher_etat(self):
        """Proxy pour l'affichage des alertes."""
        self.alerteur.afficher_tout()

    @staticmethod
    def _trier_par_volume(produits: list) -> list:
        """Trie décroissant (Gros volumes au fond)."""
        produits.sort(key=GestionnaireCommandes._extraire_vol, reverse=True)
        return produits

    @staticmethod
    def _parser(texte: str) -> list:
        """Nettoie et découpe la chaîne d'entrée."""
        if not texte:
            return []
        nettoye = texte.replace(',', ' ')
        return [x.strip() for x in nettoye.split() if x.strip()]

    @staticmethod
    def _extraire_vol(nom_produit: str) -> int:
        """Extrait l'entier du nom (A3 -> 3)."""
        try:
            return int(nom_produit[1:])
        except (ValueError, IndexError):
            return 0


if __name__ == "__main__":
    # --- Scénario de conformité ---
    ARRIVAGE = "A1, A1, B2, C3, A3"
    GEST = GestionnaireCommandes(ARRIVAGE)

    print("\n--- TEST 1 : ANNULATION (Stratégie 1) ---")
    # Demande 3 A1 alors qu'il n'y en a que 2 -> Doit échouer
    GEST.traiter_commande("A1, A1, A1", strict=True)

    print("\n--- TEST 2 : ENDETTEMENT (Stratégie 2) ---")
    # Demande 3 A1 -> Prend les 2 dispo, met le 3ème en dette (-1)
    # Le colis ne contiendra que 2 A1.
    COLIS = GEST.traiter_commande("A1, A1, A1", strict=False)
    
    print(f"\nColis physique livré : {COLIS}")
    print(f"Dette A1 (Attendue -1) : {GEST.inventaire.quantite_comptable('A1')}")
    
    GEST.afficher_etat()
