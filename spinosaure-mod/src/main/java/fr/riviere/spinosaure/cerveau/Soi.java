package fr.riviere.spinosaure.cerveau;

import java.util.List;

/**
 * Etat du spinosaure vu par son cerveau.
 *
 * @param regard         direction du corps (unitaire, horizontale)
 * @param sante          fraction de vie restante, 0..1
 * @param santeMax       points de vie maximum (pour convertir les degats en fraction)
 * @param submerge       entierement sous l'eau (peut s'y cacher et s'y soigner)
 * @param eauProfonde    point d'eau profonde connu le plus proche, ou null
 * @param attaqueEnCours une attaque est en train d'etre jouee : ne pas en lancer d'autre
 * @param tick           horloge du monde, en ticks (20 par seconde)
 * @param voisinage      points de terrain echantillonnes autour de lui (peut etre vide)
 */
public record Soi(Vec pos, Vec regard, double sante, double santeMax, boolean dansEau, boolean submerge,
                  Vec eauProfonde, boolean attaqueEnCours, long tick, List<PointTerrain> voisinage) {

    public Soi(Vec pos, Vec regard, double sante, double santeMax, boolean dansEau, boolean submerge,
               Vec eauProfonde, boolean attaqueEnCours, long tick) {
        this(pos, regard, sante, santeMax, dansEau, submerge, eauProfonde, attaqueEnCours, tick, List.of());
    }
}
