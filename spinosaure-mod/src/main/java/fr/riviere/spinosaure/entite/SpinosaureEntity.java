package fr.riviere.spinosaure.entite;

import fr.riviere.spinosaure.cerveau.Animations;
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
import net.minecraft.sounds.SoundEvents;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
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
import net.minecraft.world.level.block.state.BlockState;
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
    /** Distance a sa cible (pour choisir l'animation de course cote client). */
    private static final EntityDataAccessor<Float> DISTANCE_CIBLE =
            SynchedEntityData.defineId(SpinosaureEntity.class, EntityDataSerializers.FLOAT);

    private static final String PREFIXE = "animation.spinosaure.";
    /**
     * Vitesse au sol (blocs/s) pour laquelle chaque animation de marche a ete calee,
     * mesuree sur le modele a l'echelle 1 puis ramenee a l'echelle de rendu. Le rendu
     * accelere ou ralentit l'animation selon la vitesse reelle : pas de pieds qui glissent.
     */
    private static final double MARCHE_NOMINALE = 1.08, COURSE_NOMINALE = 5.53, CHARGE_NOMINALE = 8.92,
            FEUTREE_NOMINALE = 0.23, BOITEUSE_NOMINALE = 0.77, VIRAGE_NOMINALE = 6.1, EAU_NOMINALE = 0.80,
            // mesurees de la meme facon (vitesse du pied pose, cinematique directe sur le modele)
            MENACE_NOMINALE = 0.43, OBSERVATION_NOMINALE = 0.81, GRIMPE_NOMINALE = 0.63, RUEE_NOMINALE = 3.54,
            MAINTIEN_NOMINALE = 1.09;

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private final Reglages reglages = Reglages.defaut();
    private final Cerveau cerveau;
    private final Instantane instantane;
    private final Locomotion locomotion;
    private final List<Evenement> evenements = new ArrayList<>();
    private final java.util.Map<java.util.UUID, Long> derniersTirs = new java.util.HashMap<>();

    private Decision decision;
    private Attaque attaque;
    private int attaqueTick;
    private LivingEntity cibleAttaque;
    private boolean chargeTouchee;
    private Player tenu;
    private boolean lacherAutorise;
    private long dernierCombat = Long.MIN_VALUE / 2;
    private Tactique tactiquePrecedente = Tactique.ERRANCE;
    private long prochainePresence;
    private long dernierActif = Long.MIN_VALUE / 2;
    private long derniereAnnonce = Long.MIN_VALUE / 2;
    /** Creatures qui l'ont frappe, et quand : il les combat (une minute de rancune). */
    private final java.util.Map<java.util.UUID, Long> agresseurs = new java.util.HashMap<>();
    /** Attaque en cours : l'animation jouee (variante selon le terrain), sa duree, ses impacts. */
    private Variante variante;
    /** Il ne bouge pas avant ce tick (reveil, se relever, rugissement de victoire, inspection). */
    private long immobileJusqua;
    private boolean rugirVictoire;
    private long prochainInspecte, prochainSaut;
    // transitions du corps (eau, sauts, chutes)
    private boolean etaitSubmerge, etaitDansEau, etaitAuSol = true;
    private int submergeTicks, surfaceTicks, dansEauTicks, horsEauTicks;
    private double eauQuittee;
    private float hauteurChute;
    /** Vitesse de montee lissee (blocs/tick), des deux cotes : pour l'animation d'escalade. */
    private double montee;
    // cote client : depuis quand la tactique affichee est en cours
    private Tactique tactiqueVue = Tactique.ERRANCE;
    private int tactiqueVueDepuis;

    /** Animation d'attaque jouee et son minutage (impacts mesures sur l'animation). */
    private record Variante(String animation, int duree, int[] impacts, double allonge) {
        static Variante de(Attaque a) {
            return new Variante(a.animation, a.duree, a.impacts, 0);
        }
    }

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
        if (!fr.riviere.spinosaure.Reglage.APPARITION_NATURELLE.get()) {
            return false;
        }
        if (niveau.getDifficulty() == Difficulty.PEACEFUL || !Mob.checkMobSpawnRules(type, niveau, raison, pos, alea)
                || alea.nextInt(4) != 0) {
            return false;
        }
        // un nombre limite par zone : un super-predateur est rare, et un evenement ne doit pas
        // se transformer en elevage (compte les spinosaures des chunks charges)
        int r = fr.riviere.spinosaure.Reglage.RAYON_ZONE.get();
        net.minecraft.world.phys.AABB zone = new net.minecraft.world.phys.AABB(pos).inflate(r, 384, r);
        return niveau.getEntitiesOfClass(SpinosaureEntity.class, zone, net.minecraft.world.entity.Entity::isAlive).size()
                < fr.riviere.spinosaure.Reglage.MAX_PAR_ZONE.get();
    }

    // ================================================================== base

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        this.entityData.define(TACTIQUE, Tactique.ERRANCE.ordinal());
        this.entityData.define(ALLURE, Allure.ARRET.ordinal());
        this.entityData.define(SUBMERGE, false);
        this.entityData.define(DISTANCE_CIBLE, 99F);
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

    // ------------------------------------------------------------------ sons
    // Sons du ravageur, plus graves : aucun fichier son a fournir. Muet pendant la traque et
    // l'affut : le silence fait partie de la menace.

    @Override
    protected net.minecraft.sounds.SoundEvent getAmbientSound() {
        return silencieux(tactique()) ? null : SoundEvents.RAVAGER_AMBIENT;
    }

    @Override
    public int getAmbientSoundInterval() {
        return 240;
    }

    @Override
    protected net.minecraft.sounds.SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.RAVAGER_HURT;
    }

    @Override
    protected net.minecraft.sounds.SoundEvent getDeathSound() {
        return SoundEvents.RAVAGER_DEATH;
    }

    @Override
    protected void playStepSound(BlockPos pos, net.minecraft.world.level.block.state.BlockState etat) {
        if (!silencieux(tactique()) || allure() == Allure.COURSE) {   // il file sans bruit
            playSound(SoundEvents.RAVAGER_STEP, 0.9F, 0.6F);
        }
    }

    @Override
    protected float getSoundVolume() {
        return 2.5F;
    }

    @Override
    public float getVoicePitch() {
        return 0.6F + getRandom().nextFloat() * 0.1F;
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
        return level().getGameTime() - dernierActif > 6000;
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
    /**
     * Devant lui, a hauteur des pieds et juste au-dessus : un ouvrage humain (planches, marches,
     * dalles, murets, briques, rondins ecorces...) ? Il enjambe le terrain naturel (talus, racines,
     * rochers) mais n'escalade pas les maisons, les pontons ni les toits en escalier.
     */
    boolean obstacleArtificiel() {
        Vec3 avant = Instantane.vec3(Instantane.avant(yBodyRot));
        double d = getBbWidth() / 2 + 0.6;
        for (int lat = -1; lat <= 1; lat++) {
            BlockPos p = BlockPos.containing(getX() + avant.x * d - avant.z * lat * 1.2, getY() + 0.5,
                    getZ() + avant.z * d + avant.x * lat * 1.2);
            for (int dy = 0; dy <= 1; dy++) {
                if (artificiel(level().getBlockState(p.above(dy)))) {
                    return true;
                }
            }
        }
        return false;
    }

    static boolean artificiel(BlockState s) {
        if (s.isAir() || !s.getFluidState().isEmpty() && s.getCollisionShape(net.minecraft.world.level.EmptyBlockGetter.INSTANCE, BlockPos.ZERO).isEmpty()) {
            return false;
        }
        if (s.is(BlockTags.PLANKS) || s.is(BlockTags.STAIRS) || s.is(BlockTags.SLABS) || s.is(BlockTags.FENCES)
                || s.is(BlockTags.WALLS) || s.is(BlockTags.DOORS) || s.is(BlockTags.TRAPDOORS) || s.is(BlockTags.BEDS)) {
            return true;
        }
        String n = net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(s.getBlock()).getPath();
        return n.contains("stripped") || n.contains("brick") || n.contains("concrete") || n.contains("glass")
                || n.contains("terracotta") || n.contains("wool") || n.contains("quartz") || n.contains("copper")
                || n.contains("iron") || n.contains("barrel") || n.contains("chest") || n.contains("polished");
    }

    /** Pas automatique de 1,5 bloc sur le terrain naturel, celui d'un joueur devant un ouvrage. */
    @Override
    public float maxUpStep() {
        return !level().isClientSide() && obstacleArtificiel() ? 0.6F : super.maxUpStep();
    }

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

    /**
     * Une creature a combattre : celle qu'on lui a designee (commande, autre mod qui pose sa
     * cible), une creature qui le vise, ou qui l'a frappe il y a moins d'une minute.
     */
    boolean ennemi(LivingEntity e) {
        if (e == this || e instanceof Player || !e.isAlive()) {
            return false;
        }
        long tick = level().getGameTime();
        if (e == getTarget() || (e instanceof Mob m && m.getTarget() == this)) {
            agresseurs.put(e.getUUID(), tick);          // engage : il ne l'oublie pas s'il change d'avis
            return true;
        }
        Long t = agresseurs.get(e.getUUID());
        return t != null && tick - t < 1200;
    }

    /** Joueur ou creature vivante de cet identifiant, ou null. */
    private LivingEntity vivant(java.util.UUID id) {
        if (id == null) {
            return null;
        }
        Player p = level().getPlayerByUUID(id);
        if (p != null) {
            return p;
        }
        if (level() instanceof net.minecraft.server.level.ServerLevel sl && sl.getEntity(id) instanceof LivingEntity le
                && le.isAlive()) {
            return le;
        }
        return null;
    }

    /** Lecture seule, pour les essais en jeu (GameTest) et le debogage. */
    public fr.riviere.spinosaure.cerveau.Attaque attaqueActive() {
        return attaque;
    }

    /**
     * Pour les essais : points du terrain echantillonne ou il peut aller (sol a 4 blocs pres,
     * jungle ou eau, sans danger). Sous une canopee, ils etaient tous sur la cime des arbres.
     */
    public long pointsPraticables() {
        return instantane.voisinage().stream()
                .filter(p -> !p.danger() && p.domaine() && Math.abs(p.denivele()) <= 4).count();
    }

    public java.util.UUID cibleActuelle() {
        return cerveau.cible();
    }

    public fr.riviere.spinosaure.cerveau.Vec destinationDecision() {
        return decision == null ? null : decision.destination();
    }

    public String raisonDecision() {
        return decision == null ? "" : decision.raison();
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
            double y0 = getY();
            boolean tetehors = !estSubmerge();
            moveRelative(0.05F, entree);
            move(net.minecraft.world.entity.MoverType.SELF, getDeltaMovement());
            Vec3 v = getDeltaMovement().scale(0.9D);
            // contre une berge franchissable, il se hisse (le vanilla le fait ; notre nage l'avait perdu :
            // en jeu il restait bloque dans l'angle d'un bassin a bords droits)
            // seulement tete hors de l'eau : sous l'eau, cette poussee le faisait escalader les parois
            // et seulement sur une berge naturelle : contre un ponton ou des pilotis, il se hissait
            // sur le village
            if (tetehors && horizontalCollision && !obstacleArtificiel() && isFree(v.x, v.y + 1.6 - getY() + y0, v.z)) {
                v = new Vec3(v.x, 0.3, v.z);
            } else if (!plongeeVoulue) {
                // flottaison : sans plongee voulue, il se tient dos affleurant (la surface a
                // PROFONDEUR_NAGE au-dessus des pieds), ou pose sur le fond si l'eau est moins
                // profonde. Avant, rien ne le tirait vers le haut ni vers le bas : il restait a
                // la hauteur ou il etait entre dans l'eau et semblait voler au-dessus.
                double surface = surfaceEau();
                if (!Double.isNaN(surface)) {
                    double ecart = (surface - PROFONDEUR_NAGE) - getY();
                    v = new Vec3(v.x, v.y * 0.6 + Mth.clamp(ecart * 0.06, -0.08, 0.05), v.z);
                }
            }
            setDeltaMovement(v);
        } else {
            super.travel(entree);
        }
    }

    /** Hauteur des pieds sous la surface quand il nage en surface (dos et voile hors de l'eau). */
    static final double PROFONDEUR_NAGE = 2.6;
    /** Posee par le controle de deplacement : il vise un point plus bas, on ne le fait pas remonter. */
    boolean plongeeVoulue;

    /** y de la surface de l'eau au-dessus de lui (NaN si pas d'eau a ses pieds). */
    double surfaceEau() {
        BlockPos p = BlockPos.containing(getX(), getY() + 0.1, getZ());
        if (!level().getFluidState(p).is(FluidTags.WATER)) {
            return Double.NaN;
        }
        for (int i = 0; i < 24 && level().getFluidState(p.above()).is(FluidTags.WATER); i++) {
            p = p.above();
        }
        return p.getY() + level().getFluidState(p).getHeight(level(), p);
    }

    // ================================================================== degats recus

    @Override
    public boolean hurt(DamageSource source, float montant) {
        boolean touche = super.hurt(source, montant);
        if (touche && !level().isClientSide()) {
            Entity auteur = source.getEntity();
            if (auteur instanceof Player p) {
                if (!p.isCreative() && !p.isSpectator()) {
                    evenements.add(new Evenement.Degats(p.getUUID(), montant, source.getDirectEntity() instanceof Projectile));
                    dernierCombat = level().getGameTime();
                }
            } else if (auteur instanceof LivingEntity le && le != this && le.isAlive()) {
                // une creature (un autre monstre, un loup, un golem, une creature d'un autre mod) :
                // il s'en souvient et la combat (avant, seuls les coups des joueurs comptaient)
                agresseurs.put(le.getUUID(), level().getGameTime());
                evenements.add(new Evenement.Degats(le.getUUID(), montant, source.getDirectEntity() instanceof Projectile));
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

    /**
     * Un coup de feu (balle TaCZ) a ete tire par ce joueur a portee d'oreille. Limite a un
     * evenement par demi-seconde et par tireur : une rafale ne sature pas le cerveau.
     */
    public void entendreTir(Player tireur) {
        long tick = level().getGameTime();
        Long dernier = derniersTirs.get(tireur.getUUID());
        if (dernier != null && tick - dernier < 10) {
            return;
        }
        derniersTirs.put(tireur.getUUID(), tick);
        evenements.add(new Evenement.Tir(tireur.getUUID(), Instantane.vec(tireur.position())));
    }

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
            decision = cerveau.penser(instantane.soi(attaque != null, vivant(cerveau.cible())), instantane.joueurs(), evts);
            appliquerNouvelleDecision(decision);
        }
        executer(decision);
        tickAttaque();
        if (locomotion.tick() == fr.riviere.spinosaure.cerveau.Deblocage.Action.ABANDONNER) {
            cerveau.destinationBloquee(tick);         // le cerveau choisit autre chose
            Tactique t = decision.tactique();
            if (!isInWater() && attaque == null && tick >= prochainInspecte
                    && (t == Tactique.ERRANCE || t == Tactique.ENQUETE)) {
                triggerAnim("ambiance", "inspecte_obstacle");         // il renifle ce qui le bloque
                immobileJusqua = tick + 60;
                prochainInspecte = tick + 600;
            }
        }
        if (rugirVictoire && attaque == null) {
            rugirVictoire = false;
            triggerAnim("ambiance", "rugissement_territorial_cinematique");
            playSound(SoundEvents.RAVAGER_ROAR, 4.5F, 0.5F);
            immobileJusqua = tick + 168;
        }
        transitionsCorps(tick);
        LivingEntity c = vivant(cerveau.cible());
        entityData.set(DISTANCE_CIBLE, c == null ? 99F : c.distanceTo(this));
        if (tick % 200 == 0) {
            agresseurs.values().removeIf(t -> tick - t > 1200);
        }
        regeneration(tick);
        presence(tick);
        if (tick % 10 == 0 && getTags().contains("debug")) {
            setCustomName(Component.literal(decision.tactique() + " : " + decision.raison()));
            setCustomNameVisible(true);
        }
    }


    private void appliquerNouvelleDecision(Decision d) {
        entityData.set(TACTIQUE, d.tactique().ordinal());
        entityData.set(ALLURE, d.allure().ordinal());
        if (d.lacher()) {
            lacher();
        }
        transitionTactique(tactiquePrecedente, d.tactique());
        if (d.animation() != null) {
            triggerAnim("ambiance", resoudre(d.animation()));
        }
        if (d.attaque() != null && attaque == null) {
            demarrerAttaque(d.attaque(), vivant(d.cible()), d.destination());
        }
        long tick = level().getGameTime();
        if (enCombat(d.tactique())) {
            dernierCombat = tick;
        }
        if (d.tactique() != Tactique.ERRANCE && d.tactique() != Tactique.ENQUETE) {
            dernierActif = tick;
        }
        // il jaillit de l'ombre : c'est le seul moment ou il rugit (le sursaut)
        if (d.tactique() == Tactique.ENGAGEMENT && silencieux(tactiquePrecedente)
                && tactiquePrecedente != Tactique.DISPARITION && tick - derniereAnnonce > 200) {
            derniereAnnonce = tick;
            playSound(SoundEvents.RAVAGER_ROAR, 3.5F, 0.7F);
        }
        tactiquePrecedente = d.tactique();
    }

    private void executer(Decision d) {
        if (attaque == Attaque.CHARGE) {
            return;                                         // la charge suit sa propre trajectoire
        }
        if (attaque == null && level().getGameTime() < immobileJusqua) {
            locomotion.arreter();                           // il finit de se relever, de rugir...
            if (d.regard() != null) {
                getLookControl().setLookAt(d.regard().x(), d.regard().y() + 1.5, d.regard().z(), 10.0F, 10.0F);
            }
            return;
        }
        if (attaque != null) {
            locomotion.arreter();                           // attaque engagee : il ne bouge plus
            if (cibleAttaque != null && attaque != Attaque.BALAYAGE_QUEUE && attaqueTick < premierImpact(variante)) {
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

    // ================================================================== transitions du corps

    /** S'endormir, se reveiller, se coucher, se relever, emerger lentement de l'eau. */
    private void transitionTactique(Tactique avant, Tactique apres) {
        if (avant == apres) {
            return;
        }
        long tick = level().getGameTime();
        if (apres == Tactique.SOMMEIL) {
            triggerAnim("ambiance", "endormissement");
        } else if (avant == Tactique.SOMMEIL) {
            triggerAnim("ambiance", "reveil");
            immobileJusqua = tick + 50;                    // il met un instant a se lever
        } else if (apres == Tactique.REPOS) {
            triggerAnim("ambiance", "se_couche_ror");
        } else if (avant == Tactique.REPOS) {
            triggerAnim("ambiance", "se_releve_ror");
            immobileJusqua = tick + 36;
        } else if (avant == Tactique.AFFUT_EAU && isInWater() && profondeurSous() >= 3
                && (apres == Tactique.FIGE || apres == Tactique.OBSERVATION || apres == Tactique.INTIMIDATION)) {
            triggerAnim("ambiance", "emergence_lente");  // il monte du fond, lentement, face a toi
        }
    }

    /** Noms symboliques du cerveau : le corps choisit selon ce qui l'entoure. */
    private String resoudre(String anim) {
        if (Animations.PAUSE_ERRANCE.equals(anim)) {
            return pauseErrance();
        }
        if ("tete_inclinee_fixe".equals(anim) && getRandom().nextInt(3) == 0) {
            return "spasmes_cou";
        }
        return anim;
    }

    /** A l'arret pendant l'errance : il pêche, boit, appelle un congenere, rugit, flaire. */
    private String pauseErrance() {
        RandomSource a = getRandom();
        if (isInWater()) {
            return "peche_gueule_eau";
        }
        if (eauDevant() && a.nextInt(3) != 0) {
            return "boit";
        }
        boolean congenere = !level().getEntitiesOfClass(SpinosaureEntity.class, getBoundingBox().inflate(64),
                e -> e != this && e.isAlive()).isEmpty();
        if (congenere && a.nextInt(2) == 0) {
            playSound(SoundEvents.RAVAGER_AMBIENT, 3.0F, 0.45F);
            return "communication_congeneres";
        }
        int k = a.nextInt(10);
        if (k == 0) {
            playSound(SoundEvents.RAVAGER_ROAR, 4.0F, 0.5F);      // il marque son territoire
            return "hurle_long";
        }
        if (k == 1) {
            return "spasmes_cou";
        }
        return "renifle_air";
    }

    /** De l'eau devant lui, a 2 a 6 blocs, au niveau de ses pieds ou juste dessous. */
    private boolean eauDevant() {
        Vec3 avant = Instantane.vec3(Instantane.avant(yBodyRot));
        for (int k = 2; k <= 6; k++) {
            BlockPos p = BlockPos.containing(getX() + avant.x * k, getY() - 0.5, getZ() + avant.z * k);
            if (level().getFluidState(p).is(FluidTags.WATER) || level().getFluidState(p.below()).is(FluidTags.WATER)) {
                return true;
            }
        }
        return false;
    }

    /** Blocs d'eau sous ses pieds (jusqu'a 12). */
    private int profondeurSous() {
        BlockPos p = blockPosition();
        int n = 0;
        while (n < 12 && level().getFluidState(p.below(n + 1)).is(FluidTags.WATER)) {
            n++;
        }
        return n;
    }

    /**
     * Plonger, remonter, s'ebrouer, sauter, se recevoir. Les animations qui abaissent le modele
     * de 3 a 4 blocs (plonge, remonte) ne partent qu'en eau assez profonde : sinon le corps
     * traverserait le fond.
     */
    private void transitionsCorps(long tick) {
        boolean eau = isInWater(), sub = estSubmerge();
        boolean calme = attaque == null && tick >= immobileJusqua;
        if (eau && calme) {
            if (sub && !etaitSubmerge && surfaceTicks > 40 && plongeeVoulue && profondeurSous() >= 4) {
                triggerAnim("ambiance", "plonge");
            } else if (!sub && etaitSubmerge && submergeTicks > 40 && profondeurSous() >= 3) {
                triggerAnim("ambiance", "remonte_surface");
            }
        }
        submergeTicks = sub ? submergeTicks + 1 : 0;
        surfaceTicks = sub ? 0 : surfaceTicks + 1;
        etaitSubmerge = sub;
        // entree dans l'eau en tombant de haut, ou en pleine course vers l'eau profonde
        // (l'entree calme, au pas, reste a la locomotion : « entree_eau »)
        if (eau && !etaitDansEau && calme) {
            Allure a = allure();
            if (hauteurChute >= 4) {
                triggerAnim("ambiance", "plongeon_hauteur");
            } else if ((a == Allure.COURSE || a == Allure.CHARGE || a == Allure.NAGE_RAPIDE) && profondeurSous() >= 4) {
                triggerAnim("ambiance", "plongeon_rapide");
            }
        }
        // sortie de l'eau : il se redresse en prenant pied, puis s'ebroue une fois sur la berge
        if (eau) {
            dansEauTicks++;
            horsEauTicks = 0;
            eauQuittee = Math.max(eauQuittee * 0.98, profondeurSous());
            // (eauQuittee : profondeur recente, qui s'efface doucement en eau peu profonde)
            if (onGround() && !sub && eauQuittee >= 4 && calme && allure() != Allure.COURSE) {
                triggerAnim("ambiance", "sortie_eau_terre_redressement");
                eauQuittee = 0;
            }
        } else {
            horsEauTicks++;
            if (horsEauTicks == 12 && dansEauTicks > 60 && onGround() && calme && allure() != Allure.COURSE
                    && allure() != Allure.CHARGE) {
                triggerAnim("ambiance", "secoue_eau");
            }
            if (horsEauTicks > 12) {
                dansEauTicks = 0;
                eauQuittee = 0;
            }
        }
        etaitDansEau = eau;
        // saut (impulsion vers le haut en quittant le sol) et reception d'une chute
        if (!onGround()) {
            hauteurChute = Math.max(hauteurChute, fallDistance);
            if (etaitAuSol && !eau && getDeltaMovement().y > 0.25 && calme && tick >= prochainSaut) {
                triggerAnim("ambiance", "saut");
                prochainSaut = tick + 20;
            }
        } else {
            if (!etaitAuSol && hauteurChute >= 3 && !eau && calme) {
                triggerAnim("ambiance", "attaque_saut_sol_ror");    // la reception, griffes en avant
            }
            hauteurChute = 0;
        }
        etaitAuSol = onGround();
    }

    @Override
    public void tick() {
        super.tick();
        montee = montee * 0.8 + (getY() - yo) * 0.2;       // les deux cotes : l'animation d'escalade
    }

    // ================================================================== attaques

    private static int premierImpact(Variante v) {
        return v.impacts().length == 0 ? 0 : v.impacts()[0];
    }

    /**
     * L'animation d'une attaque depend du terrain : depuis l'eau il jaillit, bondit sur la
     * berge ou happe un bateau ; les griffes partent du cote de la cible. Impacts mesures sur
     * chaque animation (fermeture de la machoire, bras au plus rapide), comme ceux du repertoire.
     */
    private Variante variante(Attaque a, LivingEntity cible) {
        boolean eau = isInWater();
        Vec3 avant = Instantane.vec3(Instantane.avant(yBodyRot));
        switch (a) {
            case MORSURE, MORSURE_LATERALE -> {
                if (eau && cible != null) {
                    if (cible.getVehicle() instanceof net.minecraft.world.entity.vehicle.Boat) {
                        return new Variante("dash_morsure_bateau", 44, new int[]{20}, 3.0);
                    }
                    if (!cible.isInWater()) {
                        if (cible.getY() - getY() > 3.0) {
                            return new Variante("saut_attaque_hors_eau", 64, new int[]{32}, 2.0);   // sur un ponton
                        }
                        return estSubmerge() ? new Variante("bond_hors_eau_ror", 53, new int[]{34}, 3.0)
                                : new Variante("attaque_saut_eau_ror", 53, new int[]{34}, 3.0);     // sur la berge
                    }
                    if (tactiquePrecedente == Tactique.AFFUT_EAU) {
                        return new Variante("embuscade_jaillissement", 32, new int[]{21}, 1.5);
                    }
                }
            }
            case GRIFFES -> {
                if (cible != null) {
                    Vec3 v = cible.position().subtract(position());
                    double cote = avant.x * v.z - avant.z * v.x;            // > 0 : a sa droite
                    double lat = Math.abs(cote) / Math.max(1e-6, Math.hypot(v.x, v.z));
                    if (lat > 0.3) {
                        return new Variante(cote > 0 ? "coup_griffes_droit_ror" : "coup_griffes_gauche_ror", 40,
                                new int[]{17, 30}, 0);
                    }
                }
            }
            case BALAYAGE_QUEUE -> {
                if (eau) {
                    return new Variante("frappe_queue_eau", 38, new int[]{18}, 0);
                }
            }
            case RUGISSEMENT -> {
                if (eau) {
                    return new Variante("rugit_en_nageant_ror", 60, new int[]{10}, 0);
                }
            }
            default -> {
            }
        }
        return Variante.de(a);
    }

    private void demarrerAttaque(Attaque a, LivingEntity cible, fr.riviere.spinosaure.cerveau.Vec visee) {
        attaque = a;
        variante = variante(a, cible);
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
            triggerAnim("action", variante.animation());   // la charge est une allure, pas une action
        }
        if (a == Attaque.RUGISSEMENT) {
            playSound(SoundEvents.RAVAGER_ROAR, 4.0F, 0.55F);
        }
        dernierCombat = level().getGameTime();
    }

    private void tickAttaque() {
        if (attaque == null) {
            return;
        }
        attaqueTick++;
        for (int impact : variante.impacts()) {
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
        if (attaqueTick >= variante.duree()) {
            attaque = null;
            cibleAttaque = null;
        }
    }

    private void frapper(Attaque a) {
        Vec3 avant = Instantane.vec3(Instantane.avant(yBodyRot));
        switch (a) {
            case MORSURE, MORSURE_LATERALE, BOND, SAISIE -> playSound(SoundEvents.RAVAGER_ATTACK, 2.0F, 0.7F);
            case BALAYAGE_QUEUE -> playSound(SoundEvents.PLAYER_ATTACK_SWEEP, 2.5F, 0.5F);
            case GRIFFES -> playSound(SoundEvents.PLAYER_ATTACK_STRONG, 2.0F, 0.6F);
            default -> {
            }
        }
        switch (a) {
            case MORSURE, MORSURE_LATERALE, BOND -> {
                LivingEntity v = meilleurDansCone(avant, reglages.porteeMorsure + variante.allonge(),
                        a == Attaque.MORSURE_LATERALE ? 120 : 70);
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
                } else if (v != null) {
                    blesser(v, a.degats * 2.5, 0.4);              // une creature : il la broie, sans la porter
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
        boolean envie = v.isAlive();
        if (v.hurt(damageSources().mobAttack(this), degats) && recul > 0) {
            Vec3 dir = v.position().subtract(position()).multiply(1, 0, 1).normalize();
            v.knockback(recul, -dir.x, -dir.z);
        }
        if (envie && v.isDeadOrDying() && !(v instanceof Player)) {
            // il a tue une creature : il la mangera (le cerveau decide s'il est derange) ; une
            // grosse proie merite le rugissement de victoire
            evenements.add(new Evenement.Proie(Instantane.vec(v.position())));
            agresseurs.remove(v.getUUID());
            if (v.getMaxHealth() >= 20) {
                rugirVictoire = true;
            }
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

    // ================================================================== soins

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

    /** Tactiques de combat (la traque, l'observation et la filature n'en sont pas). */
    private static boolean enCombat(Tactique t) {
        return switch (t) {
            case ENGAGEMENT, CONTOURNEMENT, MAINTIEN, ACCULE, REPLI, REGENERATION, ESQUIVE_TIR, DISPARITION -> true;
            default -> false;
        };
    }

    /** Tactiques ou il est silencieux : il chasse, observe, file, attend ou s'efface. */
    private static boolean silencieux(Tactique t) {
        return switch (t) {
            case TRAQUE, FIGE, AFFUT_EAU, OBSERVATION, FILATURE, DISPARITION -> true;
            default -> false;
        };
    }

    /**
     * Signes de presence pendant la filature et l'observation : de temps en temps une
     * respiration grave, qui vient de SA position (on l'entend dans son dos, pas a l'ecran).
     */
    private void presence(long tick) {
        Tactique t = decision.tactique();
        if ((t == Tactique.FILATURE || t == Tactique.OBSERVATION) && tick >= prochainePresence) {
            if (prochainePresence > 0) {
                playSound(SoundEvents.RAVAGER_AMBIENT, 0.9F, 0.42F + getRandom().nextFloat() * 0.06F);
            }
            prochainePresence = tick + 900 + getRandom().nextInt(900);        // 45 a 90 s
        }
    }

    // ================================================================== animations

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controleurs) {
        // ordre = priorite croissante : une attaque recouvre une animation d'ambiance
        controleurs.add(new AnimationController<>(this, "mouvement", 5, this::mouvement));

        // tout nom demande doit etre enregistre ici, sinon GeckoLib l'ignore sans rien dire
        // (verifie par AnimationsTest)
        AnimationController<SpinosaureEntity> ambiance = new AnimationController<>(this, "ambiance", 5, e -> PlayState.STOP);
        for (String nom : Animations.AMBIANCES) {
            ambiance.triggerableAnim(nom, RawAnimation.begin().thenPlay(PREFIXE + nom));
        }
        controleurs.add(ambiance);

        AnimationController<SpinosaureEntity> action = new AnimationController<>(this, "action", 3, e -> PlayState.STOP);
        for (String nom : Animations.ACTIONS) {
            action.triggerableAnim(nom, RawAnimation.begin().thenPlay(PREFIXE + nom));
        }
        controleurs.add(action);
    }

    private PlayState mouvement(AnimationState<SpinosaureEntity> etat) {
        double v = Math.hypot(getX() - xo, getZ() - zo) * 20.0;          // blocs/s reels
        double lacet = Mth.wrapDegrees(yBodyRot - yBodyRotO);             // degres/tick, + = a droite
        double e = fr.riviere.spinosaure.SpinosaureMod.ECHELLE;
        Tactique t = tactique();
        if (t != tactiqueVue) {
            tactiqueVue = t;
            tactiqueVueDepuis = tickCount;
        }
        String nom;
        double nominale = 0, accelMax = 2.2;
        if (isDeadOrDying()) {
            return etat.setAndContinue(RawAnimation.begin().thenPlayAndHold(PREFIXE + (isInWater() ? "mort_eau" : "mort")));
        }
        if (isInWater() && onGround() && !estSubmerge()) {
            // pieds au fond, eau peu profonde : il y marche (pas de nage sur place)
            if (v > 0.25) {
                nom = "marche_eau_peu_profonde";
                nominale = EAU_NOMINALE;
            } else {
                // pieds sur le fond : l'affut aquatique abaisse tout le modele de 1,45 bloc (fait
                // pour flotter yeux au ras de l'eau) et enfoncait les pattes dans le sol ; debout,
                // il se tapit comme a terre
                nom = t == Tactique.AFFUT_EAU ? "fige_en_traque" : "repos";
            }
        } else if (isInWater()) {
            // (nage_derive_ror, portee de ROR ou le spino flotte a la verticale, cabre le corps
            //  de 35 degres queue pendante : elle se lisait comme une escalade. Retiree.)
            if (v > 0.3) {
                if (t == Tactique.AFFUT_EAU && !estSubmerge()) {
                    nom = "traque_eau_affleurante";                         // seuls les yeux depassent
                } else {
                    nom = allure() == Allure.NAGE_RAPIDE ? "nage_rapide_ror" : (estSubmerge() ? "nage_sous_eau" : "nage_surface");
                }
            } else if (t == Tactique.AFFUT_EAU) {
                nom = "affut_eau";
            } else {
                nom = "nage_surface";                                   // barbote lentement sur place
                etat.getController().setAnimationSpeed(0.45);
                return etat.setAndContinue(RawAnimation.begin().thenLoop(PREFIXE + nom));
            }
        } else if (!onGround() && getDeltaMovement().y < -0.35) {
            nom = "chute";
        } else if (v < 0.25 && Math.abs(lacet) > 1.5) {
            nom = "tourne_sur_place";                                     // pivot sur place
        } else if (v > 3.0 && Math.abs(lacet) > 2.5) {
            nom = lacet > 0 ? "virage_serre_droite" : "virage_serre_gauche";   // penche dans le virage
            nominale = VIRAGE_NOMINALE;
        } else if (v > 0.25 && !getPassengers().isEmpty()) {
            nom = "maintien_joueur";                                      // il emporte sa proie
            nominale = MAINTIEN_NOMINALE;
        } else if (v > 0.25 && montee > 0.05 && onGround()) {
            nom = "grimpe";                                               // pente raide, marches de terrain
            nominale = GRIMPE_NOMINALE;
        } else if (v > 0.25) {
            boolean combat = t == Tactique.ENGAGEMENT || t == Tactique.ACCULE || t == Tactique.CONTOURNEMENT;
            switch (allure()) {
                case MENACE -> { nom = "avance_menacante"; nominale = MENACE_NOMINALE; accelMax = 3.0; }
                case FEUTREE -> {
                    if (t == Tactique.OBSERVATION || t == Tactique.FILATURE || t == Tactique.TRAQUE) {
                        nom = "marche_observation";                       // tete fixe vers sa proie
                        nominale = OBSERVATION_NOMINALE;
                    } else {
                        nom = "marche_feutree";
                        nominale = FEUTREE_NOMINALE;
                    }
                }
                case COURSE -> {
                    if (combat && tickCount - tactiqueVueDepuis < 64) {
                        nom = "hurle_en_courant";                         // il jaillit en hurlant
                        nominale = COURSE_NOMINALE;
                    } else if (combat && entityData.get(DISTANCE_CIBLE) < 12) {
                        nom = "ruee_griffes_ror";                         // les derniers metres, griffes en avant
                        nominale = RUEE_NOMINALE;
                    } else {
                        nom = "course";
                        nominale = COURSE_NOMINALE;
                    }
                }
                case CHARGE -> { nom = "charge"; nominale = CHARGE_NOMINALE; }
                default -> {
                    boolean blesse = getHealth() / getMaxHealth() < reglages.seuilRepli;
                    nom = blesse ? "marche_boiteuse" : "marche";
                    nominale = blesse ? BOITEUSE_NOMINALE : MARCHE_NOMINALE;
                }
            }
        } else {
            nom = switch (t) {
                case SOMMEIL -> "dort";
                case REPOS -> "assis_ror";
                case FIGE, FILATURE -> "fige_en_traque";
                case OBSERVATION -> "respiration_lourde";                 // il te regarde en respirant
                case TRAQUE -> "traque_lente";
                default -> getHealth() / getMaxHealth() < reglages.seuilRepli ? "respiration_lourde" : "repos";
            };
        }
        etat.getController().setAnimationSpeed(nominale > 0 ? Mth.clamp(v / (nominale * e), 0.5, accelMax) : 1.0);
        return etat.setAndContinue(RawAnimation.begin().thenLoop(PREFIXE + nom));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }
}
