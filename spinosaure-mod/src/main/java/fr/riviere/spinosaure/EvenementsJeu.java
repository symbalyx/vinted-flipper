package fr.riviere.spinosaure;

import fr.riviere.spinosaure.entite.SpinosaureEntity;
import net.minecraftforge.event.entity.EntityMountEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/** Evenements du bus de jeu (pas du bus du mod). */
public final class EvenementsJeu {

    private EvenementsJeu() {
    }

    /**
     * Un joueur saisi ne peut pas se degager en s'accroupissant : seuls ses allies (degats),
     * sa propre resistance ou la fin du maintien le liberent. Le spinosaure, lui, peut lacher.
     */
    @SubscribeEvent
    public static void descente(EntityMountEvent e) {
        if (e.isDismounting() && e.getEntityBeingMounted() instanceof SpinosaureEntity spino
                && !e.getLevel().isClientSide() && spino.retient(e.getEntityMounting())) {
            e.setCanceled(true);
        }
    }
}
