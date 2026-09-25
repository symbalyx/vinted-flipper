package fr.riviere.spinosaure.cerveau;

import java.util.UUID;

/**
 * Ce que le spinosaure peut savoir d'un joueur a un instant donne. Construit par
 * l'entite a partir du monde ; le cerveau ne lit jamais le monde lui-meme.
 *
 * @param regard      direction unitaire du regard du joueur
 * @param sante       fraction de vie restante, 0..1
 * @param armure      points d'armure, 0..20
 * @param visible     ligne de vue degagee entre le spinosaure et le joueur
 * @param atteignable un chemin terrestre ou aquatique existe jusqu'a lui
 * @param vitesse     deplacement mesure, en blocs par tick (pour l'intercepter)
 */
public record Joueur(UUID id, Vec pos, Vec regard, double sante, double armure, Arme arme,
                     boolean bouclierLeve, boolean accroupi, boolean sprinte, boolean dansEau,
                     boolean visible, boolean atteignable, Vec vitesse) {

    public enum Arme { AUCUNE, MELEE, DISTANCE, TRIDENT }

    public boolean armeADistance() {
        return arme == Arme.DISTANCE || arme == Arme.TRIDENT;
    }
}
