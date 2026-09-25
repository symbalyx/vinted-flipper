package fr.riviere.spinosaure.cerveau;

import java.util.ArrayDeque;
import java.util.Deque;

/**
 * Detection de blocage physique et remedes gradues. Un gros animal se coince contre un
 * arbre, une marche de 2 blocs, un angle de maison : au lieu de pousser indefiniment,
 * il essaie dans l'ordre
 * <ol>
 *   <li>SAUTER (marche un peu trop haute) ;</li>
 *   <li>RECULER de quelques blocs pour se degager ;</li>
 *   <li>CONTOURNER par le cote ;</li>
 *   <li>ABANDONNER cette destination : le cerveau en choisit une autre.</li>
 * </ol>
 * Le progres se mesure en distance GAGNEE VERS LA DESTINATION, pas en distance parcourue :
 * reculer pour se degager ne compte pas comme un progres, sinon l'echelle repartirait
 * de zero a chaque recul et il ne contournerait jamais.
 */
public final class Deblocage {

    public enum Action { RIEN, SAUTER, RECULER, CONTOURNER, ABANDONNER }

    public static final int FENETRE = 30, PALIER = 20, PALIER_CONTOURNEMENT = 50, CALME = 60;
    public static final double PROGRES = 1.0;

    private final Deque<Double> distances = new ArrayDeque<>();
    private int niveau;
    private int depuisPalier;
    private int calme;

    public int niveau() {
        return niveau;
    }

    /**
     * @param distanceBut distance horizontale restante jusqu'a la destination
     * @param veutAvancer le pilote commande une vitesse non nulle
     * @return l'action a entreprendre CE tick (RIEN la plupart du temps)
     */
    public Action evaluer(double distanceBut, boolean veutAvancer) {
        distances.addLast(distanceBut);
        while (distances.size() > FENETRE) {
            distances.removeFirst();
        }
        if (!veutAvancer) {
            reinitialiser();
            return Action.RIEN;
        }
        if (niveau > 0) {
            depuisPalier++;
        }
        if (distances.size() < FENETRE) {
            return Action.RIEN;
        }
        if (distances.peekFirst() - distanceBut >= PROGRES) {
            // il se rapproche : l'echelle ne retombe qu'apres un moment de progres continu
            if (++calme >= CALME) {
                niveau = 0;
                depuisPalier = 0;
            }
            return Action.RIEN;
        }
        calme = 0;
        int attente = niveau == 3 ? PALIER_CONTOURNEMENT : PALIER;
        if (niveau > 0 && depuisPalier < attente) {
            return Action.RIEN;
        }
        depuisPalier = 0;
        niveau++;
        Action a = switch (niveau) {
            case 1 -> Action.SAUTER;
            case 2 -> Action.RECULER;
            case 3 -> Action.CONTOURNER;
            default -> Action.ABANDONNER;
        };
        if (a == Action.ABANDONNER) {
            reinitialiser();
        }
        return a;
    }

    public void reinitialiser() {
        niveau = 0;
        depuisPalier = 0;
        calme = 0;
        distances.clear();
    }
}
