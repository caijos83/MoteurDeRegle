# Manuel utilisateur — DMN Light Engine

Guide pas-à-pas pour créer, modifier et exécuter une table de décision dans
l'IHM. Application accessible sur http://localhost:8501 une fois lancée
(voir `docs/manuel_installation.md`).

## 1. Vue d'ensemble de l'IHM

La barre de navigation en haut propose trois onglets : **Tables**, **API**,
**Paramètres**. Le cœur de l'application est l'onglet **Tables**, qui couvre
tout le cycle de vie d'une table de décision : liste → création → édition →
exécution.

## 2. Écran « Tables »

Écran d'accueil. Il affiche la liste des tables existantes avec, pour
chacune : nom, hit policy (badge *First* ou *Collect Sum*), nombre de
critères d'entrée, nombre de règles, date de dernière modification.

Actions disponibles :
- **Filtrer** par hit policy via le menu déroulant au-dessus de la liste.
- **✎** — ouvrir le détail de la table.
- **▶** — exécuter/tester la table directement.
- **🗑** — supprimer la table (suppression immédiate, sans confirmation à ce
  stade).
- **＋ Nouvelle table** — créer une nouvelle table de décision.

## 3. Créer une table de décision

Bouton **＋ Nouvelle table** depuis l'écran Tables.

### 3.1 Informations générales
- **Nom de la table** (obligatoire).
- **Description** (libre, informative).
- **Hit Policy** (obligatoire) :
  - *First* : retourne la première règle qui matche les inputs.
  - *Collect Sum* : additionne les outputs numériques de toutes les règles
    qui matchent.

### 3.2 Colonnes d'entrée et de sortie
Dans la carte « Colonnes d'entrée (critères) », ajouter chaque colonne avec :
- un **nom** (ex. `age`, `revenu`, `decision`),
- un **type** : `numérique`, `texte` ou `booléen`,
- un **rôle** : `IN` (critère d'entrée) ou `OUT` (résultat en sortie).

Une table valide nécessite au moins une colonne `IN` et une colonne `OUT`.

### 3.3 Règles de décision
Une fois les colonnes définies, le tableau des règles apparaît. Cliquer sur
**＋ Ajouter une règle** ouvre un formulaire :
- une **condition** par colonne d'entrée (laisser vide = toujours vrai),
- une **valeur de résultat** par colonne de sortie.

Opérateurs disponibles selon le type de colonne :

| Type      | Opérateurs                                                        |
|-----------|---------------------------------------------------------------------|
| numérique | `>`, `<`, `≥`, `≤`, `=`, `≠`, intervalle `entre … et …` → `[a..b]`  |
| texte     | égalité directe, appartenance à une liste (`fait partie de la liste`) |
| booléen   | `est Vrai` / `est Faux`                                            |

### 3.4 Import / Export
- **↓ Exporter** : télécharge la table en cours d'édition au format JSON.
- **↑ Importer** : charge un fichier JSON (colonnes + règles) dans le
  formulaire en cours.

### 3.5 Enregistrer
Le bouton **✓ Enregistrer** crée la table via l'API puis ouvre directement
sa page de détail.

## 4. Détail d'une table

Accessible via **✎** depuis la liste, ou automatiquement après création.

- **Cartes de statistiques** : nombre de critères, nombre de sorties, nombre
  de règles, plage de score (uniquement pertinent pour *Collect Sum*).
- **Onglet Règles** : aperçu en lecture de toutes les règles.
- **Onglet JSON** : représentation JSON brute de la table (utile pour
  copier/partager une table).
- **Onglet Historique** : non disponible dans cette version.
- **✎ Modifier** : ouvre l'écran d'édition des règles.
- **▶ Exécuter** : ouvre l'écran de simulation.
- **Zone dangereuse** (en bas de page) : suppression définitive de la table.

## 5. Modifier les règles d'une table

Écran accessible via **✎ Modifier** depuis le détail d'une table.

- Chaque règle existante est éditable directement dans le tableau (champs
  de saisie en ligne pour les conditions et les résultats).
- **🗑** sur une ligne supprime la règle correspondante immédiatement.
- **✓ Enregistrer** sauvegarde toutes les modifications du tableau en une
  fois.
- **＋ Ajouter une règle** ouvre le même formulaire que lors de la création.
- **↓ Export JSON** / **↑ Import** : mêmes fonctions qu'à la création,
  appliquées à la table existante (l'import ajoute les règles importées à
  celles déjà présentes).

Laisser un champ de condition vide (`—`) signifie que ce critère est ignoré
pour cette règle.

## 6. Exécuter / Tester une table

Écran accessible via **▶ Exécuter**.

1. Choisir la table à tester (menu déroulant en haut, si non déjà
   présélectionnée).
2. Renseigner une valeur pour chaque critère d'entrée dans le panneau
   « Valeurs d'entrée ».
3. Cliquer sur **▶ Évaluer**.

Le panneau de droite affiche :
- le **résultat** (décision pour *First*, score total pour *Collect Sum*),
- le **détail de chaque règle évaluée** : matchée (✓) ou non (✗), et pour
  *First*, les règles suivantes sont marquées « ignorée » une fois la
  première règle matchée trouvée,
- le **temps d'évaluation** en millisecondes (mesure réelle de l'appel à
  l'API, donc au moteur Mojo).

## 7. Opérateurs de condition — référence rapide

| Syntaxe        | Signification                                  | Type concerné      |
|-----------------|--------------------------------------------------|----------------------|
| `> 18`          | strictement supérieur                            | numérique           |
| `< 18`          | strictement inférieur                            | numérique           |
| `>= 18`         | supérieur ou égal                                | numérique           |
| `<= 18`         | inférieur ou égal                                | numérique           |
| `= 18`          | égal                                              | numérique           |
| `!= 18`         | différent                                        | numérique / texte / booléen |
| `[0..100]`      | intervalle fermé (bornes incluses)               | numérique           |
| `[0..100[`      | intervalle semi-ouvert (borne haute exclue)      | numérique           |
| `["a","b"]`     | appartenance à une liste de valeurs              | texte               |
| `true` / `false`| valeur booléenne directe                         | booléen             |
| *(vide)*        | condition ignorée (toujours vraie)               | tous                |

## 8. Erreurs courantes

| Message                                                | Cause                                                  |
|----------------------------------------------------------|----------------------------------------------------------|
| « Le nom de la table est obligatoire »                  | Champ nom vide lors de l'enregistrement                |
| « Ajoutez au moins une colonne d'entrée (IN) »           | Aucune colonne avec rôle `IN`                          |
| « Ajoutez au moins une colonne de sortie (OUT) »         | Aucune colonne avec rôle `OUT`                         |
| « Renseignez tous les champs de résultats »              | Une colonne de sortie n'a pas de valeur dans le formulaire de règle |
| « Colonnes d'input manquantes : … » (lors de l'exécution)| Toutes les colonnes d'entrée doivent recevoir une valeur lors de l'évaluation |
| « Aucune règle ne correspond »                           | Aucune règle ne matche les valeurs saisies              |
