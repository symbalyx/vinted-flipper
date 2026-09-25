package fr.riviere.spinosaure.cerveau;

/**
 * Repertoire offensif. Chaque attaque est TELEGRAPHIEE : l'animation demarre et le coup
 * ne porte qu'a l'instant ou on le VOIT porter (machoire qui se referme, bras au plus
 * rapide). Un joueur attentif peut esquiver ; c'est ce qui rend le combat lisible a plusieurs.
 * duree = longueur de l'animation, recharge en ticks, degats = multiplicateur de l'attribut.
 */
public enum Attaque {
    // impacts mesures sur les animations (fermeture de machoire, bras au plus rapide...)
    MORSURE("morsure_rapide", 23, 24, 1.0, 13),
    MORSURE_LATERALE("morsure_laterale", 25, 30, 1.0, 10),
    /** Deux coups, un bras puis l'autre. Casse les boucliers leves, comme une hache. */
    GRIFFES("coup_griffes_double", 44, 70, 0.8, 10, 32),
    /** Pivot complet sur 360 degres : touche tout ce qui l'entoure, avec recul. */
    BALAYAGE_QUEUE("coup_de_queue_pivot", 36, 100, 0.7, 19),
    /** Course droite : l'impact se fait au contact, pas a un instant fixe. */
    CHARGE("charge", 40, 200, 1.3),
    /** Elan au tick 6, morsure a l'atterrissage (tick 22). */
    BOND("bond_joueur", 34, 160, 1.1, 22),
    /** Saisie : sur terre il secoue, dans l'eau il entraine au fond. Les allies peuvent liberer. */
    SAISIE("saisie_joueur", 36, 300, 0.5, 17),
    /** Rugissement : ralentit et affaiblit brievement le groupe qui arrive. */
    RUGISSEMENT("hurle_intimidation", 60, 600, 0.0, 10);

    public final String animation;
    public final int duree, recharge;
    public final double degats;
    /** Ticks, depuis le debut de l'animation, ou le coup porte. */
    public final int[] impacts;

    Attaque(String animation, int duree, int recharge, double degats, int... impacts) {
        this.animation = animation;
        this.duree = duree;
        this.recharge = recharge;
        this.degats = degats;
        this.impacts = impacts;
    }
}
