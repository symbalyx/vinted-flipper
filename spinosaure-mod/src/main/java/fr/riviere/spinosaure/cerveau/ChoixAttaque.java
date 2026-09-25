package fr.riviere.spinosaure.cerveau;

import java.util.List;
import java.util.Map;

/**
 * Quelle attaque, maintenant ? La reponse depend de la geometrie du combat, pas du hasard :
 * <ul>
 *   <li>deux joueurs dans le dos (ou un dans le dos et un groupe devant) : balayage de queue ;</li>
 *   <li>cible dans l'eau et a portee : saisie, pour l'entrainer ;</li>
 *   <li>bouclier leve face a lui : griffes, qui desactivent le bouclier ;</li>
 *   <li>cible a moyenne distance, ligne droite degagee : charge, ou bond si plus pres ;</li>
 *   <li>au contact : morsure, laterale si la cible est sur le flanc.</li>
 * </ul>
 * Renvoie null s'il faut d'abord se placer.
 */
public final class ChoixAttaque {

    private ChoixAttaque() {
    }

    static boolean dispo(Map<Attaque, Long> pret, Attaque a, long tick) {
        return pret.getOrDefault(a, Long.MIN_VALUE) <= tick;
    }

    /** Joueurs proches situes dans le dos du spinosaure. */
    public static int dansLeDos(Soi soi, List<Joueur> percus, Reglages r) {
        int n = 0;
        for (Joueur p : percus) {
            Vec v = p.pos().moins(soi.pos());
            if (v.normeH() <= r.porteeQueue && Vec.angleH(soi.regard(), v) >= r.angleArriere) {
                n++;
            }
        }
        return n;
    }

    public static Attaque choisir(Soi soi, Joueur cible, List<Joueur> percus, Map<Attaque, Long> pret,
                                  Reglages r) {
        long tick = soi.tick();
        int dos = dansLeDos(soi, percus, r);
        if ((dos >= 2 || (dos >= 1 && percus.size() >= 3)) && dispo(pret, Attaque.BALAYAGE_QUEUE, tick)) {
            return Attaque.BALAYAGE_QUEUE;
        }
        Vec v = cible.pos().moins(soi.pos());
        double d = v.normeH();
        double dy = Math.abs(v.y());
        double ang = Vec.angleH(soi.regard(), v);
        boolean aHauteur = dy < 4.0;

        if (cible.dansEau() && d <= r.porteeSaisie && aHauteur && ang < 50 && !cible.bouclierLeve()
                && dispo(pret, Attaque.SAISIE, tick)) {
            return Attaque.SAISIE;
        }
        if (cible.bouclierLeve()) {
            if (ang < 50 && d <= r.porteeGriffes && aHauteur && dispo(pret, Attaque.GRIFFES, tick)) {
                return Attaque.GRIFFES;
            }
            return null;                                   // il faut le contourner
        }
        boolean ligneDroite = cible.visible() && cible.atteignable() && !soi.dansEau() && dy < 2.5;
        if (ligneDroite && d >= r.chargeMin && d <= r.chargeMax && ang < 20 && dispo(pret, Attaque.CHARGE, tick)) {
            return Attaque.CHARGE;
        }
        if (ligneDroite && d >= r.bondMin && d <= r.bondMax && ang < 30 && dispo(pret, Attaque.BOND, tick)) {
            return Attaque.BOND;
        }
        if (d <= r.porteeMorsure && aHauteur) {
            if (ang >= 35 && ang <= 110 && dispo(pret, Attaque.MORSURE_LATERALE, tick)) {
                return Attaque.MORSURE_LATERALE;
            }
            if (ang < 35) {
                if (dispo(pret, Attaque.MORSURE, tick)) {
                    return Attaque.MORSURE;
                }
                if (d <= r.porteeGriffes && dispo(pret, Attaque.GRIFFES, tick)) {
                    return Attaque.GRIFFES;
                }
            }
        }
        return null;
    }
}
