package fr.riviere.spinosaure.cerveau;

import java.util.UUID;

/** Ce qui arrive au spinosaure entre deux reflexions. */
public sealed interface Evenement {

    /** Il a ete blesse par un joueur. {@code aDistance} : fleche, trident, projectile. */
    record Degats(UUID source, double montant, boolean aDistance) implements Evenement {
    }

    /** Un bruit a ete percu (bloc casse, porte, coffre, explosion...). */
    record Bruit(UUID source, Vec pos, double portee) implements Evenement {
    }
}
