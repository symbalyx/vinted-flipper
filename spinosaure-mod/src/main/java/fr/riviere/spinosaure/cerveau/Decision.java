package fr.riviere.spinosaure.cerveau;

import java.util.UUID;

/**
 * Ce que le cerveau demande au corps pour les prochains ticks.
 *
 * @param destination ou aller (null : rester sur place)
 * @param regard      point a fixer (null : regarder ou l'on va)
 * @param attaque     attaque a declencher MAINTENANT (null : aucune)
 * @param lacher      liberer le joueur tenu
 * @param animation   animation d'ambiance ponctuelle (renifler, regard fixe...), ou null
 * @param raison      explication lisible, pour le debogage (/data, logs, overlay)
 */
public record Decision(Tactique tactique, UUID cible, Vec destination, Allure allure, Vec regard,
                       Attaque attaque, boolean lacher, String animation, String raison) {

    public enum Tactique {
        ERRANCE, ENQUETE, TRAQUE, FIGE, AFFUT_EAU, INTIMIDATION, ENGAGEMENT, CONTOURNEMENT,
        MAINTIEN, REPLI, REGENERATION, ESQUIVE_TIR, ACCULE,
        /** horreur : observe de loin */ OBSERVATION,
        /** horreur : file sa proie par derriere */ FILATURE,
        /** horreur : s'efface (vu, blesse de loin, ou apres une frappe) */ DISPARITION
    }

    /**
     * Allure demandee ; l'entite en deduit la vitesse ET l'animation de deplacement.
     * vitesse = multiplicateur de l'attribut MOVEMENT_SPEED (0.34). Au sol un mob avance
     * d'environ 44 x (attribut x multiplicateur)^2 blocs/s : feutree 1.1, marche 2.1,
     * course 5.1, charge 7.9 blocs/s. (La feutree etait a 0.3 bloc/s : mesure en jeu, il
     * mettait 50 s a faire 10 blocs et le deblocage le croyait coince.)
     */
    public enum Allure {
        ARRET(0.0), FEUTREE(0.47), MARCHE(0.65), COURSE(1.0), CHARGE(1.25), NAGE(0.8), NAGE_RAPIDE(1.2);

        public final double vitesse;

        Allure(double vitesse) {
            this.vitesse = vitesse;
        }
    }
}
