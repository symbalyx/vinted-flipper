package fr.riviere.spinosaure.entite;

import fr.riviere.spinosaure.cerveau.Joueur;
import fr.riviere.spinosaure.cerveau.Reglages;
import fr.riviere.spinosaure.cerveau.Soi;
import fr.riviere.spinosaure.cerveau.Vec;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ProjectileWeaponItem;
import net.minecraft.world.item.TieredItem;
import net.minecraft.world.item.TridentItem;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Traduit le monde Minecraft en instantane pour le cerveau. Les calculs couteux
 * (chemins, recherche d'eau) sont mis en cache et etales dans le temps.
 */
final class Instantane {

    private final SpinosaureEntity spino;
    private final Reglages r;

    private final Map<UUID, Boolean> atteignable = new HashMap<>();
    private final Map<UUID, Long> atteignableCalcule = new HashMap<>();
    private Vec eauProfonde;
    private long eauCalculee = Long.MIN_VALUE / 2;

    Instantane(SpinosaureEntity spino, Reglages r) {
        this.spino = spino;
        this.r = r;
    }

    static Vec vec(Vec3 v) {
        return new Vec(v.x, v.y, v.z);
    }

    static Vec3 vec3(Vec v) {
        return new Vec3(v.x(), v.y(), v.z());
    }

    /** Direction du corps (yBodyRot) en vecteur horizontal. */
    static Vec avant(float yaw) {
        float rad = yaw * Mth.DEG_TO_RAD;
        return new Vec(-Mth.sin(rad), 0, Mth.cos(rad));
    }

    Soi soi(boolean attaqueEnCours) {
        long tick = spino.level().getGameTime();
        if (tick - eauCalculee >= 40) {
            eauProfonde = chercherEau();
            eauCalculee = tick;
        }
        return new Soi(vec(spino.position()), avant(spino.yBodyRot), spino.getHealth() / spino.getMaxHealth(),
                spino.getMaxHealth(), spino.isInWater(), spino.estSubmerge(), eauProfonde, attaqueEnCours, tick);
    }

    List<Joueur> joueurs() {
        Level niveau = spino.level();
        long tick = niveau.getGameTime();
        List<Joueur> out = new ArrayList<>();
        List<Player> ps = niveau.getEntitiesOfClass(Player.class, spino.getBoundingBox().inflate(r.porteeVue),
                p -> p.isAlive() && !p.isSpectator() && !p.isCreative());
        for (Player p : ps) {
            UUID id = p.getUUID();
            // un chemin par joueur toutes les 20 ticks, decale selon le joueur
            Long quand = atteignableCalcule.get(id);
            if (quand == null || tick - quand >= 20 + (id.hashCode() & 7)) {
                atteignable.put(id, calculerAtteignable(p));
                atteignableCalcule.put(id, tick);
            }
            boolean visible = !p.isInvisible() && spino.getSensing().hasLineOfSight(p);
            out.add(new Joueur(id, vec(p.position()), vec(p.getViewVector(1.0F)),
                    p.getHealth() / p.getMaxHealth(), p.getArmorValue(), arme(p.getMainHandItem().getItem()),
                    p.isBlocking(), p.isCrouching(), p.isSprinting(), p.isInWater(),
                    visible, atteignable.getOrDefault(id, true)));
        }
        atteignable.keySet().removeIf(id -> ps.stream().noneMatch(p -> p.getUUID().equals(id)));
        atteignableCalcule.keySet().retainAll(atteignable.keySet());
        return out;
    }

    private boolean calculerAtteignable(Player p) {
        if (p.isInWater() && spino.isInWater()) {
            return true;                                // en nage, rien ne l'arrete
        }
        Path chemin = spino.getNavigation().createPath(p, 2);
        if (chemin == null) {
            return false;
        }
        if (chemin.canReach()) {
            return true;
        }
        // chemin partiel : atteignable si son bout est a portee de morsure (joueur sur une butte)
        BlockPos fin = chemin.getTarget();
        return fin != null && Vec3.atCenterOf(fin).distanceTo(p.position()) <= r.porteeMorsure - 1;
    }

    static Joueur.Arme arme(Item item) {
        if (item instanceof TridentItem) {
            return Joueur.Arme.TRIDENT;
        }
        if (item instanceof ProjectileWeaponItem) {
            return Joueur.Arme.DISTANCE;               // arc, arbalete
        }
        if (item instanceof TieredItem) {
            return Joueur.Arme.MELEE;                  // epees, haches, outils
        }
        return Joueur.Arme.AUCUNE;
    }

    /**
     * Eau d'au moins 4 blocs de profondeur la plus proche, dans un rayon de 28 blocs.
     * Echantillonnage en anneaux via les cartes de hauteur : pas de balayage de blocs.
     */
    private Vec chercherEau() {
        Level niveau = spino.level();
        if (spino.estSubmerge()) {
            return vec(spino.position());
        }
        int x0 = spino.getBlockX(), z0 = spino.getBlockZ();
        for (int rayon = 4; rayon <= 28; rayon += 4) {
            int n = Math.max(8, rayon * 2);
            for (int i = 0; i < n; i++) {
                double a = 2 * Math.PI * i / n;
                int x = x0 + (int) Math.round(Math.cos(a) * rayon), z = z0 + (int) Math.round(Math.sin(a) * rayon);
                BlockPos test = new BlockPos(x, spino.getBlockY(), z);
                if (!niveau.hasChunkAt(test)) {
                    continue;
                }
                int surface = niveau.getHeight(Heightmap.Types.WORLD_SURFACE, x, z);
                int fond = niveau.getHeight(Heightmap.Types.OCEAN_FLOOR, x, z);
                if (surface - fond >= 4 && niveau.getFluidState(new BlockPos(x, surface - 1, z)).is(FluidTags.WATER)) {
                    return new Vec(x + 0.5, fond + 1, z + 0.5);
                }
            }
        }
        return null;
    }
}
