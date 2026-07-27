'use strict';
/* ═══════════════════════════════════════════════════════════════════════════
   RHESO — données publiées
   ─────────────────────────────────────────────────────────────────────────
   PÉRIMÈTRE VOLONTAIREMENT LIMITÉ. Cette page publie la STRUCTURE du
   référentiel : les cinq curseurs, leur question, et le nom des vingt-cinq
   réglages avec leur définition en une ligne.

   Elle NE publie PAS le contenu opérationnel des fiches — « ce que je fais »,
   « ce que je dis », l’intention, la frontière avec le niveau voisin — ni les
   règles d’interaction complètes de la console. Ce contenu est le cœur du
   savoir-faire RHESO ; il se transmet en formation et n’a pas à être
   téléchargeable depuis une page publique.

   Une seule fiche est publiée en entier — H3 — comme démonstration.
   `full:true` marque cette fiche. N’ajoutez pas de second `full`.

   Ne publiez jamais ici : le réglage attendu d’une situation (quelle
   combinaison pour une crise, un recadrage…), ni les seuils d’interaction
   entre curseurs. C’est du savoir-faire appliqué, pas de la structure.
   ═══════════════════════════════════════════════════════════════════════════ */

const DEMO = 'H3';

const AXES = [
  {
    id:'R', name:'RÉALITÉ', full:'Réalité',
    c:'#405B4A', t:'#405B4A', ct:'#33503F', l:'#8FBBA1',
    sub:'Le curseur du niveau d’exposition aux faits.',
    key:'Qu’est-ce que je choisis de montrer de la réalité ?',
    watch:'Doser pour protéger est légitime. Tout exposer sans discernement peut fracturer.',
    levels:[
      {code:'R1', label:'Je simplifie',          line:'Je ne montre qu’une part rassurante ou essentielle des faits.'},
      {code:'R2', label:'Je focalise',           line:'Je choisis un angle précis et j’assume d’écarter le reste.'},
      {code:'R3', label:'Je décris le système',   line:'Je pose l’ensemble des faits disponibles, sans interpréter.'},
      {code:'R4', label:'J’analyse',             line:'Je relie les faits entre eux et je fais apparaître ce qui se joue.'},
      {code:'R5', label:'Je lève le voile',      line:'Je nomme ce qui est tu, ce qui dérange, ce qui fâche.'}
    ]
  },
  {
    id:'H', name:'HUMAIN', full:'Humain',
    c:'#C8A010', t:'#C8A010', ct:'#7A620A', l:'#E5C74A',
    sub:'Le curseur du niveau de présence à l’autre.',
    key:'Quelle place est-il juste de donner à l’humain ?',
    watch:'Trop peu d’humanité peut blesser inutilement. Trop peut faire perdre le cap.',
    levels:[
      {code:'H1', label:'Je mets à distance',     line:'Je privilégie la tâche sur la relation.'},
      {code:'H2', label:'Je prends acte',         line:'Je reconnais l’autre sans m’impliquer davantage.'},
      {code:'H3', label:'J’écoute vraiment',      line:'Je cherche à comprendre ce que vit l’autre.',
       full:true,
       int:'Créer un espace d’échange sincère.',
       do:['Je pose des questions ouvertes',
           'Je reformule pour vérifier ma compréhension',
           'Je suspends mon jugement et mon agenda'],
       say:['Si je comprends bien, ce qui est difficile…',
            'Qu’est-ce qui se passe de ton côté ?',
            'Dis-moi ce que tu vis là-dedans.'],
       bd:'H2 reconnaît sans aller chercher ; H3 cherche activement à comprendre. H2 accuse réception, H3 ouvre la porte.'},
      {code:'H4', label:'J’intègre la personne',  line:'Je tiens compte de l’autre dans ma décision et ma façon d’agir.'},
      {code:'H5', label:'Je priorise la relation',line:'Je place le lien avant l’objectif immédiat.'}
    ]
  },
  {
    id:'E', name:'ÉNERGIE', full:'Énergie',
    c:'#D06818', t:'#D06818', ct:'#9C4C10', l:'#EFA265',
    sub:'Le curseur du niveau d’intensité dans l’action.',
    key:'Avec quelle intensité est-il pertinent de communiquer ?',
    watch:'Pas assez d’élan peut laisser stagner. Trop peut épuiser ou braquer.',
    levels:[
      {code:'E1', label:'Je laisse respirer',     line:'Je reste en retrait et j’observe ce qui émerge.'},
      {code:'E2', label:'Je mets en mouvement',   line:'Je donne une impulsion légère, je propose sans imposer.'},
      {code:'E3', label:'Je fais avancer',        line:'Je maintiens un rythme soutenu et stable.'},
      {code:'E4', label:'J’accélère',             line:'J’intensifie l’engagement au-delà du rythme habituel.'},
      {code:'E5', label:'J’intensifie',           line:'Je concentre toute l’énergie sur un point de bascule.'}
    ]
  },
  {
    id:'S', name:'SENS', full:'Sens',
    c:'#3A7A8A', t:'#3A7A8A', ct:'#2F6674', l:'#8CC0CD',
    sub:'Le curseur du niveau d’éclairage sur la direction et ses raisons.',
    key:'Jusqu’où est-il utile d’expliciter le cap et le pourquoi ?',
    watch:'Trop peu de sens laisse les gens sans repère. Trop peut noyer l’action dans le symbolique.',
    levels:[
      {code:'S1', label:'Je m’inscris dans la continuité', line:'Le sens est déjà là, inutile de le redire.'},
      {code:'S2', label:'Je rappelle la direction',        line:'Je remets légèrement le cap en évidence.'},
      {code:'S3', label:'J’explique pourquoi',             line:'Je clarifie la direction et la logique qui y conduit.'},
      {code:'S4', label:'J’organise la feuille de route',  line:'Je structure le sens dans la durée.'},
      {code:'S5', label:'J’embarque',                      line:'Je connecte au sens profond pour créer l’adhésion.'}
    ]
  },
  {
    id:'O', name:'OUVERTURE', full:'Ouverture',
    c:'#C0607A', t:'#C0607A', ct:'#A63A58', l:'#E2A9B7',
    sub:'Le curseur du niveau d’accueil des points de vue extérieurs.',
    key:'Jusqu’où est-il utile d’ouvrir le jeu aux autres ?',
    watch:'Trop fermer peut créer des angles morts. Trop ouvrir peut déstabiliser.',
    levels:[
      {code:'O1', label:'Je ferme',            line:'Je protège une décision ou un cadre — je ne rouvre pas.'},
      {code:'O2', label:'Je limite',           line:'J’accepte certains retours, mais je garde la main.'},
      {code:'O3', label:'J’intègre les idées', line:'J’accueille les points de vue pour enrichir ma réflexion.'},
      {code:'O4', label:'Je co-construis',     line:'Je fais évoluer ma position avec le collectif.'},
      {code:'O5', label:'J’explore',           line:'Je remets les évidences en question pour créer du nouveau.'}
    ]
  }
];

/* Exercices — des situations à régler, sans réglage préchargé.
   La console posait auparavant sept « prémix » : chaque situation arrivait
   avec ses cinq valeurs. C'était donner la réponse, et la donner en clair
   dans le code source. Les situations sont conservées, les valeurs non :
   la console propose l'exercice, le réglage juste se travaille en formation.
   N'ajoutez pas de champ `mix` ici. */
const EXERCICES = [
  {tag:'CRISE',    name:'Situation de crise'},
  {tag:'CADRE',    name:'Recadrer'},
  {tag:'PROJET',   name:'Lancer un projet'},
  {tag:'ÉCOUTE',   name:'Temps d’écoute'},
  {tag:'IDÉES',    name:'Brainstorming'},
  {tag:'ÉLAN',     name:'Mobiliser'},
  {tag:'DÉCISION', name:'Décision déjà prise'}
];

const SITUATIONS = [
  {k:'prise', label:'Prise de poste', title:'Entrer dans une histoire déjà en cours',
   lines:['Je reprends une équipe existante.','J’accueille un nouveau collaborateur.'],
   note:'Le premier réglage installe durablement ce que l’équipe croit possible de dire.'},
  {k:'quotidien', label:'Quotidien', title:'Faire travailler sans épuiser',
   lines:['J’anime une réunion d’équipe.','Je fais un point d’avancement.','Je prépare ou débriefe une intervention.'],
   note:'Le quotidien est là où un mauvais réglage coûte le plus, parce qu’il se répète.'},
  {k:'entretiens', label:'Entretiens', title:'Dire ce qui compte au bon niveau',
   lines:['Je fais un point individuel positif.','Je fais un point individuel négatif.'],
   note:'Un entretien réussi n’est pas un entretien agréable : c’est un entretien juste.'},
  {k:'recadrage', label:'Recadrage', title:'Poser une limite sans casser la relation',
   lines:['Je recadre un collaborateur.','Je refuse une demande.','Je traite un comportement inadapté.'],
   note:'La limite tient si la relation survit — et inversement.'},
  {k:'conflits', label:'Conflits', title:'Réduire la température, restaurer le dialogue',
   lines:['Je réponds à une personne en colère.','Je gère une réunion tendue.','Je rétablis le dialogue après un conflit.'],
   note:'En conflit, le réglage précède le contenu : personne n’entend un argument avant d’être reconnu.'},
  {k:'changement', label:'Changement', title:'Mettre en mouvement sans perdre le sens',
   lines:['J’annonce une réorganisation.','Je modifie les méthodes de travail.','J’accompagne une transformation.'],
   note:'Une transformation échoue rarement sur la stratégie. Elle échoue sur le réglage de sa communication.'},
  {k:'client', label:'Relation client', title:'Rester juste quand la pression monte',
   lines:['Je réponds à une réclamation.','Je reçois un client mécontent.'],
   note:'Le client n’attend pas qu’on lui donne raison. Il attend qu’on lui montre qu’on a compris.'},
  {k:'recrutement', label:'Recrutement', title:'Créer les conditions d’une vraie rencontre',
   lines:['Je conduis un entretien d’embauche.','J’intègre un nouveau collaborateur.'],
   note:'Le réglage de l’entretien dit à la personne ce qu’elle pourra dire, plus tard, une fois en poste.'},
  {k:'collectif', label:'Collectif', title:'Faire émerger une décision praticable',
   lines:['Je recherche une décision collective.','Je relance une équipe qui s’essouffle.','Je célèbre une réussite sans perdre l’élan.'],
   note:'Une décision collective ne vaut que par ce qu’elle rend exécutable le lendemain.'}
];

const REFS = ['Air France','Société Générale','Thales','Capgemini','UPS','Procter & Gamble',
  'Fnac Darty','AG2R','Médecins du Monde','Hôpital Franco-Britannique','Michelin',
  'General Electric','Enedis','Easy Cash','goFLUENT'];
