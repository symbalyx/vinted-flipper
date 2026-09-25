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
