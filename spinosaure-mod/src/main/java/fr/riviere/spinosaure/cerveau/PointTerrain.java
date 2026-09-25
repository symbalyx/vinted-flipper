package fr.riviere.spinosaure.cerveau;

/**
 * Un point echantillonne autour du spinosaure (fourni par l'entite, via les cartes de
 * hauteur : aucun balayage de blocs).
 *
 * @param eau        la surface y est de l'eau
 * @param profondeur hauteur d'eau (0 hors de l'eau) ; >= 4 : il peut s'y submerger
 * @param denivele   difference d'altitude avec lui (positif : plus haut)
 * @param danger     lave, feu, neige poudreuse... a eviter absolument
 * @param domaine    en jungle ou dans l'eau : son territoire (il ne va pas en plaine)
 * @param couvert    hors de la ligne de vue de sa cible actuelle (tronc, relief, feuillage)
 */
public record PointTerrain(Vec pos, boolean eau, double profondeur, double denivele, boolean danger,
                           boolean domaine, boolean couvert) {

    public PointTerrain(Vec pos, boolean eau, double profondeur, double denivele, boolean danger) {
        this(pos, eau, profondeur, denivele, danger, true, false);
    }

    public boolean profonde() {
        return eau && profondeur >= 4;
    }

    /** Berge : eau peu profonde, la ou il chasse et boit. */
    public boolean rive() {
        return eau && profondeur < 3;
    }
}
