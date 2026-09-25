package fr.riviere.spinosaure.entite;

import fr.riviere.spinosaure.cerveau.Attaque;
import fr.riviere.spinosaure.cerveau.Cerveau;
import fr.riviere.spinosaure.cerveau.Decision;
import fr.riviere.spinosaure.cerveau.Decision.Allure;
import fr.riviere.spinosaure.cerveau.Decision.Tactique;
import fr.riviere.spinosaure.cerveau.Evenement;
import fr.riviere.spinosaure.cerveau.Reglages;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerBossEvent;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
import net.minecraft.world.BossEvent;
import net.minecraft.world.Difficulty;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.navigation.AmphibiousPathNavigation;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.pathfinder.BlockPathTypes;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.ForgeEventFactory;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;

/**
 * Le corps du spinosaure : il percoit le monde, le traduit pour le {@link Cerveau},
 * execute ses decisions (deplacement, attaques telegraphiees, saisie) et choisit les
 * animations. Toute l'intelligence est dans le cerveau, testee hors du jeu.
 *
 * Debogage en jeu : {@code /tag @e[type=spinosaure:spinosaure] add debug} affiche
 * au-dessus de sa tete la tactique en cours et la raison de sa decision.
 */
public class SpinosaureEntity extends PathfinderMob implements GeoEntity, Enemy {

    private static final EntityDataAccessor<Integer> TACTIQUE =
            SynchedEntityData.defineId(SpinosaureEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> ALLURE =
            SynchedEntityData.defineId(SpinosaureEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> SUBMERGE =
            SynchedEntityData.defineId(SpinosaureEntity.class, EntityDataSerializers.BOOLEAN);

    private static final String PREFIXE = "animation.spinosaure.";
    /** Animations ponctuelles d'ambiance que le cerveau peut demander. */
    private static final String[] AMBIANCES = {"renifle_piste_sol", "marche_regard_fixe_droite",
            "marche_regard_fixe_gauche", "secoue_proie", "degats", "degats_eau", "hurle_court",
            "entree_eau", "ralentissement_course_arret"};
    /**
     * Vitesse au sol (blocs/s) pour laquelle chaque animation de marche a ete calee,
     * mesuree sur le modele a l'echelle 1 puis ramenee a l'echelle de rendu. Le rendu
     * accelere ou ralentit l'animation selon la vitesse reelle : pas de pieds qui glissent.
     */
    private static final double MARCHE_NOMINALE = 1.08, COURSE_NOMINALE = 5.53, CHARGE_NOMINALE = 8.92,
            FEUTREE_NOMINALE = 0.23, BOITEUSE_NOMINALE = 0.77, VIRAGE_NOMINALE = 6.1;

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private final Reglages reglages = Reglages.defaut();
    private final Cerveau cerveau;
    private final Instantane instantane;
    private final Locomotion locomotion;
    private final List<Evenement> evenements = new ArrayList<>();
    private final ServerBossEvent barre = new ServerBossEvent(Component.translatable("entity.spinosaure.spinosaure"),
            BossEvent.BossBarColor.GREEN, BossEvent.BossBarOverlay.NOTCHED_10);

    private Decision decision;
    private Attaque attaque;
    private int attaqueTick;
    private LivingEntity cibleAttaque;
    private boolean chargeTouchee;
    private Player tenu;
    private boolean lacherAutorise;
    private long dernierCombat = Long.MIN_VALUE / 2;

    public SpinosaureEntity(EntityType<? extends SpinosaureEntity> type, Level level) {
        super(type, level);
        this.moveControl = new ControleDeplacement(this);
        this.setPathfindingMalus(BlockPathTypes.WATER, 0.0F);
        this.setPathfindingMalus(BlockPathTypes.WATER_BORDER, 0.0F);
        this.setMaxUpStep(1.5F);
        this.xpReward = 80;
        this.cerveau = new Cerveau(reglages, level.getRandom().nextLong());
        this.instantane = new Instantane(this, reglages);
        this.locomotion = new Locomotion(this);
        this.barre.setVisible(false);
    }

    public static AttributeSupplier.Builder attributs() {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 300.0D)
                .add(Attributes.ATTACK_DAMAGE, 14.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.34D)
                .add(Attributes.FOLLOW_RANGE, 48.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 0.9D)
                .add(Attributes.ARMOR, 8.0D)
                .add(Attributes.ATTACK_KNOCKBACK, 1.5D);
    }

    public static boolean peutApparaitre(EntityType<SpinosaureEntity> type, ServerLevelAccessor niveau,
                                         MobSpawnType raison, BlockPos pos, RandomSource alea) {
        return niveau.getDifficulty() != Difficulty.PEACEFUL
                && Mob.checkMobSpawnRules(type, niveau, raison, pos, alea)
                && alea.nextInt(4) == 0;
    }

    // ================================================================== base

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        this.entityData.define(TACTIQUE, Tactique.ERRANCE.ordinal());
        this.entityData.define(ALLURE, Allure.ARRET.ordinal());
        this.entityData.define(SUBMERGE, false);
    }

    @Override
    protected PathNavigation createNavigation(Level level) {
        return new AmphibiousPathNavigation(this, level);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new ButCerveau());
    }

    /**
     * Le modele (13 blocs de long) deborde largement de la boite de collision : sans cet
     * agrandissement, le museau et la queue disparaitraient quand le centre sort de l'ecran.
     */
    @Override
    public net.minecraft.world.phys.AABB getBoundingBoxForCulling() {
        return getBoundingBox().inflate(6.0, 2.0, 6.0);
    }

    @Override
    public boolean canBreatheUnderwater() {
        return true;
    }

    @Override
    public boolean isPushedByFluid() {
        return false;
    }

    @Override
    public boolean removeWhenFarAway(double distance) {
        // pas de disparition au milieu d'une chasse ou d'une rancune
        return level().getGameTime() - dernierCombat > 6000;
    }

    @Override
    public void checkDespawn() {
        if (level().getDifficulty() == Difficulty.PEACEFUL) {
            discard();
            return;
        }
        super.checkDespawn();
    }

    /** Sous l'eau pour de bon : le dos couvert, pas seulement les pattes. */
    public boolean estSubmerge() {
        if (level().isClientSide()) {
            return entityData.get(SUBMERGE);
        }
        return isInWater() && level().getFluidState(BlockPos.containing(getX(), getY() + 2.5, getZ())).is(FluidTags.WATER);
    }

    Locomotion locomotion() {
        return locomotion;
    }

    boolean attaqueEnCours() {
        return attaque != null;
    }

    /** Renverse ce qui se trouve sur la trajectoire d'une charge (sans l'arreter). */
    void pietiner(LivingEntity e) {
        blesser(e, 0.5, 1.6);
    }

    @Override
    public void addAdditionalSaveData(net.minecraft.nbt.CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        fr.riviere.spinosaure.cerveau.Vec t = cerveau.territoire();
        if (t != null) {
            tag.putDouble("TerritoireX", t.x());
            tag.putDouble("TerritoireY", t.y());
            tag.putDouble("TerritoireZ", t.z());
        }
    }

    @Override
    public void readAdditionalSaveData(net.minecraft.nbt.CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        if (tag.contains("TerritoireX")) {
            cerveau.definirTerritoire(new fr.riviere.spinosaure.cerveau.Vec(
                    tag.getDouble("TerritoireX"), tag.getDouble("TerritoireY"), tag.getDouble("TerritoireZ")));
        }
    }

    public Tactique tactique() {
        return Tactique.values()[entityData.get(TACTIQUE)];
    }

    public Allure allure() {
        return Allure.values()[entityData.get(ALLURE)];
    }

    @Override
    public void travel(Vec3 entree) {
        if (isEffectiveAi() && isInWater()) {
            // poussee calee pour nager a ~2.7 blocs/s (NAGE) et ~4 blocs/s (NAGE_RAPIDE)
            moveRelative(0.05F, entree);
            move(net.minecraft.world.entity.MoverType.SELF, getDeltaMovement());
            setDeltaMovement(getDeltaMovement().scale(0.9D));
        } else {
            super.travel(entree);
        }
    }

    // ================================================================== degats recus

    @Override
    public boolean hurt(DamageSource source, float montant) {
        boolean touche = super.hurt(source, montant);
        if (touche && !level().isClientSide()) {
            if (source.getEntity() instanceof Player p && !p.isCreative()) {
                evenements.add(new Evenement.Degats(p.getUUID(), montant, source.getDirectEntity() instanceof Projectile));
                dernierCombat = level().getGameTime();
            }
            if (attaque == null && isAlive()) {
                triggerAnim("ambiance", isInWater() ? "degats_eau" : "degats");
            }
        }
        return touche;
    }

    @Override
    protected void tickDeath() {
        // l'animation de mort dure 4 s : on laisse le corps le temps de tomber
        ++this.deathTime;
        if (this.deathTime >= 80 && !level().isClientSide() && !isRemoved()) {
            level().broadcastEntityEvent(this, (byte) 60);
            remove(Entity.RemovalReason.KILLED);
        }
    }

    // ================================================================== saisie

    /** Le joueur est-il tenu dans la gueule (et interdit de descendre) ? */
    public boolean retient(Entity e) {
        // jamais un mort ou un joueur qui quitte le monde : sinon il resterait accroche
        return e == tenu && !lacherAutorise && e.isAlive() && !e.isRemoved();
    }

    @Override
    protected boolean canAddPassenger(Entity passager) {
        return getPassengers().isEmpty() && passager instanceof Player;
    }

    @Override
    public boolean shouldRiderSit() {
        return false;
    }

    @Override
    protected void positionRider(Entity passager, Entity.MoveFunction place) {
        // dans la gueule : 5 blocs devant le centre, a hauteur de machoire
        Vec3 avant = Instantane.vec3(Instantane.avant(yBodyRot));
        place.accept(passager, getX() + avant.x * 5.0, getY() + 2.4 - passager.getBbHeight() / 2, getZ() + avant.z * 5.0);
    }

    private void lacher() {
        if (tenu != null) {
            lacherAutorise = true;
            tenu.stopRiding();
            Vec3 avant = Instantane.vec3(Instantane.avant(yBodyRot));
            tenu.setDeltaMovement(avant.x * 0.6, 0.35, avant.z * 0.6);
            tenu.hurtMarked = true;
            tenu = null;
            lacherAutorise = false;
        }
    }

    // ================================================================== boucle serveur

    private final class ButCerveau extends Goal {
        ButCerveau() {
            setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK, Flag.JUMP, Flag.TARGET));
        }

        @Override
        public boolean canUse() {
            return isAlive();
        }

        @Override
        public boolean requiresUpdateEveryTick() {
            return true;
        }

        @Override
        public void tick() {
            vivre();
        }
    }

    private void vivre() {
        long tick = level().getGameTime();
        entityData.set(SUBMERGE, estSubmerge());

        // le joueur tenu a pu mourir, se deconnecter, etre teleporte
        if (tenu != null && (!tenu.isAlive() || tenu.getVehicle() != this)) {
            tenu = null;
            cerveau.priseRompue(tick);
        }

        // reflechir tous les 4 ticks (decale d'une entite a l'autre), agir a chaque tick
        if (decision == null || (tick + getId()) % 4 == 0) {
            List<Evenement> evts = new ArrayList<>(evenements);
            evenements.clear();
            decision = cerveau.penser(instantane.soi(attaque != null), instantane.joueurs(), evts);
            appliquerNouvelleDecision(decision);
        }
        executer(decision);
        tickAttaque();
        if (locomotion.tick() == fr.riviere.spinosaure.cerveau.Deblocage.Action.ABANDONNER) {
            cerveau.destinationBloquee(tick);         // le cerveau choisit autre chose
        }
        regeneration(tick);
        barre(tick);
        if (tick % 10 == 0 && getTags().contains("debug")) {
            setCustomName(Component.literal(decision.tactique() + " : " + decision.raison()));
            setCustomNameVisible(true);
        }
    }

    private Player joueur(java.util.UUID id) {
        return id == null ? null : level().getPlayerByUUID(id);
    }

    private void appliquerNouvelleDecision(Decision d) {
        entityData.set(TACTIQUE, d.tactique().ordinal());
        entityData.set(ALLURE, d.allure().ordinal());
        if (d.lacher()) {
            lacher();
        }
        if (d.animation() != null) {
            triggerAnim("ambiance", d.animation());
        }
        if (d.attaque() != null && attaque == null) {
            demarrerAttaque(d.attaque(), joueur(d.cible()), d.destination());
        }
        if (d.tactique() != Tactique.ERRANCE && d.tactique() != Tactique.ENQUETE) {
            dernierCombat = level().getGameTime();
        }
    }

    private void executer(Decision d) {
        if (attaque == Attaque.CHARGE) {
            return;                                         // la charge suit sa propre trajectoire
        }
        if (attaque != null) {
            locomotion.arreter();                           // attaque engagee : il ne bouge plus
            if (cibleAttaque != null && attaque != Attaque.BALAYAGE_QUEUE && attaqueTick < premierImpact(attaque)) {
                getLookControl().setLookAt(cibleAttaque, 20.0F, 20.0F);
                tournerVers(cibleAttaque.position(), 6.0F);
            }
            return;
        }
        if (d.regard() != null) {
            getLookControl().setLookAt(d.regard().x(), d.regard().y() + 1.5, d.regard().z(), 30.0F, 30.0F);
        }
        if (d.destination() == null || d.allure() == Allure.ARRET) {
            locomotion.arreter();
            if (d.regard() != null) {
                tournerVers(Instantane.vec3(d.regard()), (float) fr.riviere.spinosaure.cerveau.Pilote.PIVOT_DEG);
            }
            return;
        }
        locomotion.aller(Instantane.vec3(d.destination()), d.allure());
    }

    private void tournerVers(Vec3 cible, float max) {
        double dx = cible.x - getX(), dz = cible.z - getZ();
        float cap = (float) (Mth.atan2(dz, dx) * Mth.RAD_TO_DEG) - 90.0F;
        setYRot(Mth.approachDegrees(getYRot(), cap, max));
        yBodyRot = getYRot();
    }

    // ================================================================== attaques

    private static int premierImpact(Attaque a) {
        return a.impacts.length == 0 ? 0 : a.impacts[0];
    }

    private void demarrerAttaque(Attaque a, Player cible, fr.riviere.spinosaure.cerveau.Vec visee) {
        attaque = a;
        attaqueTick = 0;
        cibleAttaque = cible;
        chargeTouchee = false;
        if (a == Attaque.CHARGE) {
            Vec3 point = visee != null ? Instantane.vec3(visee) : (cible != null ? cible.position() : null);
            if (point == null) {
                attaque = null;
                return;
            }
            locomotion.lancerCharge(point);
            playSound(SoundEvents.RAVAGER_ROAR, 3.0F, 0.8F);   // le signal : on a le temps de s'ecarter
        }
        if (a != Attaque.CHARGE) {
            triggerAnim("action", a.animation);   // la charge est une allure, pas une action
        }
        if (a == Attaque.RUGISSEMENT) {
            playSound(SoundEvents.RAVAGER_ROAR, 4.0F, 0.55F);
        }
    }

    private void tickAttaque() {
        if (attaque == null) {
            return;
        }
        attaqueTick++;
        for (int impact : attaque.impacts) {
            if (attaqueTick == impact) {
                frapper(attaque);
            }
        }
        if (attaque == Attaque.BOND && attaqueTick == 6 && cibleAttaque != null) {
            Vec3 elan = cibleAttaque.position().subtract(position()).multiply(1, 0, 1).normalize();
            setDeltaMovement(elan.x * 1.15, 0.55, elan.z * 1.15);
        }
        if (attaque == Attaque.CHARGE) {
            LivingEntity t = chargeTouchee ? null : locomotion.tickCharge(cibleAttaque);
            if (t != null) {
                chargeTouchee = true;
                blesser(t, Attaque.CHARGE.degats, 2.2);
            }
            if (chargeTouchee || locomotion.chargeArrivee() || attaqueTick >= attaque.duree) {
                locomotion.finCharge();                    // le pilote freine : il ne s'arrete pas net
                attaque = null;
                cibleAttaque = null;
            }
            return;
        }
        if (attaqueTick >= attaque.duree) {
            attaque = null;
            cibleAttaque = null;
        }
    }

    private void frapper(Attaque a) {
        Vec3 avant = Instantane.vec3(Instantane.avant(yBodyRot));
        switch (a) {
            case MORSURE, MORSURE_LATERALE, BOND -> {
                LivingEntity v = meilleurDansCone(avant, reglages.porteeMorsure, a == Attaque.MORSURE_LATERALE ? 120 : 70);
                if (v != null) {
                    blesser(v, a.degats, 0.6);
                }
            }
            case GRIFFES -> {
                for (LivingEntity v : dansCone(avant, reglages.porteeGriffes, 90)) {
                    if (v instanceof Player p && p.isBlocking()) {
                        p.disableShield(true);            // comme un coup de hache
                    }
                    blesser(v, a.degats, 0.8);
                }
            }
            case BALAYAGE_QUEUE -> {
                // pivot complet : tout ce qui l'entoure
                for (LivingEntity v : level().getEntitiesOfClass(LivingEntity.class,
                        getBoundingBox().inflate(reglages.porteeQueue, 1.5, reglages.porteeQueue),
                        e -> e != this && e.isAlive() && !getPassengers().contains(e)
                                && e.distanceTo(this) <= reglages.porteeQueue + 1.5)) {
                    blesser(v, a.degats, 1.8);
                }
            }
            case SAISIE -> {
                LivingEntity v = meilleurDansCone(avant, reglages.porteeSaisie, 70);
                if (v instanceof Player p && tenu == null) {
                    blesser(p, a.degats, 0.0);
                    if (p.isAlive() && p.startRiding(this, true)) {
                        tenu = p;
                        cerveau.priseEtablie(p.getUUID(), level().getGameTime());
                    }
                }
            }
            case RUGISSEMENT -> {
                for (Player p : level().getEntitiesOfClass(Player.class, getBoundingBox().inflate(16),
                        p -> p.isAlive() && !p.isCreative() && !p.isSpectator())) {
                    p.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 60, 1), this);
                    p.addEffect(new MobEffectInstance(MobEffects.WEAKNESS, 60, 0), this);
                }
            }
            case CHARGE -> {
            }
        }
    }

    private void blesser(LivingEntity v, double multiplicateur, double recul) {
        float degats = (float) (getAttributeValue(Attributes.ATTACK_DAMAGE) * multiplicateur);
        if (v.hurt(damageSources().mobAttack(this), degats) && recul > 0) {
            Vec3 dir = v.position().subtract(position()).multiply(1, 0, 1).normalize();
            v.knockback(recul, -dir.x, -dir.z);
        }
    }

    private List<LivingEntity> dansCone(Vec3 avant, double portee, double ouverture) {
        return level().getEntitiesOfClass(LivingEntity.class, getBoundingBox().inflate(portee, 2.0, portee), e -> {
            if (e == this || !e.isAlive() || getPassengers().contains(e)) {
                return false;
            }
            Vec3 v = e.position().subtract(position());
            double dh = Math.sqrt(v.x * v.x + v.z * v.z);
            if (dh > portee + e.getBbWidth() / 2 || Math.abs(v.y) > 4.5) {
                return false;
            }
            double cos = (v.x * avant.x + v.z * avant.z) / Math.max(dh, 1e-6);
            return Math.toDegrees(Math.acos(Mth.clamp(cos, -1, 1))) <= ouverture / 2;
        });
    }

    private LivingEntity meilleurDansCone(Vec3 avant, double portee, double ouverture) {
        LivingEntity best = null;
        for (LivingEntity e : dansCone(avant, portee, ouverture)) {
            if (e == cibleAttaque) {
                return e;                                  // la cible visee d'abord
            }
            if (best == null || e.distanceToSqr(this) < best.distanceToSqr(this)) {
                best = e;
            }
        }
        return best;
    }

    // ================================================================== soins, barre de vie

    private void regeneration(long tick) {
        if (tick % 20 != 0 || getHealth() >= getMaxHealth()) {
            return;
        }
        if (decision.tactique() == Tactique.REGENERATION && estSubmerge()) {
            heal((float) reglages.regenParSeconde);
        } else if (tick - dernierCombat > 1200) {
            heal(0.5F);                                    // lentement, hors combat
        }
        if (tenu != null && tick % 40 == 0) {
            // tenu hors de l'eau : il est secoue ; sous l'eau, c'est la noyade qui agit
            if (!estSubmerge()) {
                triggerAnim("ambiance", "secoue_proie");
            }
            blesser(tenu, 0.25, 0.0);
        }
    }

    private void barre(long tick) {
        barre.setProgress(getHealth() / getMaxHealth());
        boolean combat = tick - dernierCombat < 200;
        barre.setVisible(combat);
    }

    @Override
    public void startSeenByPlayer(ServerPlayer joueur) {
        super.startSeenByPlayer(joueur);
        barre.addPlayer(joueur);
    }

    @Override
    public void stopSeenByPlayer(ServerPlayer joueur) {
        super.stopSeenByPlayer(joueur);
        barre.removePlayer(joueur);
    }

    // ================================================================== animations

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controleurs) {
        // ordre = priorite croissante : une attaque recouvre une animation d'ambiance
        controleurs.add(new AnimationController<>(this, "mouvement", 5, this::mouvement));

        AnimationController<SpinosaureEntity> ambiance = new AnimationController<>(this, "ambiance", 5, e -> PlayState.STOP);
        for (String nom : AMBIANCES) {
            ambiance.triggerableAnim(nom, RawAnimation.begin().thenPlay(PREFIXE + nom));
        }
        controleurs.add(ambiance);

        AnimationController<SpinosaureEntity> action = new AnimationController<>(this, "action", 3, e -> PlayState.STOP);
        for (Attaque a : Attaque.values()) {
            if (a != Attaque.CHARGE) {
                action.triggerableAnim(a.animation, RawAnimation.begin().thenPlay(PREFIXE + a.animation));
            }
        }
        controleurs.add(action);
    }

    private PlayState mouvement(AnimationState<SpinosaureEntity> etat) {
        double v = Math.hypot(getX() - xo, getZ() - zo) * 20.0;          // blocs/s reels
        double lacet = Mth.wrapDegrees(yBodyRot - yBodyRotO);             // degres/tick, + = a droite
        double e = fr.riviere.spinosaure.SpinosaureMod.ECHELLE;
        Tactique t = tactique();
        String nom;
        double nominale = 0;
        if (isDeadOrDying()) {
            return etat.setAndContinue(RawAnimation.begin().thenPlayAndHold(PREFIXE + (isInWater() ? "mort_eau" : "mort")));
        }
        if (isInWater()) {
            if (v > 0.3) {
                nom = allure() == Allure.NAGE_RAPIDE ? "nage_rapide_ror" : (estSubmerge() ? "nage_sous_eau" : "nage_surface");
            } else {
                nom = t == Tactique.AFFUT_EAU ? "affut_eau" : "nage_derive_ror";
            }
        } else if (!onGround() && getDeltaMovement().y < -0.35) {
            nom = "chute";
        } else if (v < 0.25 && Math.abs(lacet) > 1.5) {
            nom = "tourne_sur_place";                                     // pivot sur place
        } else if (v > 3.0 && Math.abs(lacet) > 2.5) {
            nom = lacet > 0 ? "virage_serre_droite" : "virage_serre_gauche";   // penche dans le virage
            nominale = VIRAGE_NOMINALE;
        } else if (v > 0.25) {
            switch (allure()) {
                case FEUTREE -> { nom = "marche_feutree"; nominale = FEUTREE_NOMINALE; }
                case COURSE -> { nom = "course"; nominale = COURSE_NOMINALE; }
                case CHARGE -> { nom = "charge"; nominale = CHARGE_NOMINALE; }
                default -> {
                    boolean blesse = getHealth() / getMaxHealth() < reglages.seuilRepli;
                    nom = blesse ? "marche_boiteuse" : "marche";
                    nominale = blesse ? BOITEUSE_NOMINALE : MARCHE_NOMINALE;
                }
            }
        } else {
            nom = switch (t) {
                case FIGE -> "fige_en_traque";
                case TRAQUE -> "traque_lente";
                default -> getHealth() / getMaxHealth() < reglages.seuilRepli ? "respiration_lourde" : "repos";
            };
        }
        etat.getController().setAnimationSpeed(nominale > 0 ? Mth.clamp(v / (nominale * e), 0.5, 2.2) : 1.0);
        return etat.setAndContinue(RawAnimation.begin().thenLoop(PREFIXE + nom));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }
}
