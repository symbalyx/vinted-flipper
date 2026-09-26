package fr.riviere.spinosaure.cerveau;

/**
 * Tous les reglages du comportement, en blocs et en ticks (20 ticks = 1 s).
 * Les portees d'attaque sont mesurees sur le modele a l'echelle de rendu 0.7
 * (6.7 blocs de haut, 13.4 de long) : museau a 5.9 blocs devant le centre, mains a
 * 2.8, bout de queue a 7.6 blocs derriere.
 * Champs publics et non finaux : les tests les ajustent, un fichier de config peut le faire.
 */
public final class Reglages {

    // ------------------------------------------------------------ perception
    public double porteeVue = 48;
    /** Ouverture TOTALE du cone de vision (degres). Les yeux sont lateraux : large. */
    public double coneVue = 220;
    /** Portee a laquelle on entend un joueur selon son allure. */
    public double ouieSprint = 24, ouieMarche = 12, ouieAccroupi = 4;
    /** Au contact on sent toujours, meme dans le dos. */
    public double proximiteSentie = 3.5;
    /** Attention : un joueur percu reste suivi ce nombre de ticks, a portee de vue, meme hors du cone. */
    public long attention = 300;
    /** Sous l'eau, la vue vers la surface est reduite a cette fraction. */
    public double vueDepuisEau = 0.5;
    /** Duree pendant laquelle une position vue reste exploitable. */
    public long dureeMemoire = 600;

    // ------------------------------------------------------------ menace
    /** Demi-vie de la menace (ticks). La rancune, elle, ne decroit que tres lentement. */
    public double demiVieMenace = 400;
    public double demiVieRancune = 12000;
    /** Un coup a distance pese plus : il ne peut pas riposter. */
    public double poidsDistance = 1.6;

    // ------------------------------------------------------------ choix de la cible
    /** La nouvelle cible doit faire mieux que l'actuelle de ce facteur pour la remplacer. */
    public double hysteresis = 1.3;
    /** Engagement minimal sur une cible avant de pouvoir en changer (sauf perte). */
    public long engagementMin = 60;
    /** Un joueur est « isole » quand son plus proche allie est au-dela de cette distance. */
    public double isolement = 14;

    // ------------------------------------------------------------ tactique
    public double seuilRepli = 0.30;
    public double seuilRetour = 0.75;
    public double seuilAcculeSansEau = 0.15;
    /** Nombre de joueurs proches a partir duquel on considere etre en infériorite. */
    public int surnombre = 3;
    public double rayonGroupe = 24;
    /** Coups a distance d'un joueur inatteignable avant de rompre la ligne de vue. */
    public int coupsTireurAvantEsquive = 2;
    public long fenetreTireur = 200;
    public long dureeEsquive = 200;
    /** Sans progres vers la cible pendant ce temps : elle est jugee inatteignable. */
    public long delaiBlocage = 100;
    public long dureeInatteignable = 300;
    /** Traque : distance en dessous de laquelle la proie ne peut plus l'ignorer. */
    public double traqueContact = 10;
    /** Un joueur regarde le spinosaure si l'ecart d'angle est sous ce seuil. */
    public double angleRegard = 28;
    /** Fige sous un regard plus longtemps que ca : il bondit. */
    public long figeMax = 90;

    // ------------------------------------------------------------ horreur
    // La tension monte avec le temps passe a traquer UNE proie (ticks cumules) :
    //   phase 1 (< phaseFilature) : il observe de loin, planque ;
    //   phase 2 (< phaseFrappe)   : il la file, derriere elle, en silence ;
    //   phase 3                   : il frappe a la premiere ouverture.
    public double phaseFilature = 600;          // 30 s
    public double phaseFrappe = 1800;           // 1 min 30
    /** Face a un groupe, il n'ose frapper qu'apres une tres longue traque. */
    public double tensionGroupe = 4800;         // 4 min
    public double demiVieTension = 2400;
    /** Ouverture : proie a moins de cette distance, dos tourne, sans allie proche. */
    public double distanceFrappe = 14;
    public double isolementFrappe = 16;
    /** Blesse par un joueur plus proche que ca : il riposte ; plus loin : il se derobe. */
    public double distanceRiposte = 8;
    /** Vu de plus pres que ca : il disparait. Plus loin : il se fige et soutient le regard. */
    public double distanceDisparition = 24;
    public double distanceObservation = 28;
    public double distanceFilature = 16, distanceFilatureProche = 10;
    /** Frappe eclair : au plus 2 attaques ou 6 s, puis il disparait. */
    public long dureeFrappe = 120;
    public int attaquesParFrappe = 2;
    public double degatsFinFrappe = 0.05;       // fraction de vie perdue qui l'interrompt
    public long dureeDisparition = 200;

    // ------------------------------------------------------------ armes a feu (TaCZ)
    /** Un coup de feu s'entend a cette distance. */
    public double ouieTir = 96;
    /** Tireur qui le voit a moins de cette distance : il est sous le feu, il se met a couvert. */
    public double porteeFeu = 48;
    /** Face a une arme a feu, il file et observe de plus loin. */
    public double margeFeu = 6;
    /** Un canon braque sur lui a moins de cette distance : il disparait (pas de duel de regards). */
    public double disparitionFeu = 40;

    // ------------------------------------------------------------ directeur (a la Alien Isolation)
    /** Sans contact depuis ce delai, le « directeur » lui souffle la zone du joueur le plus proche. */
    public long delaiIndice = 1200;              // 1 min
    public double porteeIndice = 160;
    public double flouIndice = 16;
    /** Pression : temps passe a moins de `distancePression` d'un joueur sans l'avoir frappe. */
    public double distancePression = 32;
    public double pressionMax = 3600;            // 3 min : il se retire pour laisser respirer
    public long dureeRetrait = 1600;             // 80 s en coulisses

    // ------------------------------------------------------------ attaques
    public double porteeMorsure = 6.8;
    public double porteeGriffes = 4.5;
    public double porteeSaisie = 6.0;
    public double porteeQueue = 7.5;
    public double chargeMin = 9, chargeMax = 20;
    public double bondMin = 7, bondMax = 12;
    /** Au-dela de cet angle depuis l'axe du corps, un joueur est « dans le dos ». */
    public double angleArriere = 115;
    /** Maintien d'un joueur saisi : liberation sur ces seuils (fair-play multijoueur). */
    public long maintienMax = 120;
    public double liberationParAllies = 20;
    public double liberationParVictime = 12;
    public double regenParSeconde = 2.0;

    public static Reglages defaut() {
        return new Reglages();
    }
}
