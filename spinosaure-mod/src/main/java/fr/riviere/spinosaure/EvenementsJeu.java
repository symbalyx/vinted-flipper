package fr.riviere.spinosaure;

import fr.riviere.spinosaure.entite.SpinosaureEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.event.entity.EntityMountEvent;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/** Evenements du bus de jeu (pas du bus du mod). */
public final class EvenementsJeu {

    private EvenementsJeu() {
    }

    /**
     * Coups de feu TaCZ : chaque balle qui apparait (entite de l'espace de noms « tacz ») est
     * un tir. Les spinosaures a portee d'oreille (96 blocs) l'entendent. Aucune dependance a
     * TaCZ : sans le mod, cet evenement ne voit simplement jamais de balle.
     */
    @SubscribeEvent
    public static void tir(EntityJoinLevelEvent e) {
        if (e.getLevel().isClientSide() || !(e.getEntity() instanceof Projectile balle)) {
            return;
        }
        var cle = ForgeRegistries.ENTITY_TYPES.getKey(balle.getType());
        if (cle == null || !cle.getNamespace().equals("tacz") || !(balle.getOwner() instanceof Player tireur)) {
            return;
        }
        for (SpinosaureEntity spino : e.getLevel().getEntitiesOfClass(SpinosaureEntity.class,
                tireur.getBoundingBox().inflate(96))) {
            spino.entendreTir(tireur);
        }
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
