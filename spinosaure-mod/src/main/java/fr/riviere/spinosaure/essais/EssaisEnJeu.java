package fr.riviere.spinosaure.essais;

import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import fr.riviere.spinosaure.SpinosaureMod;
import fr.riviere.spinosaure.cerveau.Decision.Tactique;
import fr.riviere.spinosaure.entite.SpinosaureEntity;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Essais dans un vrai serveur Minecraft (GameTest, sans ecran) : on pose une arene de jungle
 * (sol, piliers-troncs pour se couvrir, bassin de 7 de fond), un spinosaure et de faux joueurs
 * en survie, et on journalise sa tactique, son allure et sa distance au joueur chaque seconde.
 *
 * Lancer : {@code ./gradlew runGameTestServer}. Les lignes du journal commencent par [ESSAI].
 * Ces essais ne sont charges que par le serveur de test (espace de noms active par la
 * propriete forge.enabledGameTestNamespaces) : en jeu normal, ils n'existent pas.
 */
@GameTestHolder(SpinosaureMod.MODID)
@PrefixGameTestTemplate(false)
public final class EssaisEnJeu {

    private static final Logger LOG = LogUtils.getLogger();
    /** L'herbe de l'arene est a y = 7 : on se tient a y = 8. */
    private static final int SOL = 8;

    private EssaisEnJeu() {
    }

    // ================================================================== scenarios

    /** Seul, sans joueur : il doit vivre, penser et se deplacer (errance). */
    @GameTest(template = "arene", timeoutTicks = 500, batch = "a_seul")
    public static void seul(GameTestHelper h) {
        Scene s = new Scene(h, "seul");
        SpinosaureEntity spino = s.spino(32, 32);
        Vec3 depart = spino.position();
        h.onEachTick(() -> {
            s.journal(spino, null);
            if (h.getTick() >= 440) {
                double bouge = spino.position().distanceTo(depart);
                s.resume(spino, null, "deplacement %.1f blocs".formatted(bouge));
                if (!spino.isAlive()) {
                    h.fail("mort");
                }
                if (bouge < 2) {
                    h.fail("immobile : %.1f blocs en 22 s".formatted(bouge));
                }
                s.fin();
                h.succeed();
            }
        });
    }

    /**
     * Un joueur immobile, dos tourne. Attendu : observation de loin, filature dans son dos,
     * puis frappe a l'ouverture (dos tourne, isole, a moins de 14 blocs) apres ~90 s.
     */
    @GameTest(template = "arene", timeoutTicks = 4200, batch = "b_dos_tourne")
    public static void dosTourne(GameTestHelper h) {
        Scene s = new Scene(h, "dos_tourne");
        ServerPlayer j = s.joueur("proie", 32, 12, 180F);           // regarde vers le nord (-z)
        SpinosaureEntity spino = s.spino(32, 56);                   // 44 blocs derriere lui
        h.onEachTick(() -> {
            s.journal(spino, j);
            if (spino.attaqueActive() != null || j.getHealth() < j.getMaxHealth()) {
                s.resume(spino, j, "FRAPPE a %.0f s, attaque %s".formatted(h.getTick() / 20.0, spino.attaqueActive()));
                s.fin();
                h.succeed();
            } else if (h.getTick() >= 4100) {
                s.resume(spino, j, "aucune frappe en 205 s");
                s.fin();
                h.fail("pas de frappe en 205 s");
            }
        });
    }

    /**
     * Le joueur le fixe du regard a 20 blocs, en le suivant des yeux. Attendu : il ne s'approche
     * pas pour frapper ; il disparait (fuite ou plongee) ou se fige.
     */
    @GameTest(template = "arene", timeoutTicks = 1400, batch = "c_regard")
    public static void regard(GameTestHelper h) {
        Scene s = new Scene(h, "regard");
        ServerPlayer j = s.joueur("guetteur", 32, 12, 0F);
        SpinosaureEntity spino = s.spino(32, 34);
        h.onEachTick(() -> {
            regarder(j, spino);
            s.journal(spino, j);
            if (spino.attaqueActive() != null) {
                s.resume(spino, j, "a attaque alors qu'on le fixait");
                s.fin();
                h.fail("attaque sous le regard");
            }
            if (h.getTick() >= 1300) {
                boolean esquive = s.vu(Tactique.DISPARITION) || s.vu(Tactique.FIGE) || s.distanceMax > s.distanceDepart + 6;
                s.resume(spino, j, esquive ? "il esquive le regard" : "il n'a pas reagi au regard");
                s.fin();
                if (!esquive) {
                    h.fail("aucune reaction au regard");
                }
                h.succeed();
            }
        });
    }

    /** Le joueur nage dans le bassin : c'est son domaine. Attendu : approche et saisie ou attaque. */
    @GameTest(template = "arene", timeoutTicks = 1600, batch = "d_eau")
    public static void eau(GameTestHelper h) {
        Scene s = new Scene(h, "eau");
        ServerPlayer j = s.joueurA("nageur", 52, 5, 52, 90F);
        SpinosaureEntity spino = s.spino(20, 52);
        h.onEachTick(() -> {
            s.journal(spino, j);
            if (spino.attaqueActive() != null || j.getVehicle() == spino || j.getHealth() < j.getMaxHealth()) {
                s.resume(spino, j, "ATTAQUE DANS L'EAU a %.0f s (%s)".formatted(h.getTick() / 20.0,
                        j.getVehicle() == spino ? "saisi" : String.valueOf(spino.attaqueActive())));
                s.fin();
                h.succeed();
            } else if (h.getTick() >= 1500) {
                s.resume(spino, j, "rien en 75 s");
                s.fin();
                h.fail("pas d'attaque dans l'eau en 75 s");
            }
        });
    }

    /**
     * Trois joueurs groupes ; au bout de 20 s, l'un s'ecarte seul et tourne le dos. Attendu : il
     * reste a distance du groupe et finit par viser celui qui s'est isole.
     */
    @GameTest(template = "arene", timeoutTicks = 4600, batch = "e_groupe")
    public static void groupe(GameTestHelper h) {
        Scene s = new Scene(h, "groupe");
        ServerPlayer a = s.joueur("groupe_a", 30, 14, 180F);
        ServerPlayer b = s.joueur("groupe_b", 34, 14, 180F);
        ServerPlayer isole = s.joueur("isole", 32, 16, 180F);
        SpinosaureEntity spino = s.spino(32, 54);
        List<ServerPlayer> groupe = List.of(a, b);
        h.onEachTick(() -> {
            long t = h.getTick();
            if (t == 400) {
                Vec3 p = h.absoluteVec(new Vec3(14.5, SOL, 34.5));  // il s'ecarte : 27 blocs du groupe, a portee du spinosaure
                isole.moveTo(p.x, p.y, p.z, 180F, 0F);
                isole.setYHeadRot(180F);
                isole.yHeadRotO = 180F;
            }
            s.journal(spino, isole);
            if (spino.attaqueActive() != null) {
                UUID c = spino.cibleActuelle();
                boolean surIsole = isole.getUUID().equals(c);
                s.resume(spino, isole, "FRAPPE a %.0f s sur %s".formatted(t / 20.0,
                        surIsole ? "l'isole" : groupe.stream().anyMatch(g -> g.getUUID().equals(c)) ? "le groupe" : "?"));
                s.fin();
                if (!surIsole && t < 2400) {
                    h.fail("a frappe le groupe avant 2 min au lieu de l'isole");
                }
                h.succeed();
            } else if (t >= 4500) {
                s.resume(spino, isole, "aucune frappe en 225 s");
                s.fin();
                h.fail("pas de frappe en 225 s");
            }
        });
    }

    // ================================================================== outils

    private static void regarder(ServerPlayer j, Entity cible) {
        Vec3 d = cible.position().add(0, 2.5, 0).subtract(j.getEyePosition());
        float yaw = (float) (Math.toDegrees(Math.atan2(-d.x, d.z)));
        float pitch = (float) (-Math.toDegrees(Math.atan2(d.y, Math.hypot(d.x, d.z))));
        j.setYRot(yaw);
        j.setXRot(pitch);
        j.setYHeadRot(yaw);
        j.yHeadRotO = yaw;
    }

    /** Un scenario : ses faux joueurs, son journal et son bilan. */
    private static final class Scene {
        final GameTestHelper h;
        final String nom;
        final List<ServerPlayer> joueurs = new ArrayList<>();
        final Map<Tactique, Integer> temps = new EnumMap<>(Tactique.class);
        final StringBuilder frise = new StringBuilder();
        Tactique derniere;
        double distanceDepart = -1, distanceMin = 1e9, distanceMax = 0;

        Scene(GameTestHelper h, String nom) {
            this.h = h;
            this.nom = nom;
            nettoyer(h.getLevel());
            MinecraftServer serveur = h.getLevel().getServer();
            BlockPos a = h.absolutePos(new BlockPos(0, 0, 0));
            BlockPos b = h.absolutePos(new BlockPos(63, 19, 63));
            CommandSourceStack src = serveur.createCommandSourceStack().withSuppressedOutput().withLevel(h.getLevel());
            // /fillbiome est limite a 32 768 blocs par appel : l'arene (64 x 20 x 64) se fait par tranches
            int x0 = Math.min(a.getX(), b.getX()), x1 = Math.max(a.getX(), b.getX());
            int y0 = Math.min(a.getY(), b.getY()), y1 = Math.max(a.getY(), b.getY());
            int z0 = Math.min(a.getZ(), b.getZ()), z1 = Math.max(a.getZ(), b.getZ());
            int ok = 0;
            for (int z = z0; z <= z1; z += 16) {
                ok += serveur.getCommands().performPrefixedCommand(src, "fillbiome %d %d %d %d %d %d minecraft:jungle".formatted(
                        x0, y0, z, x1, y1, Math.min(z + 15, z1)));
            }
            boolean jungle = h.getLevel().getBiome(h.absolutePos(new BlockPos(32, SOL, 32)))
                    .is(net.minecraft.tags.BiomeTags.IS_JUNGLE);
            LOG.info("[ESSAI] ===== {} ===== (biome jungle pose : {}, commandes {})", nom, jungle, ok);
            if (!jungle) {
                h.fail("l'arene n'est pas en jungle");
            }
        }

        SpinosaureEntity spino(int x, int z) {
            SpinosaureEntity e = h.spawn(SpinosaureMod.SPINOSAURE.get(), new BlockPos(x, SOL, z));
            e.addTag("debug");
            return e;
        }

        ServerPlayer joueur(String n, double x, double z, float yaw) {
            return joueurA(n, x, SOL, z, yaw);
        }

        ServerPlayer joueurA(String n, double x, double y, double z, float yaw) {
            ServerLevel niveau = h.getLevel();
            FakePlayer fp = new FakePlayer(niveau, new GameProfile(UUID.randomUUID(), ("t_" + n).substring(0, Math.min(16, n.length() + 2))));
            Vec3 p = h.absoluteVec(new Vec3(x + 0.5, y, z + 0.5));
            fp.moveTo(p.x, p.y, p.z, yaw, 0F);
            fp.setYHeadRot(yaw);
            fp.yHeadRotO = yaw;
            niveau.addNewPlayer(fp);
            joueurs.add(fp);
            return fp;
        }

        void journal(SpinosaureEntity s, ServerPlayer j) {
            long t = h.getTick();
            // un faux joueur n'est pas anime par le serveur : on met a jour son etat (dans l'eau, au sol)
            for (ServerPlayer p : joueurs) {
                if (p.isAlive() && p.getVehicle() == null) {
                    p.baseTick();
                }
            }
            Tactique tac = s.tactique();
            temps.merge(tac, 1, Integer::sum);
            if (j != null) {
                double d = s.distanceTo(j);
                if (distanceDepart < 0) {
                    distanceDepart = d;
                }
                distanceMin = Math.min(distanceMin, d);
                distanceMax = Math.max(distanceMax, d);
            }
            if (tac != derniere) {
                frise.append(String.format(" %.0fs:%s", t / 20.0, tac));
                derniere = tac;
            }
            if (t % 20 == 0) {
                Vec3 o = h.absoluteVec(Vec3.ZERO);
                var dest = s.destinationDecision();
                LOG.info("[ESSAI] {} t={}s tactique={} allure={} dist={} eau={} attaque={} pos=({},{}) but={} nav={} v={} raison={}",
                        nom, t / 20, tac, s.allure(), j == null ? "-" : "%.1f".formatted(s.distanceTo(j)), s.isInWater(),
                        s.attaqueActive(), "%.0f".formatted(s.getX() - o.x), "%.0f".formatted(s.getZ() - o.z),
                        dest == null ? "-" : "(%.0f,%.0f)".formatted(dest.x() - o.x, dest.z() - o.z),
                        s.getNavigation().isDone() ? "fini" : "en_cours",
                        "%.2f".formatted(s.getDeltaMovement().horizontalDistance()), s.raisonDecision());
            }
        }

        boolean vu(Tactique t) {
            return temps.containsKey(t);
        }

        void resume(SpinosaureEntity s, ServerPlayer j, String verdict) {
            StringBuilder parts = new StringBuilder();
            long total = Math.max(1, temps.values().stream().mapToLong(Integer::longValue).sum());
            temps.forEach((k, v) -> parts.append(String.format(" %s=%.0f%%", k, 100.0 * v / total)));
            LOG.info("[ESSAI] RESUME {} : {} | dist depart={} min={} max={} | temps :{} | frise :{}", nom, verdict,
                    "%.1f".formatted(distanceDepart), "%.1f".formatted(distanceMin), "%.1f".formatted(distanceMax),
                    parts, frise);
        }

        void fin() {
            for (ServerPlayer p : joueurs) {
                h.getLevel().removePlayerImmediately(p, Entity.RemovalReason.DISCARDED);
            }
        }

        private static void nettoyer(ServerLevel niveau) {
            for (ServerPlayer p : new ArrayList<>(niveau.players())) {
                if (p instanceof FakePlayer) {
                    niveau.removePlayerImmediately(p, Entity.RemovalReason.DISCARDED);
                }
            }
        }
    }
}
