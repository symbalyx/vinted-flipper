package fr.riviere.spinosaure.cerveau;

import fr.riviere.spinosaure.cerveau.Decision.Allure;

import java.util.List;

/**
 * Pilotage physique : comment un animal de 13 blocs de long suit un chemin.
 *
 * <p>Le deplacement vanilla fait pivoter un mob de 90 degres par tick et change sa vitesse
 * instantanement : un spinosaure lance a pleine charge ferait demi-tour sur place. Ici :
 * <ul>
 *   <li><b>vitesse de lacet bornee</b> et d'autant plus faible qu'il va vite : rayon de
 *       braquage de 0.7 bloc au pas, 3 blocs en course, 5.3 en charge. Un joueur qui
 *       s'ecarte au dernier moment esquive la charge : c'est voulu ;</li>
 *   <li><b>il ralentit</b> quand le point vise est dans son cercle de braquage, au lieu de
 *       tourner autour indefiniment, et <b>freine avant les virages</b> du chemin ;</li>
 *   <li><b>inertie</b> : accelerations et freinages progressifs ;</li>
 *   <li><b>pivot sur place</b> quand la destination est derriere lui a l'arret ;</li>
 *   <li><b>endurance</b> : la course et la charge l'essoufflent ; essouffle, il marche
 *       le temps de recuperer. Les joueurs peuvent donc le semer en courant longtemps.</li>
 * </ul>
 * Repere Minecraft : lacet 0 = sud (+Z), il augmente en tournant a DROITE.
 */
public final class Pilote {

    public enum Geste { AUCUN, VIRAGE_GAUCHE, VIRAGE_DROITE, PIVOT, FREINAGE }

    /**
     * @param lacet   nouveau lacet du corps (degres)
     * @param vitesse multiplicateur de MOVEMENT_SPEED a appliquer
     */
    public record Commande(float lacet, double vitesse, Geste geste) {
    }

    /** Attribut MOVEMENT_SPEED de l'entite. */
    public static final double ATTRIBUT = 0.34;
    public static final double PIVOT_DEG = 4.5;          // tourne_sur_place : 90 deg/s
    public static final double ACCEL = 0.03, FREIN = 0.07;
    public static final double DUREE_COURSE = 240, DUREE_CHARGE = 100;   // ticks d'endurance
    public static final double RECUP = 1.0 / 300;                        // 15 s pour recuperer
    public static final double DEBORD = 1.5;          // debordement tolere dans un virage (blocs)
    public static final double ANTICIPATION = 4.0;    // distance de visee sur le chemin (blocs)
    public static final double GAIN_CAP = 0.3;

    private double v;                 // multiplicateur courant
    private double endurance = 1.0;
    private boolean essouffle;
    private boolean lance;            // a atteint la course : un arret declenche le freinage

    public double vitesseCourante() {
        return v;
    }

    public double endurance() {
        return endurance;
    }

    public boolean essouffle() {
        return essouffle;
    }

    /** Vitesse au sol, blocs par tick, pour un multiplicateur donne (mesure du moteur vanilla). */
    public static double vitesseSol(double mult) {
        double s = ATTRIBUT * mult;
        return 2.2 * s * s;
    }

    /** Vitesse de lacet maximale (degres/tick) a ce multiplicateur. */
    public static double lacetMax(double mult) {
        if (mult < 0.05) {
            return PIVOT_DEG;
        }
        return 7.5 - 3.2 * Math.min(mult / 1.25, 1.0);
    }

    /** Rayon de braquage minimal (blocs) a ce multiplicateur. */
    public static double rayon(double mult) {
        if (mult < 0.05) {
            return 0;
        }
        return vitesseSol(mult) / Math.toRadians(lacetMax(mult));
    }

    /** Plus grand multiplicateur <= plafond dont le rayon de braquage tient dans r. */
    static double vitessePourRayon(double r, double plafond) {
        for (double m = plafond; m > 0.05; m -= 0.025) {
            if (rayon(m) <= r) {
                return m;
            }
        }
        return 0;
    }

    /**
     * Fenetre de noeuds a viser : ceux qui sont a moins de `anticipation` blocs a
     * l'horizontale et a la meme hauteur a 1 bloc pres (on s'arrete au premier qui sort).
     * Renvoie le nombre de noeuds retenus (0 si aucun).
     */
    public static int fenetre(Vec moi, List<Vec> noeuds, double anticipation) {
        int n = 0;
        for (Vec p : noeuds) {
            if (p.distanceH(moi) > anticipation || Math.abs(p.y() - moi.y()) > 1.0) {
                break;
            }
            n++;
        }
        return n;
    }

    /**
     * Point vise lisse : la MOYENNE des noeuds de la fenetre. Le chemin vanilla est en
     * escalier des qu'il est en diagonale ; viser un noeud (meme lointain) fait alterner le
     * cap entre deux marches (mesure : 3.5 a 4.5 degres/tick d'oscillation, assez pour
     * declencher les animations de virage en ligne droite). La moyenne redresse l'escalier.
     */
    public static Vec viseeMoyenne(Vec moi, List<Vec> noeuds, double anticipation) {
        int n = fenetre(moi, noeuds, anticipation);
        if (n == 0) {
            return null;
        }
        double x = 0, y = 0, z = 0;
        for (int i = 0; i < n; i++) {
            x += noeuds.get(i).x();
            y += noeuds.get(i).y();
            z += noeuds.get(i).z();
        }
        return new Vec(x / n, y / n, z / n);
    }

    public static float lacetVers(double dx, double dz) {
        return (float) (Math.toDegrees(Math.atan2(dz, dx)) - 90.0);
    }

    public static double ecart(double a, double b) {
        double d = (b - a) % 360.0;
        if (d >= 180) {
            d -= 360;
        }
        if (d < -180) {
            d += 360;
        }
        return d;
    }

    /**
     * @param pos       position actuelle
     * @param lacet     lacet actuel du corps
     * @param vise      point de chemin vise (null : s'arreter)
     * @param suivants  points suivants du chemin (pour anticiper les virages), peut etre vide
     * @param allure    allure demandee par le cerveau
     */
    public Commande piloter(Vec pos, float lacet, Vec vise, List<Vec> suivants, Allure allure) {
        // ------------------------------------------------ endurance
        double cible = allure.vitesse;
        if (allure == Allure.COURSE || allure == Allure.CHARGE) {
            if (v > 0.8) {
                endurance -= 1.0 / (allure == Allure.CHARGE ? DUREE_CHARGE : DUREE_COURSE);
            }
        } else {
            endurance = Math.min(1.0, endurance + RECUP);
        }
        if (endurance <= 0) {
            endurance = 0;
            essouffle = true;
        } else if (essouffle && endurance >= 0.4) {
            essouffle = false;
        }
        if (essouffle && allure != Allure.NAGE && allure != Allure.NAGE_RAPIDE) {
            cible = Math.min(cible, Allure.MARCHE.vitesse);
        }

        // ------------------------------------------------ cap
        double erreur = 0;
        if (vise == null || cible <= 0) {
            cible = 0;
        } else {
            Vec d = vise.moins(pos);
            double dist = d.normeH();
            if (dist < 0.3) {
                cible = 0;
            } else {
                erreur = ecart(lacet, lacetVers(d.x(), d.z()));
                double e = Math.abs(erreur);
                // rayon qu'il faudrait pour passer par le point vise
                double rReq = e >= 90 ? dist / 2 : dist / (2 * Math.sin(Math.toRadians(Math.max(e, 1e-3))));
                if (allure == Allure.CHARGE) {
                    // charge = engagement : pas de freinage pour mieux viser. Seul le lacet
                    // est borne, c'est ce qui la rend esquivable d'un pas de cote.
                } else if (e > 100) {
                    cible = 0;                      // derriere lui : il s'arrete et pivote
                } else {
                    cible = vitessePourRayon(rReq, cible);
                }
                // virage a venir sur le chemin : arriver a une vitesse qui le permet
                Vec prec = vise;
                double cumul = dist;
                Vec dirPrec = d.unitaireH();
                for (Vec s : suivants) {
                    Vec seg = s.moins(prec);
                    if (seg.normeH() < 0.2) {
                        continue;
                    }
                    double angle = Vec.angleH(dirPrec, seg);
                    if (angle > 40 && allure != Allure.CHARGE) {
                        // en virant au noeud avec un rayon R, il deborde du chemin de R(1 - cos a) :
                        // on tolere 1.5 bloc de debordement (la largeur d'un couloir de chemin)
                        double a = Math.toRadians(Math.min(angle, 90));
                        double rVirage = DEBORD / (1 - Math.cos(a));
                        double vVirage = vitessePourRayon(rVirage, cible);
                        // vitesse permise a `cumul` blocs du virage : le temps de freiner jusqu'a vVirage
                        double permis = vVirage + Math.max(0, cumul - 1.5) * 0.25;
                        cible = Math.min(cible, permis);
                    }
                    cumul += seg.normeH();
                    dirPrec = seg.unitaireH();
                    prec = s;
                    if (cumul > 16) {
                        break;
                    }
                }
            }
        }

        // ------------------------------------------------ inertie
        double avant = v;
        if (cible > v) {
            v = Math.min(cible, v + ACCEL);
        } else {
            v = Math.max(cible, v - FREIN);
        }

        // ------------------------------------------------ lacet
        // correction PROPORTIONNELLE (30 % de l'ecart par tick), plafonnee par la vitesse de
        // lacet : sans amortissement, il corrige tout d'un coup, depasse et revient (cap qui
        // oscille de 4.5 degres/tick sur une simple diagonale)
        double max = lacetMax(v);
        double pas = Math.max(-max, Math.min(max, erreur * GAIN_CAP));
        float nouveau = (float) (lacet + pas);

        // ------------------------------------------------ geste (animation)
        Geste g = Geste.AUCUN;
        if (avant >= 0.9 && cible > 0) {
            lance = true;                          // en pleine course, pas en train de freiner
        }
        if (lance && cible == 0) {
            if (vise == null) {
                g = Geste.FREINAGE;                // arret demande en pleine course
            }
            lance = false;
        } else if (v < 0.08 && Math.abs(erreur) > 15) {
            g = Geste.PIVOT;
        } else if (v >= 0.8 && Math.abs(erreur) > 20) {
            g = erreur > 0 ? Geste.VIRAGE_DROITE : Geste.VIRAGE_GAUCHE;
        }
        return new Commande(nouveau, v, g);
    }
}
