package fr.riviere.spinosaure.cerveau;

import java.util.UUID;

/**
 * Ce que le spinosaure peut savoir d'un adversaire (un joueur, ou une creature qui l'attaque)
 * a un instant donne. Construit par
 * l'entite a partir du monde ; le cerveau ne lit jamais le monde lui-meme.
 *
 * @param regard      direction unitaire du regard du joueur
 * @param sante       fraction de vie restante, 0..1
 * @param armure      points d'armure, 0..20
 * @param visible     ligne de vue degagee entre le spinosaure et le joueur
 * @param atteignable un chemin terrestre ou aquatique existe jusqu'a lui
 * @param vitesse     deplacement mesure, en blocs par tick (pour l'intercepter)
 * @param inoffensif  joueur en creatif : il l'observe et le traque, mais ne l'attaque pas
 * @param chargeurVide arme a feu en main, chargeur vide (il recharge) : une ouverture
 * @param dansDomaine le joueur est en jungle ou dans l'eau (hors de la, il ne le suit pas)
 * @param creature    pas un joueur : une creature (d'un autre mod, un loup, un golem...) qui
 *                    l'attaque, le prend pour cible ou qu'on lui a designee. Pas de jeu
 *                    d'horreur avec elle : il se bat, jusqu'au bout.
 */
public record Joueur(UUID id, Vec pos, Vec regard, double sante, double armure, Arme arme,
                     boolean bouclierLeve, boolean accroupi, boolean sprinte, boolean dansEau,
                     boolean visible, boolean atteignable, Vec vitesse, boolean inoffensif,
                     boolean chargeurVide, boolean dansDomaine, boolean creature) {

    /** FEU : arme a feu (mod TaCZ, ou tout objet reconnu comme tel par l'entite). */
    public enum Arme { AUCUNE, MELEE, DISTANCE, TRIDENT, FEU }

    public Joueur(UUID id, Vec pos, Vec regard, double sante, double armure, Arme arme,
                  boolean bouclierLeve, boolean accroupi, boolean sprinte, boolean dansEau,
                  boolean visible, boolean atteignable, Vec vitesse, boolean inoffensif) {
        this(id, pos, regard, sante, armure, arme, bouclierLeve, accroupi, sprinte, dansEau, visible, atteignable,
                vitesse, inoffensif, false, true, false);
    }

    public Joueur(UUID id, Vec pos, Vec regard, double sante, double armure, Arme arme,
                  boolean bouclierLeve, boolean accroupi, boolean sprinte, boolean dansEau,
                  boolean visible, boolean atteignable, Vec vitesse, boolean inoffensif,
                  boolean chargeurVide, boolean dansDomaine) {
        this(id, pos, regard, sante, armure, arme, bouclierLeve, accroupi, sprinte, dansEau, visible, atteignable,
                vitesse, inoffensif, chargeurVide, dansDomaine, false);
    }

    public boolean armeADistance() {
        return arme == Arme.DISTANCE || arme == Arme.TRIDENT || arme == Arme.FEU;
    }

    public boolean armeFeu() {
        return arme == Arme.FEU;
    }
}
