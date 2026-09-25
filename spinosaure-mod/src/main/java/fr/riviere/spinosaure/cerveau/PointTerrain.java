package fr.riviere.spinosaure.cerveau;

/**
 * Un point echantillonne autour du spinosaure (fourni par l'entite, via les cartes de
 * hauteur : aucun balayage de blocs).
 *
 * @param eau        la surface y est de l'eau
 * @param profondeur hauteur d'eau (0 hors de l'eau) ; >= 4 : il peut s'y submerger
 * @param denivele   difference d'altitude avec lui (positif : plus haut)
 * @param danger     lave, feu, neige poudreuse... a eviter absolument
 */
public record PointTerrain(Vec pos, boolean eau, double profondeur, double denivele, boolean danger) {

    public boolean profonde() {
        return eau && profondeur >= 4;
    }

    /** Berge : eau peu profonde, la ou il chasse et boit. */
    public boolean rive() {
        return eau && profondeur < 3;
    }
}
