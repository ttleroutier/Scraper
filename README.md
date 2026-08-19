# Maps Lead Finder

Outil local d'extraction de fiches d'entreprises depuis Google Maps.
Interface Streamlit, tableau qui se remplit en direct, sauvegarde continue,
export Excel et CSV.

- Entree : un mot-cle + un point central (adresse ou GPS) + un rayon en km.
- Sortie : nom, adresse, telephone, site, email, description, categorie,
  note, nombre d'avis, coordonnees, distance au point choisi.
- Execution : sur votre PC, navigateur visible, CAPTCHA resolu manuellement.

IMPORTANT : aucun contournement de CAPTCHA ni de protection technique n'est
implemente. Respectez les conditions d'utilisation des sites visites et le
RGPD pour les donnees de contact collectees.


===============================================================================
SOMMAIRE
===============================================================================

PARTIE A - DOCUMENTATION TECHNIQUE (pour vous ou une IA)
  1. Demarrage rapide
  2. Carte du projet : ou se trouve quoi
  3. Blocs internes de chaque fichier
  4. Table de decision pour modifier le projet
  5. Flux de donnees
  6. Contrats des fonctions
  7. Regles a respecter
  8. Modele de demande pour une IA

PARTIE B - MODE D'EMPLOI DETAILLE (utilisation quotidienne)
  9. Installation pas a pas (Windows)
  10. Lancer l'outil
  11. Les deux fenetres
  12. Remplir le formulaire
  13. Reglages de cadence
  14. Lancer une recherche
  15. Pendant la collecte
  16. Que faire si un CAPTCHA apparait
  17. Recuperer les resultats
  18. Reprendre une recherche interrompue
  19. Conseils de volume
  20. Depannage
  21. Cadre legal


===============================================================================
PARTIE A - DOCUMENTATION TECHNIQUE
===============================================================================

-------------------------------------------------------------------------------
1. DEMARRAGE RAPIDE
-------------------------------------------------------------------------------

```bash
git clone <url-du-repo>
cd maps-lead-finder

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

streamlit run app.py
```


-------------------------------------------------------------------------------
2. CARTE DU PROJET : OU SE TROUVE QUOI
-------------------------------------------------------------------------------

```text
maps-lead-finder/
├── app.py                 # Interface Streamlit
├── config.py              # Toutes les constantes reglables
├── models.py              # Structures de donnees
├── geo.py                 # Geocodage, distance, zoom
├── storage.py             # SQLite, exports
├── scraper.py             # Playwright, Google Maps
├── website_enricher.py    # Email et description depuis le site
├── requirements.txt
├── README.md
├── .gitignore
├── data/                  # Base SQLite (genere, non versionne)
└── browser_profile/       # Profil Chromium persistant (genere)
```

Chaque fichier a une responsabilite unique.

| Fichier              | Role                                              | Ne contient jamais    |
|----------------------|---------------------------------------------------|-----------------------|
| config.py            | Constantes reglables                              | Logique metier        |
| models.py            | Dataclasses partagees                             | I/O, reseau           |
| geo.py               | Adresse -> GPS, distance, zoom carte              | Playwright, base      |
| storage.py           | SQLite, DataFrame, export Excel/CSV               | Scraping, UI          |
| scraper.py           | Playwright, selecteurs, cadence, CAPTCHA          | Streamlit             |
| website_enricher.py  | Email et description depuis le site web           | Google Maps           |
| app.py               | Interface, boutons, tableau, exports              | Selecteurs CSS        |


-------------------------------------------------------------------------------
3. BLOCS INTERNES DE CHAQUE FICHIER
-------------------------------------------------------------------------------

Chaque fichier est decoupe en blocs numerotes en commentaire, par exemple :
`# ---------------- 3. DISTANCE`
Cela permet de cibler une modification sans lire le reste du fichier.

config.py
  1. PATHS
  2. RATE LIMITING
  3. BROWSER
  4. SEARCH
  5. WEBSITE ENRICHMENT

models.py
  1. A PLACE
  2. SEARCH PARAMETERS
  3. SPEED SETTINGS
  4. RUNTIME SHARED COUNTERS

geo.py
  1. GEOCODING
  2. DISTANCE
  3. RADIUS -> MAP ZOOM LEVEL

storage.py
  1. SCHEMA
  2. WRITE
  3. READ
  4. EXPORT

scraper.py
  1. SELECTORS
  2. RUN CONTROLLER
  3. RATE LIMITER
  4. PAGE UTILITIES
  5. LIST SCROLLING
  6. DETAIL EXTRACTION
  7. MAIN LOOP

website_enricher.py
  1. ROBOTS.TXT
  2. FETCH
  3. PARSE
  4. ENTRY

app.py
  1. APP STATE
  2. WORKER LAUNCH
  3. SIDEBAR UI
  4. CONTROL BAR
  5. STATUS
  6. LIVE TABLE
  7. EXPORT
  8. AUTO REFRESH


-------------------------------------------------------------------------------
4. TABLE DE DECISION POUR MODIFIER LE PROJET
-------------------------------------------------------------------------------

| Je veux...                                | Fichier              | Bloc      |
|-------------------------------------------|----------------------|-----------|
| Changer les delais par defaut             | config.py            | 2         |
| Rendre le navigateur invisible            | config.py            | 3         |
| Changer le dossier de la base             | config.py            | 1         |
| Changer la langue de Google Maps          | scraper.py           | 7 (hl=fr) |
| Reparer une extraction cassee             | scraper.py           | 1         |
| Changer la profondeur de defilement       | config.py            | 4         |
| Modifier le filtre par rayon              | scraper.py           | 7         |
| Ameliorer la detection de CAPTCHA         | scraper.py           | 4         |
| Changer le calcul de distance             | geo.py               | 2         |
| Changer le zoom selon le rayon            | geo.py               | 3         |
| Ajouter des pages contact scannees        | config.py            | 5         |
| Filtrer certains emails                   | website_enricher.py  | 3         |
| Ajouter une colonne au tableau            | app.py               | 6         |
| Ajouter un champ de formulaire            | app.py               | 3         |
| Changer un export                         | storage.py           | 4         |
| Changer la vitesse de rafraichissement    | app.py               | 8         |

Ajouter un champ complet (exemple : horaires d'ouverture) :
  1. models.py bloc 1        -> ajouter l'attribut a Place
  2. scraper.py bloc 1       -> ajouter le selecteur
  3. scraper.py bloc 6       -> extraire la valeur
  4. storage.py bloc 1       -> ajouter la colonne au CREATE TABLE
  5. storage.py haut fichier -> ajouter le nom dans COLUMNS
  6. app.py bloc 6           -> ajouter au visible_columns


-------------------------------------------------------------------------------
5. FLUX DE DONNEES
-------------------------------------------------------------------------------

```text
Sidebar (app.py 3)
      | SearchConfig + RateSettings
      v
start_run (app.py 2)  ->  thread en arriere-plan
      |
      v
run_scrape (scraper.py 7)
      |-- collect_card_links   (scraper.py 5)
      |-- extract_place        (scraper.py 6)
      |-- haversine_km         (geo.py 2)   -> filtre par rayon
      |-- enrich               (website_enricher.py 4)
      '-- on_result -> save_place (storage.py 2) -> SQLite
                                                       |
                                                       v
                                   load_dataframe (storage.py 3)
                                                       |
                                                       v
                              tableau + exports (app.py 6 et 7)
```


-------------------------------------------------------------------------------
6. CONTRATS DES FONCTIONS
-------------------------------------------------------------------------------

```python
# geo.py
geocode_address(address: str) -> tuple[float, float, str] | None
haversine_km(lat1, lon1, lat2, lon2) -> float
zoom_for_radius(radius_km: float) -> int

# storage.py
init_db() -> None
save_place(place: Place, run_id: str) -> None
known_place_ids(run_id: str) -> set[str]
load_dataframe(run_id: str | None = None) -> pandas.DataFrame
list_runs() -> list[tuple[str, int]]
dataframe_to_excel_bytes(frame) -> bytes
dataframe_to_csv_bytes(frame) -> bytes

# scraper.py
class ScrapeController:
    pause() / resume() / stop()
    should_stop() -> bool
    wait_if_paused() -> None
    status: str
    captcha_detected: bool
    stats: RunStats

run_scrape(search, rates, controller, on_result, already_seen) -> None  # bloquant
extract_place(page, url: str) -> Place | None
is_captcha(page) -> bool

# website_enricher.py
enrich(website: str) -> tuple[str | None, str | None]   # (email, description)
```


-------------------------------------------------------------------------------
7. REGLES A RESPECTER
-------------------------------------------------------------------------------

- scraper.py ne doit jamais importer streamlit.
- app.py ne doit jamais contenir de selecteur CSS.
- Toute constante reglable va dans config.py, pas en dur dans le code.
- Tout nouveau champ persistant doit etre ajoute a trois endroits :
  Place, COLUMNS, CREATE TABLE.
- Le scraper communique avec l'interface uniquement via ScrapeController
  et le callback on_result.
- Aucune fonction ne doit tenter de contourner un CAPTCHA.
- Le code est ecrit en anglais, la documentation en francais.


-------------------------------------------------------------------------------
8. MODELE DE DEMANDE POUR UNE IA
-------------------------------------------------------------------------------

Pour faire modifier le projet sans envoyer tout le code, collez ceci :

  Projet : Maps Lead Finder (Python, Streamlit, Playwright).
  Architecture :
    config.py            = constantes reglables
    models.py            = dataclasses Place, SearchConfig, RateSettings
    geo.py               = geocodage, distance haversine, zoom
    storage.py           = SQLite, exports Excel et CSV
    scraper.py           = Playwright, selecteurs, cadence, CAPTCHA
    website_enricher.py  = email et description depuis le site
    app.py               = interface Streamlit

  Regles : scraper.py n'importe pas streamlit ; app.py ne contient pas
  de selecteur CSS ; les constantes vont dans config.py ; un nouveau champ
  doit etre ajoute a Place, COLUMNS et CREATE TABLE.

  Demande : <votre demande>
  Fichier concerne : <fichier> bloc <numero>
  Voici uniquement ce fichier :
  <coller le fichier>

  Renvoie uniquement le bloc modifie, avec son numero de bloc.


===============================================================================
PARTIE B - MODE D'EMPLOI DETAILLE
===============================================================================

-------------------------------------------------------------------------------
9. INSTALLATION PAS A PAS (WINDOWS)
-------------------------------------------------------------------------------

Prerequis : Python 3.10 ou superieur, et Git.
Verifiez avec :

```bash
python --version
git --version
```

Etape 1 - Recuperer le projet

```bash
git clone <url-du-repo>
cd maps-lead-finder
```

Etape 2 - Creer un environnement virtuel

```bash
python -m venv .venv
.venv\Scripts\activate
```

La ligne de commande doit maintenant commencer par (.venv).

Etape 3 - Installer les dependances

```bash
pip install -r requirements.txt
```

Etape 4 - Installer le navigateur Playwright

```bash
playwright install chromium
```

Cette etape telecharge environ 150 Mo. Elle n'est a faire qu'une seule fois.


-------------------------------------------------------------------------------
10. LANCER L'OUTIL
-------------------------------------------------------------------------------

A chaque utilisation :

```bash
cd maps-lead-finder
.venv\Scripts\activate
streamlit run app.py
```

Votre navigateur ouvre automatiquement http://localhost:8501
Si ce n'est pas le cas, ouvrez cette adresse manuellement.

Pour arreter l'outil : Ctrl + C dans le terminal.


-------------------------------------------------------------------------------
11. LES DEUX FENETRES
-------------------------------------------------------------------------------

Quand une recherche demarre, deux fenetres coexistent :

  Fenetre 1 - Streamlit (localhost:8501)
    Vos reglages, les boutons, les compteurs, le tableau, les exports.

  Fenetre 2 - Chromium pilote par Playwright
    Google Maps qui defile tout seul. C'est ici que s'affiche un CAPTCHA.

NE FERMEZ JAMAIS la fenetre Chromium pendant une collecte : cela interrompt
le travail en cours. Vous pouvez la reduire, mais pas la fermer.


-------------------------------------------------------------------------------
12. REMPLIR LE FORMULAIRE
-------------------------------------------------------------------------------

Tous les champs sont dans la colonne de gauche.

Mot-cle
  Ce que vous cherchez. Exemples : plombier, restaurant italien,
  garage automobile, agence immobiliere.
  Conseil : un mot-cle precis donne de meilleurs resultats qu'un mot-cle large.

Point central
  Deux modes au choix.
  - Adresse : tapez une ville ou une adresse complete. L'outil la convertit
    en coordonnees via OpenStreetMap et affiche l'adresse retenue.
  - Coordonnees GPS : entrez directement latitude et longitude.
    Utile si l'adresse est mal reconnue.

Rayon (km)
  De 1 a 50 km. Toute fiche situee au-dela est ignoree et comptee
  dans le compteur "Hors rayon".

Nombre max de fiches
  Limite haute pour la recherche. Google Maps renvoie rarement plus de
  120 resultats par recherche, quel que soit ce chiffre.
  Pour couvrir une grande zone, faites plusieurs recherches avec des
  points centraux differents.

Chercher email et description sur le site
  Si coche, l'outil visite le site de chaque entreprise pour tenter d'y
  trouver un email public et une description. Cela ralentit la collecte
  d'environ 2 a 5 secondes par fiche. Le fichier robots.txt est respecte.
  Les emails ne figurent presque jamais sur Google Maps : sans cette option,
  la colonne email restera vide.


-------------------------------------------------------------------------------
13. REGLAGES DE CADENCE
-------------------------------------------------------------------------------

Ces reglages determinent la vitesse et le risque de blocage.

Delai entre fiches (s)
  Attente aleatoire entre deux fiches. Defaut : 3 a 8 secondes.
  Plus bas = plus rapide mais plus risque.

Pause longue toutes les N fiches
  Nombre de fiches avant une pause prolongee. Defaut : 30.
  Mettre 0 desactive les pauses longues (deconseille).

Duree de la pause longue (s)
  Duree aleatoire de cette pause. Defaut : 30 a 90 secondes.

Profils conseilles :

  Prudent (recommande)
    delai 5 a 12 s | pause toutes les 20 fiches | pause 60 a 120 s
    Environ 200 a 300 fiches par jour, risque faible.

  Equilibre (par defaut)
    delai 3 a 8 s  | pause toutes les 30 fiches | pause 30 a 90 s
    Environ 400 a 600 fiches par jour.

  Rapide (risque eleve)
    delai 1 a 3 s  | pause toutes les 50 fiches | pause 20 a 40 s
    CAPTCHA probable, a reserver aux petits volumes ponctuels.


-------------------------------------------------------------------------------
14. LANCER UNE RECHERCHE
-------------------------------------------------------------------------------

1. Remplissez le formulaire.
2. Cliquez sur Start.
3. Si vous avez saisi une adresse, verifiez le message bleu qui indique
   le point central retenu. Si l'adresse est fausse, cliquez sur Stop
   et passez en mode Coordonnees GPS.
4. La fenetre Chromium s'ouvre. Au premier lancement, une banniere de
   consentement Google peut apparaitre : l'outil clique automatiquement
   sur "Tout accepter". Sinon, cliquez vous-meme.
5. La liste des resultats defile automatiquement, puis chaque fiche est
   ouverte une par une.


-------------------------------------------------------------------------------
15. PENDANT LA COLLECTE
-------------------------------------------------------------------------------

Quatre compteurs en haut de page :

  Statut            etat courant (running, paused, long pause, finished)
  Fiches listees    nombre de fiches reperees dans la liste
  Enregistrees      nombre de fiches reellement sauvegardees
  Hors rayon        fiches ecartees car trop eloignees du point central

Le tableau se met a jour automatiquement toutes les 3 secondes.
Vous pouvez trier les colonnes en cliquant sur leur titre.

Quatre boutons de controle :

  Start    lance une nouvelle recherche
  Pause    suspend proprement apres la fiche en cours
  Resume   reprend la collecte
  Stop     arrete definitivement la recherche en cours

Un bandeau depliant "Erreurs" en bas de page liste les fiches ayant echoue.
Quelques erreurs sont normales : certaines fiches n'ont pas de page detaillee.


-------------------------------------------------------------------------------
16. QUE FAIRE SI UN CAPTCHA APPARAIT
-------------------------------------------------------------------------------

Deroulement automatique :
  1. L'outil detecte le CAPTCHA.
  2. Il se met en pause tout seul.
  3. Un bandeau orange apparait dans Streamlit.
  4. Le statut devient "CAPTCHA - solve it in the browser".

Ce que vous devez faire :
  1. Basculez sur la fenetre Chromium.
  2. Resolvez le CAPTCHA manuellement.
  3. Attendez que Google Maps se recharge normalement.
  4. Revenez sur Streamlit et cliquez sur Resume.

Si les CAPTCHA reviennent souvent :
  - augmentez les delais ;
  - reduisez le nombre de fiches avant pause ;
  - allongez la duree des pauses ;
  - arretez la collecte et reprenez plus tard dans la journee.

Aucune resolution automatique n'est prevue et n'en sera ajoutee.


-------------------------------------------------------------------------------
17. RECUPERER LES RESULTATS
-------------------------------------------------------------------------------

Deux boutons sous le tableau :

  Telecharger Excel  -> fichier .xlsx
  Telecharger CSV    -> fichier .csv encode UTF-8 avec BOM,
                        s'ouvre correctement dans Excel francais

Vous pouvez telecharger a tout moment, meme pendant la collecte.
Les donnees sont egalement conservees en permanence dans data/results.sqlite.

Colonnes exportees :
  place_id, name, address, phone, email, website, description, category,
  rating, reviews, latitude, longitude, distance_km, maps_url, run_id,
  created_at


-------------------------------------------------------------------------------
18. REPRENDRE UNE RECHERCHE INTERROMPUE
-------------------------------------------------------------------------------

Chaque recherche recoit un identifiant unique de la forme :
  motcle_AAAAMMJJ_HHMMSS

Toutes les fiches sont ecrites dans SQLite au fur et a mesure. En cas de
coupure (fermeture, plantage, arret), rien n'est perdu.

Note : le bouton Start cree systematiquement un nouvel identifiant.
Une reprise automatique du meme run n'est pas encore implementee.
La fonction known_place_ids() de storage.py est deja prete pour cela :
c'est la prochaine evolution prevue.


-------------------------------------------------------------------------------
19. CONSEILS DE VOLUME
-------------------------------------------------------------------------------

- Google Maps plafonne en pratique autour de 120 resultats par recherche.
- Pour couvrir une grande ville, decoupez en plusieurs points centraux
  avec un rayon de 3 a 5 km chacun.
- Pour couvrir un metier sur une region, variez les mots-cles proches
  (plombier, plomberie, depannage plomberie).
- Etalez les gros volumes sur plusieurs jours plutot que sur une session.
- L'objectif de 1000 a 10000 fiches par jour reste tres ambitieux et
  entrainera des blocages, meme avec des delais eleves.


-------------------------------------------------------------------------------
20. DEPANNAGE
-------------------------------------------------------------------------------

"playwright: command not found"
  L'environnement virtuel n'est pas active. Lancez .venv\Scripts\activate

"Executable doesn't exist" au demarrage du navigateur
  Lancez : playwright install chromium

Adresse introuvable
  Le service de geocodage n'a pas reconnu l'adresse. Simplifiez-la
  (ville + pays) ou passez en mode Coordonnees GPS.

Tableau vide alors que le navigateur travaille
  La premiere fiche prend du temps (defilement complet de la liste).
  Patientez une a deux minutes.

Toutes les colonnes email sont vides
  Verifiez que la case d'enrichissement est cochee. Beaucoup de sites
  ne publient aucun email, ou le protegent contre l'extraction.

Nom ou telephone systematiquement vides
  Google a probablement change son code HTML.
  Corrigez le dictionnaire SELECTORS dans scraper.py bloc 1.

L'interface se fige
  Le rafraichissement automatique relance la page toutes les 3 secondes.
  Sur les gros volumes, augmentez cette valeur dans app.py bloc 8.

Le navigateur demande le consentement a chaque lancement
  Supprimez le dossier browser_profile/ puis relancez, et acceptez une fois.

Port 8501 deja utilise
  Lancez : streamlit run app.py --server.port 8502


-------------------------------------------------------------------------------
21. CADRE LEGAL
-------------------------------------------------------------------------------

- Cet outil automatise une navigation publique. Son usage peut contrevenir
  aux conditions d'utilisation de Google. Vous en assumez la responsabilite.
- Aucune protection technique n'est contournee.
- Le fichier robots.txt des sites d'entreprises est verifie avant toute
  visite lors de l'enrichissement.
- Les emails collectes sont des donnees personnelles au sens du RGPD.
  Vous devez disposer d'une base legale pour les traiter, informer les
  personnes concernees et respecter leur droit d'opposition.
- N'utilisez pas ces donnees pour de la prospection non sollicitee sans
  verifier les regles applicables a votre secteur et a votre pays.
