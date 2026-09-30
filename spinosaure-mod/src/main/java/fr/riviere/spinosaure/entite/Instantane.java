package fr.riviere.spinosaure.entite;

import fr.riviere.spinosaure.cerveau.Joueur;
import fr.riviere.spinosaure.cerveau.PointTerrain;
import fr.riviere.spinosaure.cerveau.Reglages;
import fr.riviere.spinosaure.cerveau.Soi;
import fr.riviere.spinosaure.cerveau.Vec;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.BiomeTags;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.HitResult;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ProjectileWeaponItem;
import net.minecraft.world.item.TieredItem;
import net.minecraft.world.item.TridentItem;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.pathfinder.BlockPathTypes;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.level.pathfinder.WalkNodeEvaluator;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
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
    private LivingEntity cibleTerrain;
    /** Portee a laquelle le « directeur » connait les joueurs (au-dela de ses sens). */
    static final double PORTEE_DIRECTEUR = 160;
    private List<PointTerrain> voisinage = List.of();
    private long terrainCalcule = Long.MIN_VALUE / 2;
    /** Derniere position connue de chaque joueur, pour mesurer sa vitesse. */
    private final Map<UUID, Vec> dernierePos = new HashMap<>();
    private final Map<UUID, Long> derniereFois = new HashMap<>();

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

    /** En jungle ou dans l'eau : son domaine. Il ne fonctionne pas ailleurs. */
    static boolean domaine(Level niveau, BlockPos pos) {
        return niveau.getFluidState(pos).is(FluidTags.WATER) || niveau.getBiome(pos).is(BiomeTags.IS_JUNGLE);
    }

    Soi soi(boolean attaqueEnCours, LivingEntity cible) {
        long tick = spino.level().getGameTime();
        if (tick - terrainCalcule >= 40 || (cible != null && cible != cibleTerrain)) {
            cibleTerrain = cible;
            voisinage = echantillonner(cible);
            eauProfonde = plusProcheEauProfonde();
            terrainCalcule = tick;
        }
        return new Soi(vec(spino.position()), avant(spino.yBodyRot), spino.getHealth() / spino.getMaxHealth(),
                spino.getMaxHealth(), spino.isInWater(), spino.estSubmerge(), eauProfonde, attaqueEnCours, tick,
                voisinage, spino.isInWater() || domaine(spino.level(), spino.blockPosition()), spino.level().isNight());
    }

    /**
     * Ses adversaires : les joueurs (jusqu'a 160 blocs, pour le « directeur ») et les creatures
     * qu'il doit combattre (voir {@link SpinosaureEntity#ennemi}).
     */
    List<Joueur> joueurs() {
        Level niveau = spino.level();
        long tick = niveau.getGameTime();
        List<Joueur> out = new ArrayList<>();
        Set<UUID> vus = new HashSet<>();
        // jusqu'a 160 blocs : au-dela de ses sens (48), seul le « directeur » s'en sert
        List<Player> ps = niveau.getEntitiesOfClass(Player.class, spino.getBoundingBox().inflate(PORTEE_DIRECTEUR),
                p -> p.isAlive() && !p.isSpectator());      // creatif inclus : observe, jamais attaque
        for (Player p : ps) {
            UUID id = p.getUUID();
            boolean proche = p.distanceTo(spino) <= r.porteeVue;
            // un chemin par joueur proche toutes les 20 ticks, decale selon le joueur
            Long quand = atteignableCalcule.get(id);
            if (proche && (quand == null || tick - quand >= 20 + (id.hashCode() & 7))) {
                atteignable.put(id, calculerAtteignable(p));
                atteignableCalcule.put(id, tick);
            }
            boolean visible = proche && !p.isInvisible() && spino.getSensing().hasLineOfSight(p);
            Vec pos = vec(p.position());
            Vec vitesse = vitesse(id, pos, tick);
            vus.add(id);
            ItemStack main = p.getMainHandItem();
            out.add(new Joueur(id, pos, vec(p.getViewVector(1.0F)),
                    p.getHealth() / p.getMaxHealth(), p.getArmorValue(), arme(main),
                    p.isBlocking(), p.isCrouching(), p.isSprinting(), p.isInWater(),
                    visible, atteignable.getOrDefault(id, true), vitesse, p.isCreative(),
                    chargeurVide(main), p.isInWater() || domaine(niveau, p.blockPosition())));
        }
        // les creatures a combattre, dans sa portee de vue
        for (LivingEntity e : niveau.getEntitiesOfClass(LivingEntity.class, spino.getBoundingBox().inflate(r.porteeVue),
                spino::ennemi)) {
            UUID id = e.getUUID();
            Long quand = atteignableCalcule.get(id);
            if (quand == null || tick - quand >= 20 + (id.hashCode() & 7)) {
                atteignable.put(id, calculerAtteignable(e));
                atteignableCalcule.put(id, tick);
            }
            Vec pos = vec(e.position());
            vus.add(id);
            out.add(new Joueur(id, pos, vec(e.getViewVector(1.0F)), e.getHealth() / Math.max(1F, e.getMaxHealth()),
                    e.getArmorValue(), Joueur.Arme.MELEE, false, false, false, e.isInWater(),
                    !e.isInvisible() && spino.getSensing().hasLineOfSight(e), atteignable.getOrDefault(id, true),
                    vitesse(id, pos, tick), false, false, true, true));
        }
        atteignable.keySet().retainAll(vus);
        atteignableCalcule.keySet().retainAll(vus);
        dernierePos.keySet().retainAll(vus);
        derniereFois.keySet().retainAll(vus);
        return out;
    }

    /**
     * Vitesse mesuree sur le deplacement reel : cote serveur, getDeltaMovement() d'un joueur est
     * peu fiable (c'est le client qui le deplace).
     */
    private Vec vitesse(UUID id, Vec pos, long tick) {
        Vec v = Vec.ZERO;
        Vec avantPos = dernierePos.get(id);
        Long avantTick = derniereFois.get(id);
        if (avantPos != null && avantTick != null && tick > avantTick && tick - avantTick <= 10) {
            v = pos.moins(avantPos).fois(1.0 / (tick - avantTick));
        }
        dernierePos.put(id, pos);
        derniereFois.put(id, tick);
        return v;
    }

    private boolean calculerAtteignable(Entity p) {
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

    /**
     * Armes du mod TaCZ reconnues sans dependance de compilation : objet de l'espace de noms
     * « tacz » dont le nom contient « gun ». Toute autre arme a feu d'un autre mod peut etre
     * ajoutee ici de la meme facon.
     */
    static boolean armeAFeu(Item item) {
        var cle = ForgeRegistries.ITEMS.getKey(item);
        return cle != null && cle.getNamespace().equals("tacz") && cle.getPath().contains("gun");
    }

    /** TaCZ range les munitions de l'arme dans ses donnees : « GunCurrentAmmoCount ». */
    static boolean chargeurVide(ItemStack stack) {
        if (!armeAFeu(stack.getItem())) {
            return false;
        }
        CompoundTag tag = stack.getTag();
        return tag != null && tag.contains("GunCurrentAmmoCount") && tag.getInt("GunCurrentAmmoCount") <= 0
                && !tag.getBoolean("HasBulletInBarrel");
    }

    static Joueur.Arme arme(ItemStack stack) {
        return armeAFeu(stack.getItem()) ? Joueur.Arme.FEU : arme(stack.getItem());
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
     * Terrain autour de lui : 4 anneaux (8, 14, 20, 26 blocs) x 12 directions, lus dans les
     * cartes de hauteur (aucun balayage de blocs), recalcule toutes les 2 s. Pour chaque
     * point : eau et profondeur, denivele, et danger selon le classement de pathfinding
     * de Minecraft lui-meme (lave, feu, cactus, neige poudreuse...).
     */
    private List<PointTerrain> echantillonner(LivingEntity cible) {
        Level niveau = spino.level();
        List<PointTerrain> out = new ArrayList<>();
        int x0 = spino.getBlockX(), z0 = spino.getBlockZ();
        BlockPos.MutableBlockPos curseur = new BlockPos.MutableBlockPos();
        for (int rayon = 8; rayon <= 26; rayon += 6) {
            for (int i = 0; i < 12; i++) {
                double a = 2 * Math.PI * i / 12 + rayon * 0.13;        // anneaux decales
                int x = x0 + (int) Math.round(Math.cos(a) * rayon), z = z0 + (int) Math.round(Math.sin(a) * rayon);
                if (!niveau.hasChunkAt(new BlockPos(x, spino.getBlockY(), z))) {
                    continue;
                }
                // sous la jungle : WORLD_SURFACE et OCEAN_FLOOR comptent les feuilles. Sous une
                // canopee continue, chaque point tombait sur la cime des arbres, 15 a 20 blocs
                // au-dessus de lui : refuse (denivele) ou vise sans chemin. Toute carte de hauteur
                // tombe aussi sur un plafond (les barrieres qui coiffent l'arene des essais en jeu,
                // un toit, un surplomb) : on lit le sol localement, depuis sa hauteur.
                int surface = sousLeSol(niveau, x, z, spino.getBlockY());
                boolean eau = niveau.getFluidState(new BlockPos(x, surface - 1, z)).is(FluidTags.WATER);
                boolean lave = niveau.getFluidState(new BlockPos(x, surface - 1, z)).is(FluidTags.LAVA);
                int fond = surface;
                if (eau) {
                    fond = surface - 1;
                    for (int k = 0; k < 96 && niveau.getFluidState(new BlockPos(x, fond - 1, z)).is(FluidTags.WATER); k++) {
                        fond--;
                    }
                }
                double profondeur = eau ? surface - fond : 0;
                curseur.set(x, eau ? fond : surface, z);
                BlockPathTypes type = WalkNodeEvaluator.getBlockPathTypeStatic(niveau, curseur);
                boolean danger = lave || type == BlockPathTypes.LAVA || type == BlockPathTypes.DAMAGE_FIRE
                        || type == BlockPathTypes.DANGER_FIRE || type == BlockPathTypes.DAMAGE_OTHER
                        || type == BlockPathTypes.POWDER_SNOW;
                int sol = eau ? fond : surface;
                double y = profondeur >= 4 ? surface - 2.5 : sol;        // eau profonde : sous la surface
                BlockPos ici = new BlockPos(x, Math.max(sol, fond), z);
                boolean domaine = eau || niveau.getBiome(ici).is(BiomeTags.IS_JUNGLE);
                // a couvert : la ligne de vue depuis les yeux de sa cible jusqu'au point (a hauteur
                // de son dos) est coupee par un tronc, du feuillage ou le relief
                boolean couvert = false;
                if (cible != null) {
                    Vec3 dos = new Vec3(x + 0.5, sol + 3.0, z + 0.5);
                    HitResult h = niveau.clip(new ClipContext(cible.getEyePosition(), dos,
                            ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, cible));
                    couvert = h.getType() != HitResult.Type.MISS
                            && h.getLocation().distanceToSqr(dos) > 4.0;
                }
                out.add(new PointTerrain(new Vec(x + 0.5, y, z + 0.5), eau, profondeur, sol - spino.getY(), danger,
                        domaine, couvert));
            }
        }
        return out;
    }

    /**
     * Premier y libre au-dessus du sol (ou de l'eau) en (x, z), lu en descendant depuis 10 blocs
     * au-dessus de lui : feuillages et troncs ignores. Sol plus haut que ca : on rend le haut
     * de la lecture (denivele trop fort, point refuse) ; rien sur 40 blocs : un gouffre.
     */
    static int sousLeSol(Level niveau, int x, int z, int yRef) {
        BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos(x, yRef + 10, z);
        for (int k = 0; k < 40; k++) {
            net.minecraft.world.level.block.state.BlockState s = niveau.getBlockState(p.below());
            if (!s.getFluidState().isEmpty()
                    || (s.blocksMotion() && !s.is(BlockTags.LEAVES) && !s.is(BlockTags.LOGS))) {
                return p.getY();
            }
            p.move(0, -1, 0);
        }
        return yRef - 40;
    }

    List<PointTerrain> voisinage() {
        return voisinage;
    }

    private Vec plusProcheEauProfonde() {
        if (spino.estSubmerge()) {
            return vec(spino.position());
        }
        Vec moi = vec(spino.position()), best = null;
        for (PointTerrain p : voisinage) {
            if (p.profonde() && !p.danger() && (best == null || p.pos().distanceH(moi) < best.distanceH(moi))) {
                best = p.pos();
            }
        }
        return best;
    }
}
