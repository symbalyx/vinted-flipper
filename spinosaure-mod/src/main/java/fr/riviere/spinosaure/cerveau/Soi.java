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
 * @param dansDomaine    lui-meme en jungle ou dans l'eau
 * @param nuit           il fait nuit (il dort une partie de la nuit, quand rien ne le derange)
 */
public record Soi(Vec pos, Vec regard, double sante, double santeMax, boolean dansEau, boolean submerge,
                  Vec eauProfonde, boolean attaqueEnCours, long tick, List<PointTerrain> voisinage,
                  boolean dansDomaine, boolean nuit) {

    public Soi(Vec pos, Vec regard, double sante, double santeMax, boolean dansEau, boolean submerge,
               Vec eauProfonde, boolean attaqueEnCours, long tick, List<PointTerrain> voisinage,
               boolean dansDomaine) {
        this(pos, regard, sante, santeMax, dansEau, submerge, eauProfonde, attaqueEnCours, tick, voisinage, dansDomaine, false);
    }

    public Soi(Vec pos, Vec regard, double sante, double santeMax, boolean dansEau, boolean submerge,
               Vec eauProfonde, boolean attaqueEnCours, long tick, List<PointTerrain> voisinage) {
        this(pos, regard, sante, santeMax, dansEau, submerge, eauProfonde, attaqueEnCours, tick, voisinage, true, false);
    }

    public Soi(Vec pos, Vec regard, double sante, double santeMax, boolean dansEau, boolean submerge,
               Vec eauProfonde, boolean attaqueEnCours, long tick) {
        this(pos, regard, sante, santeMax, dansEau, submerge, eauProfonde, attaqueEnCours, tick, List.of(), true, false);
    }
}
