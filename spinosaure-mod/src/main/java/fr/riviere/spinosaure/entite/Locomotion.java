package fr.riviere.spinosaure.entite;

import fr.riviere.spinosaure.SpinosaureMod;
import fr.riviere.spinosaure.cerveau.Decision.Allure;
import fr.riviere.spinosaure.cerveau.Deblocage;
import fr.riviere.spinosaure.cerveau.Pilote;
import fr.riviere.spinosaure.cerveau.Vec;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.entity.EntityDimensions;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.pathfinder.Node;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.ForgeEventFactory;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Execution des deplacements : le cerveau dit OU et A QUELLE ALLURE, la locomotion
 * s'occupe du COMMENT (chemin, pilote physique, deblocage, charge engagee, transitions).
 */
final class Locomotion {

    /** Museau a 134 unites devant le centre du modele, a l'echelle de rendu. */
    static final double MUSEAU = 134.0 / 16.0 * SpinosaureMod.ECHELLE;
    static final double DEMI_LARGEUR = 1.7;

    final Pilote pilote = new Pilote();
    final Deblocage deblocage = new Deblocage();
    private final SpinosaureEntity spino;

    Allure allure = Allure.ARRET;
    private Vec3 destination;
    /** Le but tel que le cerveau l'a donne, avant ajustement a la place libre. */
    private Vec3 butDemande;
    private int prochainChemin;

    private Vec3 detour;
    private int detourTicks;
    private int cote = 1;
    private int reculTicks;

    private Vec3 chargeBut;
    private final Set<UUID> pietines = new HashSet<>();

    private boolean etaitDansEau;

    Locomotion(SpinosaureEntity spino) {
        this.spino = spino;
    }

    // ------------------------------------------------------------------ ordres

    void aller(Vec3 but, Allure a) {
        allure = a;
        if (detour != null) {
            return;                                  // on finit d'abord de contourner
        }
        if (destination == null || butDemande == null || butDemande.distanceToSqr(but) > 2.25
                || spino.getNavigation().isDone() || --prochainChemin <= 0) {
            butDemande = but;
            destination = placeLibre(but);
            prochainChemin = 20;
            spino.getNavigation().moveTo(destination.x, destination.y, destination.z, a.vitesse);
        }
    }

    /**
     * Le cerveau vise un point (10 blocs derriere toi...) sans savoir si son corps de 3,4 blocs
     * y tient : colle a un tronc, le chemin s'arrete court, il bute et recule en boucle
     * (mesure en jeu). On vise donc la place libre la plus proche, cote spinosaure.
     */
    private Vec3 placeLibre(Vec3 but) {
        EntityDimensions dims = spino.getDimensions(spino.getPose());
        if (tient(dims, but)) {
            return but;
        }
        for (int r = 1; r <= 6; r++) {
            Vec3 meilleur = null;
            double dm = Double.MAX_VALUE;
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    if (Math.max(Math.abs(dx), Math.abs(dz)) != r) {
                        continue;
                    }
                    for (int dy : new int[]{0, 1, -1}) {
                        Vec3 c = but.add(dx, dy, dz);
                        if (tient(dims, c)) {
                            double dd = c.distanceToSqr(spino.position());
                            if (dd < dm) {
                                dm = dd;
                                meilleur = c;
                            }
                            break;
                        }
                    }
                }
            }
            if (meilleur != null) {
                return meilleur;
            }
        }
        return but;
    }

    /** Son corps y tient, pose sur un sol (ou dans l'eau). */
    private boolean tient(EntityDimensions dims, Vec3 p) {
        AABB boite = dims.makeBoundingBox(p);
        if (!spino.level().noCollision(spino, boite)) {
            return false;
        }
        return !spino.level().noCollision(spino, boite.move(0, -1, 0))
                || spino.level().getFluidState(BlockPos.containing(p)).is(FluidTags.WATER);
    }

    void arreter() {
        allure = Allure.ARRET;
        destination = null;
        butDemande = null;
        detour = null;
        spino.getNavigation().stop();
    }

    /**
     * Charge ENGAGEE : vers le point ou la cible sera (interception), prolonge de 6 blocs.
     * Plus aucune correction de trajectoire ensuite : un pas de cote l'evite, et lance il
     * ne fait pas demi-tour (le pilote borne son lacet).
     */
    void lancerCharge(Vec3 visee) {
        Vec3 dir = visee.subtract(spino.position()).multiply(1, 0, 1).normalize();
        chargeBut = visee.add(dir.scale(6));
        pietines.clear();
        allure = Allure.CHARGE;
        destination = chargeBut;
        spino.getNavigation().moveTo(chargeBut.x, chargeBut.y, chargeBut.z, Allure.CHARGE.vitesse);
    }

    /** @return la cible principale touchee ce tick, ou null. La charge pietine au passage. */
    LivingEntity tickCharge(LivingEntity visee) {
        allure = Allure.CHARGE;
        if (chargeBut == null) {
            return null;
        }
        if (spino.getNavigation().isDone()) {
            spino.getNavigation().moveTo(chargeBut.x, chargeBut.y, chargeBut.z, Allure.CHARGE.vitesse);
        }
        Vec3 avant = Instantane.vec3(Instantane.avant(spino.yBodyRot));
        Vec3 centre = spino.position();
        Vec3 museau = centre.add(avant.scale(MUSEAU));
        LivingEntity touchee = null;
        for (LivingEntity e : spino.level().getEntitiesOfClass(LivingEntity.class,
                spino.getBoundingBox().inflate(MUSEAU + 1, 2, MUSEAU + 1),
                e -> e != spino && e.isAlive() && !spino.getPassengers().contains(e))) {
            if (pietines.contains(e.getUUID()) || Math.abs(e.getY() - centre.y) > 4) {
                continue;
            }
            // touche seulement sur l'axe du corps, du centre au museau
            double d = distanceSegment(e.position(), centre, museau);
            if (d < DEMI_LARGEUR + e.getBbWidth() / 2) {
                pietines.add(e.getUUID());
                if (e == visee) {
                    touchee = e;
                } else {
                    spino.pietiner(e);
                }
            }
        }
        return touchee;
    }

    boolean chargeArrivee() {
        return chargeBut == null || spino.position().multiply(1, 0, 1).distanceTo(chargeBut.multiply(1, 0, 1)) < 2.5;
    }

    void finCharge() {
        chargeBut = null;
        arreter();
    }

    // ------------------------------------------------------------------ chaque tick

    /** @return ABANDONNER quand la destination est hors d'atteinte malgre tous les remedes. */
    Deblocage.Action tick() {
        transitionsEau();
        Vec3 but = detour != null ? detour : destination;
        if (reculTicks > 0) {
            reculTicks--;
            spino.getNavigation().stop();
            // dans l'eau rien ne freine : la meme poussee l'envoyait 10 blocs en arriere
            Vec3 arriere = Instantane.vec3(Instantane.avant(spino.yBodyRot)).scale(spino.isInWater() ? -0.02 : -0.09);
            spino.setDeltaMovement(spino.getDeltaMovement().add(arriere.x, 0, arriere.z));
            if (reculTicks == 0 && destination != null) {
                prochainChemin = 0;
                aller(destination, allure);
            }
        }
        if (detour != null && (--detourTicks <= 0 || spino.position().distanceTo(detour) < 2)) {
            detour = null;
            if (destination != null) {
                prochainChemin = 0;
                aller(destination, allure);
            }
        }
        double reste = but == null ? 0 : spino.position().multiply(1, 0, 1).distanceTo(but.multiply(1, 0, 1));
        // bloque = il VEUT avancer (le pilote commande de la vitesse : pas pendant un pivot ou un
        // freinage) et il n'est pas deja arrive, rayon d'arrivee = sa demi-largeur + marge
        // (sinon, colle a un joueur, il se croyait coince et reculait)
        double arrivee = Math.max(2.5, spino.getBbWidth() / 2 + 2.0);
        boolean veut = but != null && reste > arrivee && pilote.vitesseCourante() > 0.2 && reculTicks == 0;
        // vitesse au sol attendue : ~2.2 x (attribut x multiplicateur)^2 blocs/tick (loi de Minecraft)
        double s = pilote.vitesseCourante() * spino.getAttributeValue(net.minecraft.world.entity.ai.attributes.Attributes.MOVEMENT_SPEED);
        Deblocage.Action a = deblocage.evaluer(reste, veut, spino.isInWater() ? 0 : 2.2 * s * s);
        switch (a) {
            case SAUTER -> {
                if (spino.onGround()) {
                    spino.getJumpControl().jump();
                } else if (spino.isInWater()) {
                    spino.setDeltaMovement(spino.getDeltaMovement().add(0, 0.3, 0));   // se hisse sur la berge
                }
                arracherFeuillage();
            }
            case RECULER -> reculTicks = 20;
            case CONTOURNER -> {
                Vec3 avant = Instantane.vec3(Instantane.avant(spino.yBodyRot));
                Vec3 lat = new Vec3(-avant.z, 0, avant.x).scale(6 * cote);
                cote = -cote;                                   // l'autre cote la prochaine fois
                detour = spino.position().add(lat).add(avant.scale(2));
                detourTicks = Deblocage.PALIER_CONTOURNEMENT;
                spino.getNavigation().moveTo(detour.x, detour.y, detour.z, Allure.MARCHE.vitesse);
            }
            case ABANDONNER -> arreter();
            default -> {
            }
        }
        if (spino.horizontalCollision && veut) {
            arracherFeuillage();
        }
        return a;
    }

    static final double ANTICIPATION = Pilote.ANTICIPATION;
    private int indexVise = -1;

    /** Point vise lisse sur le chemin : voir {@link Pilote#viseeMoyenne}. */
    Vec viseeLissee(Vec voulu) {
        indexVise = -1;
        Path p = spino.getNavigation().getPath();
        if (p == null || spino.isInWater()) {
            return voulu;
        }
        List<Vec> noeuds = new ArrayList<>();
        for (int i = p.getNextNodeIndex(); i < p.getNodeCount() && noeuds.size() < 12; i++) {
            Node nd = p.getNode(i);
            noeuds.add(new Vec(nd.x + 0.5, nd.y, nd.z + 0.5));
        }
        Vec moi = Instantane.vec(spino.position());
        int n = Pilote.fenetre(moi, noeuds, ANTICIPATION);
        if (n == 0) {
            return voulu;
        }
        indexVise = p.getNextNodeIndex() + n - 1;
        return Pilote.viseeMoyenne(moi, noeuds, ANTICIPATION);
    }

    /** Points de chemin situes APRES le point vise, pour freiner avant les virages. */
    List<Vec> suivants(int n) {
        List<Vec> out = new ArrayList<>();
        Path p = spino.getNavigation().getPath();
        if (p == null) {
            return out;
        }
        int debut = Math.max(indexVise, p.getNextNodeIndex()) + 1;
        for (int i = debut; i < p.getNodeCount() && out.size() < n; i++) {
            Node nd = p.getNode(i);
            out.add(new Vec(nd.x + 0.5, nd.y, nd.z + 0.5));
        }
        return out;
    }

    /** Traduction des gestes du pilote en animations ponctuelles. */
    void geste(Pilote.Geste g) {
        if (g == Pilote.Geste.FREINAGE && !spino.attaqueEnCours()) {
            spino.triggerAnim("ambiance", "ralentissement_course_arret");
        }
        // PIVOT et VIRAGE_* se lisent cote client sur la vitesse de lacet (voir l'animation
        // de mouvement) : rien a synchroniser
    }

    private void transitionsEau() {
        boolean eau = spino.isInWater();
        if (eau && !etaitDansEau && pilote.vitesseCourante() <= Allure.MARCHE.vitesse && !spino.attaqueEnCours()) {
            // entree calme dans l'eau ; en pleine course on n'impose pas une animation de 2 s
            spino.triggerAnim("ambiance", "entree_eau");
        }
        etaitDansEau = eau;
    }

    /** Coince contre des feuilles : il les arrache (si mobGriefing). */
    private void arracherFeuillage() {
        if (!ForgeEventFactory.getMobGriefingEvent(spino.level(), spino)) {
            return;
        }
        Vec3 avant = Instantane.vec3(Instantane.avant(spino.yBodyRot));
        BlockPos base = BlockPos.containing(spino.getX() + avant.x * 2.5, spino.getY(), spino.getZ() + avant.z * 2.5);
        for (BlockPos p : BlockPos.betweenClosed(base.offset(-1, 0, -1), base.offset(1, 4, 1))) {
            if (spino.level().getBlockState(p).is(BlockTags.LEAVES)) {
                spino.level().destroyBlock(p, true, spino);
            }
        }
    }

    static double distanceSegment(Vec3 p, Vec3 a, Vec3 b) {
        double abx = b.x - a.x, abz = b.z - a.z, apx = p.x - a.x, apz = p.z - a.z;
        double l2 = abx * abx + abz * abz;
        double t = l2 < 1e-9 ? 0 : Math.max(0, Math.min(1, (apx * abx + apz * abz) / l2));
        double dx = apx - abx * t, dz = apz - abz * t;
        return Math.sqrt(dx * dx + dz * dz);
    }
}
