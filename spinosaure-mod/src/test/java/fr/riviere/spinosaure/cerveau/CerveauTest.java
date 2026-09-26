package fr.riviere.spinosaure.cerveau;

import fr.riviere.spinosaure.cerveau.Decision.Allure;
import fr.riviere.spinosaure.cerveau.Decision.Tactique;
import fr.riviere.spinosaure.cerveau.Joueur.Arme;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Scenarios. Le spinosaure est a l'origine, regard vers -Z (vers le nord), sauf mention
 * contraire. j(...) cree un joueur qui REGARDE le spinosaure ; avec(p, "detourne") un
 * joueur qui lui tourne le dos.
 */
class CerveauTest {

    static final Vec NORD = new Vec(0, 0, -1);
    static final UUID A = new UUID(0, 1), B = new UUID(0, 2), C = new UUID(0, 3), D = new UUID(0, 4);

    // ------------------------------------------------------------ fabriques

    static Soi soi(long tick) {
        return new Soi(Vec.ZERO, NORD, 1.0, 300, false, false, null, false, tick);
    }

    static Soi soi(long tick, double sante, Vec eau, boolean dansEau, boolean submerge) {
        return new Soi(Vec.ZERO, NORD, sante, 300, dansEau, submerge, eau, false, tick);
    }

    static Joueur j(UUID id, double x, double z) {
        return new Joueur(id, new Vec(x, 0, z), versOrigine(x, z), 1.0, 10, Arme.MELEE,
                false, false, false, false, true, true, Vec.ZERO, false);
    }

    static Vec versOrigine(double x, double z) {
        return new Vec(-x, 0, -z).unitaire();
    }

    static Joueur avec(Joueur p, String quoi) {
        return switch (quoi) {
            case "bouclier" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    true, p.accroupi(), p.sprinte(), p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), p.inoffensif());
            case "eau" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    p.bouclierLeve(), p.accroupi(), p.sprinte(), true, p.visible(), p.atteignable(), p.vitesse(), p.inoffensif());
            case "perche" -> new Joueur(p.id(), p.pos().plus(new Vec(0, 6, 0)), p.regard(), p.sante(), p.armure(),
                    Arme.DISTANCE, false, false, false, false, true, false, p.vitesse(), false);
            case "accroupi" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    false, true, false, p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), p.inoffensif());
            case "sprint" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    false, false, true, p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), p.inoffensif());
            case "detourne" -> new Joueur(p.id(), p.pos(), p.regard().fois(-1), p.sante(), p.armure(), p.arme(),
                    p.bouclierLeve(), p.accroupi(), p.sprinte(), p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), p.inoffensif());
            case "cache" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    p.bouclierLeve(), p.accroupi(), p.sprinte(), p.dansEau(), false, p.atteignable(), p.vitesse(), p.inoffensif());
            case "blesse" -> new Joueur(p.id(), p.pos(), p.regard(), 0.3, 2, p.arme(),
                    p.bouclierLeve(), p.accroupi(), p.sprinte(), p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), p.inoffensif());
            default -> throw new IllegalArgumentException(quoi);
        };
    }

    static Cerveau cerveau() {
        return new Cerveau(Reglages.defaut(), 42);
    }

    static List<Evenement> coups(UUID source, double montant, boolean distance) {
        return List.of(new Evenement.Degats(source, montant, distance));
    }

    /** Fait penser le cerveau tous les 4 ticks de `debut` a `fin`, jusqu'a `stop` s'il est vrai. */
    static Decision jusqua(Cerveau c, List<Joueur> ps, long debut, long fin, java.util.function.Predicate<Decision> stop) {
        Decision d = null;
        for (long t = debut; t <= fin; t += 4) {
            d = c.penser(soi(t), ps, List.of());
            if (stop.test(d)) {
                return d;
            }
        }
        return d;
    }

    static Joueur court(Joueur p, Vec vitesse) {
        return new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(), p.bouclierLeve(),
                p.accroupi(), true, p.dansEau(), p.visible(), p.atteignable(), vitesse, false);
    }

    static Joueur creatif(Joueur p) {
        return new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(), false, false, false,
                p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), true);
    }

    static boolean frappe(Decision d) {
        return d.tactique() == Tactique.ENGAGEMENT;
    }

    // ------------------------------------------------------------ perception

    @Test
    void unJoueurAccroupiDansLeDosPasseInapercu() {
        Reglages r = Reglages.defaut();
        Joueur furtif = avec(avec(j(A, 0, 10), "accroupi"), "detourne");
        assertFalse(Perception.percoit(soi(0), furtif, r));
        Joueur bruyant = avec(j(A, 0, 20), "sprint");
        assertTrue(Perception.percoit(soi(0), bruyant, r), "un sprint s'entend a 24 blocs");
    }

    // ------------------------------------------------------------ horreur : la montee de tension

    @Test
    void premiereDetection_ilObserveEtTourneLaTete() {
        Cerveau c = cerveau();
        Decision d = c.penser(soi(0), List.of(avec(j(A, 0, -30), "detourne")), List.of());
        assertEquals(Tactique.OBSERVATION, d.tactique(), d.raison());
        assertNull(d.attaque());
        assertNotNull(d.animation(), "il tourne brusquement la tete vers sa proie");
    }

    @Test
    void apres30sIlFileSaProieParDerriere() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(A, 0, -30), "detourne"));   // A regarde vers le nord
        Decision d = jusqua(c, ps, 0, 900, x -> x.tactique() == Tactique.FILATURE);
        assertEquals(Tactique.FILATURE, d.tactique(), d.raison());
        // derriere A par rapport a SON regard : 16 blocs au sud de lui
        assertEquals(-14, d.destination().z(), 0.5, "poste dans son dos : " + d.destination());
        assertNotEquals(Allure.COURSE, d.allure(), "en silence");
    }

    @Test
    void phase3_ilFrappeQuandLaProieIsoleeTourneLeDos() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(C, 0, -13), "detourne"));
        Decision d = jusqua(c, ps, 0, 2400, CerveauTest::frappe);
        assertTrue(frappe(d), "jamais frappe : " + d.raison());
        assertEquals(Attaque.CHARGE, d.attaque(), "ligne degagee : charge surprise");
        assertTrue(d.destination() != null);
    }

    @Test
    void phase3_mais_ilNeFrappePasSiOnLeRegarde() {
        Cerveau c = cerveau();
        Decision d = jusqua(c, List.of(avec(j(C, 0, -40), "detourne")), 0, 2000, x -> false);  // tension
        d = c.penser(soi(2004), List.of(j(C, 0, -13)), List.of());                            // il se retourne
        assertEquals(Tactique.DISPARITION, d.tactique(), "vu de pres : " + d.raison());
    }

    @Test
    void frappeEclair_deuxCoupsPuisIlDisparait() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(C, 0, -12), "detourne"));
        long debut = -1;
        Decision d = null;
        for (long t = 0; t <= 2400 && debut < 0; t += 4) {
            d = c.penser(soi(t), ps, List.of());
            if (frappe(d)) {
                debut = t;
            }
        }
        assertTrue(debut >= 0, "jamais frappe");
        int attaques = d.attaque() != null ? 1 : 0;
        Decision fin = null;
        for (long t = debut + 4; t < debut + 200; t += 4) {
            fin = c.penser(soi(t), ps, List.of());
            if (fin.attaque() != null) {
                attaques++;
            }
            if (fin.tactique() == Tactique.DISPARITION) {
                break;
            }
        }
        assertEquals(Tactique.DISPARITION, fin.tactique(), "il ne reste pas se battre : " + fin.raison());
        assertTrue(attaques <= 2, attaques + " attaques");
        assertEquals(Allure.COURSE, fin.allure());
        assertTrue(fin.destination().distanceH(new Vec(0, 0, -12)) > 20, "il s'eloigne de sa proie");
    }

    @Test
    void blesseDeLoin_ilSeDerobe() {
        Cerveau c = cerveau();
        Decision d = c.penser(soi(0), List.of(j(A, 0, -20)), coups(A, 6, false));
        assertEquals(Tactique.DISPARITION, d.tactique(), d.raison());
        assertNull(d.attaque());
    }

    @Test
    void vuDePres_ilDisparait_vuDeLoin_ilSeFigeEtSoutientLeRegard() {
        Cerveau c = cerveau();
        assertEquals(Tactique.DISPARITION, c.penser(soi(0), List.of(j(A, 0, -15)), List.of()).tactique());

        Cerveau loin = cerveau();
        loin.penser(soi(0), List.of(avec(j(A, 0, -30), "detourne")), List.of());
        Decision f = loin.penser(soi(4), List.of(j(A, 0, -30)), List.of());
        assertEquals(Tactique.FIGE, f.tactique());
        Decision fin = jusqua(loin, List.of(j(A, 0, -30)), 8, 200, x -> x.tactique() != Tactique.FIGE);
        assertEquals(Tactique.DISPARITION, fin.tactique(), "soutient le regard puis s'efface");
    }

    @Test
    void unGroupe_ilResteADistanceEtAttendQuUnJoueurSIsole() {
        Cerveau c = cerveau();
        List<Joueur> groupe = List.of(avec(j(A, -3, -20), "detourne"), avec(j(B, 0, -21), "detourne"),
                avec(j(C, 3, -20), "detourne"));
        Decision d = jusqua(c, groupe, 0, 3000, CerveauTest::frappe);
        assertFalse(frappe(d), "il n'attaque pas un groupe");
        assertEquals(Tactique.OBSERVATION, d.tactique(), d.raison());

        // C s'ecarte du groupe, dos tourne, a 12 blocs : il frappe
        List<Joueur> ecart = List.of(avec(j(A, -30, -30), "detourne"), avec(j(B, -28, -32), "detourne"),
                avec(j(C, 0, -12), "detourne"));
        Decision e = jusqua(c, ecart, 3004, 3100, CerveauTest::frappe);
        assertTrue(frappe(e), e.raison());
        assertEquals(C, e.cible());
    }

    // ------------------------------------------------------------ choix de cible

    @Test
    void prefereLeJoueurIsoleAuGroupe() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, -3, -10), j(B, -1, -10), j(C, 14, -6));
        c.penser(soi(0), ps, List.of());
        Decision d = c.penser(soi(4), ps, List.of());
        assertEquals(C, d.cible(), d.raison());
    }

    @Test
    void neChangePasDeCibleAChaqueTick() {
        Cerveau c = cerveau();
        int changements = 0;
        UUID avant = null;
        for (int t = 0; t < 400; t++) {
            double e = Math.sin(t * 0.7) * 0.8;
            List<Joueur> ps = List.of(avec(j(A, -8, -30 + e), "detourne"), avec(j(B, 8, -30 - e), "detourne"));
            Decision d = c.penser(soi(t), ps, List.of());
            if (d.cible() != null && !d.cible().equals(avant)) {
                changements++;
                avant = d.cible();
            }
        }
        assertTrue(changements <= 2, "changements de cible : " + changements);
    }

    @Test
    void ignoreLeTireurPercheQuandUnAutreEstAtteignable() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(A, 0, -12), "perche"), j(B, 6, -9));
        Decision d = null;
        for (int t = 0; t < 60; t++) {
            d = c.penser(soi(t), ps, t % 20 == 0 ? coups(A, 4, true) : List.of());
        }
        assertEquals(B, d.cible(), d.raison());
    }

    @Test
    void seulUnTireurInatteignable_ilRompLaLigneDeTir() {
        Cerveau c = cerveau();
        Vec eau = new Vec(20, -2, 5);
        Joueur tireur = avec(j(A, 0, -12), "perche");
        Decision d = null;
        for (int t = 0; t < 60; t++) {
            d = c.penser(soi(t, 1.0, eau, false, false), List.of(tireur), t % 20 == 0 ? coups(A, 4, true) : List.of());
        }
        assertEquals(Tactique.ESQUIVE_TIR, d.tactique());
        assertEquals(eau, d.destination());
    }

    // ------------------------------------------------------------ riposte au contact

    @Test
    void encercleEtFrappe_balayageDeQueue() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, 0, -4), j(B, -2, 4), j(C, 2, 5));
        Decision d = c.penser(soi(0), ps, coups(B, 2, false));
        assertEquals(Attaque.BALAYAGE_QUEUE, d.attaque(), d.raison());
    }

    @Test
    void bouclierLeveAuContact_griffesPuisContournement() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(A, 0, -4), "bouclier"));
        Decision d1 = c.penser(soi(0), ps, coups(A, 1, false));
        assertEquals(Attaque.GRIFFES, d1.attaque(), "les griffes brisent le bouclier");
        Decision d2 = c.penser(soi(4), ps, List.of());
        assertEquals(Tactique.CONTOURNEMENT, d2.tactique(), d2.raison());
        assertTrue(Math.abs(d2.destination().x()) > 2, "destination laterale : " + d2.destination());
    }

    @Test
    void aPorteeIlTourneAutourAuLieuDePousserContreLeJoueur() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, 0, -5));
        c.penser(soi(0), ps, coups(A, 1, false));
        Decision d = c.penser(soi(4), ps, List.of());
        assertNull(d.attaque());
        double r = d.destination().distanceH(new Vec(0, 0, -5));
        assertTrue(r > 4 && r < 6, "sur un cercle autour du joueur : " + d.destination());
    }

    @Test
    void frappeAvecDesAlliesAuLoin_ilVientParLeCoteOppose() {
        Cerveau c = cerveau();
        // C isolee (allies a 20 blocs a l'ouest), bouclier leve : pas de charge, il s'approche
        List<Joueur> ps = List.of(avec(avec(j(C, 0, -12), "bouclier"), "detourne"), j(A, -20, -12), j(B, -20, -14));
        Decision d = jusqua(c, ps, 0, 2400, CerveauTest::frappe);
        assertTrue(frappe(d), d.raison());
        assertEquals(C, d.cible());
        assertTrue(d.destination().x() > 0, "il vient par l'est, les allies a l'ouest : " + d.destination());
        assertEquals(Allure.COURSE, d.allure(), "il court jusqu'a portee");
    }

    @Test
    void coupeLaRouteDUnJoueurQuiFuit() {
        Cerveau c = cerveau();
        Joueur fuyard = court(avec(j(C, 0, -12), "detourne"), new Vec(0.28, 0, 0));
        Decision d = jusqua(c, List.of(fuyard), 0, 2400, CerveauTest::frappe);
        assertTrue(frappe(d), d.raison());
        assertTrue(d.destination().x() > 3, "il vise devant le fuyard : " + d.destination());
    }

    // ------------------------------------------------------------ survie

    @Test
    void enInferioriteIlSeRepliePuisSeSoignePuisRevientEnAffut() {
        Cerveau c = cerveau();
        Vec eau = new Vec(0, -3, 25);
        List<Joueur> ps = List.of(j(A, 0, -5), j(B, 4, -5), j(C, -4, -5));
        c.penser(soi(0, 0.6, eau, false, false), ps, coups(A, 30, false));
        Decision d = c.penser(soi(10, 0.25, eau, false, false), ps, coups(B, 30, false));
        assertEquals(Tactique.REPLI, d.tactique(), d.raison());
        assertEquals(eau, d.destination());

        d = c.penser(soi(80, 0.3, eau, true, true), ps, List.of());
        assertEquals(Tactique.REGENERATION, d.tactique(), d.raison());

        List<Joueur> bord = List.of(avec(j(A, 0, -20), "eau"));
        d = c.penser(soi(900, 0.8, eau, true, true), bord, List.of());
        assertEquals(Tactique.AFFUT_EAU, d.tactique(), d.raison());
        assertEquals(A, d.cible());
    }

    @Test
    void sansEauEtPresqueMort_ilSeBatAccule() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, 0, -4), j(B, 3, -4));
        c.penser(soi(0, 0.5, null, false, false), ps, coups(A, 40, false));
        Decision d = c.penser(soi(5, 0.1, null, false, false), ps, coups(B, 40, false));
        assertEquals(Tactique.ACCULE, d.tactique(), d.raison());
    }

    @Test
    void seReplieVersUneEauQuiNeLObligePasATraverserLesJoueurs() {
        Cerveau c = cerveau();
        Vec eauDerriereEux = new Vec(0, -3, -22), eauLibre = new Vec(4, -3, 30);
        List<PointTerrain> terrain = List.of(new PointTerrain(eauDerriereEux, true, 6, -3, false),
                new PointTerrain(eauLibre, true, 6, -3, false));
        List<Joueur> ps = List.of(j(A, -2, -9), j(B, 2, -9), j(C, 0, -11));
        c.penser(new Soi(Vec.ZERO, NORD, 0.6, 300, false, false, null, false, 0, terrain), ps, coups(A, 30, false));
        Decision d = c.penser(new Soi(Vec.ZERO, NORD, 0.25, 300, false, false, null, false, 10, terrain), ps, coups(B, 30, false));
        assertEquals(Tactique.REPLI, d.tactique(), d.raison());
        assertEquals(eauLibre, d.destination());
    }

    // ------------------------------------------------------------ eau

    @Test
    void saisieDansLEauPuisLiberationParLesAllies() {
        Cerveau c = cerveau();
        Vec eau = new Vec(0, -3, -12);
        List<Joueur> ps = List.of(avec(j(A, 0, -4), "eau"), j(B, 6, 2));
        Decision d = c.penser(soi(0, 1, eau, true, false), ps, coups(A, 1, false));
        assertEquals(Attaque.SAISIE, d.attaque(), d.raison());

        c.priseEtablie(A, 10);
        d = c.penser(soi(11, 1, eau, true, false), ps, List.of());
        assertEquals(Tactique.MAINTIEN, d.tactique());
        assertEquals(eau, d.destination());
        d = c.penser(soi(20, 1, eau, true, false), ps, coups(B, 12, false));
        assertFalse(d.lacher());
        d = c.penser(soi(25, 1, eau, true, false), ps, coups(B, 10, false));
        assertTrue(d.lacher(), "22 degats des allies : il lache prise");
    }

    @Test
    void nageurLoinDansLEau_ilApprocheParEnDessous() {
        Cerveau c = cerveau();
        Decision d = c.penser(soi(0, 1, null, true, true), List.of(avec(avec(j(A, 0, -20), "eau"), "detourne")), List.of());
        assertEquals(Tactique.AFFUT_EAU, d.tactique(), d.raison());
        assertTrue(d.destination().y() < 0, "sous la surface");
    }

    // ------------------------------------------------------------ memoire, blocage, creatif

    @Test
    void perdDeVue_vaVoirLaDerniereTracePuisRenifle() {
        Cerveau c = cerveau();
        c.penser(soi(0), List.of(avec(j(A, 0, -20), "detourne")), List.of());
        Decision d = c.penser(soi(40), List.of(), List.of());
        assertEquals(Tactique.ENQUETE, d.tactique());
        assertEquals(new Vec(0, 0, -20), d.destination());
        Soi arrive = new Soi(new Vec(0, 0, -19), NORD, 1, 300, false, false, null, false, 200);
        assertEquals("renifle_piste_sol", c.penser(arrive, List.of(), List.of()).animation());
    }

    @Test
    void blesseDeLoin_finitDeSEffacerAvantDAllerVoir() {
        Cerveau c = cerveau();
        c.penser(soi(0), List.of(j(A, 0, -20)), coups(A, 1, false));
        Decision d = c.penser(soi(40), List.of(), List.of());
        assertEquals(Tactique.DISPARITION, d.tactique(), "il se derobe, il ne revient pas aussitot");
    }

    @Test
    void tournerLaTete_nePerdPasLaProie_maisSeCacherSi() {
        Cerveau c = cerveau();
        c.penser(soi(0), List.of(avec(j(A, 0, -20), "detourne")), List.of());   // vu devant lui
        Joueur derriere = avec(j(A, 0, 30), "detourne");                        // a decouvert, dans son dos
        Decision d = c.penser(soi(40), List.of(derriere), List.of());
        assertNotEquals(Tactique.ENQUETE, d.tactique(), "hors du cone mais a decouvert : toujours suivi");
        Joueur cache = avec(avec(j(A, 0, 30), "detourne"), "cache");
        d = c.penser(soi(80), List.of(cache), List.of());
        assertEquals(Tactique.ENQUETE, d.tactique(), "cache : il perd sa trace et va voir");
    }

    @Test
    void unNageur_ilQuitteLaBergePourLEau() {
        Cerveau c = cerveau();
        Joueur nageur = avec(j(A, 0, -20), "eau");
        Decision d = c.penser(soi(0), List.of(nageur), List.of());
        assertEquals(Tactique.AFFUT_EAU, d.tactique(), "l'eau est son domaine : il ne reste pas a observer depuis la rive");
        assertEquals(nageur.pos(), d.destination());
    }

    @Test
    void laRancuneLeFaitRevenirSurUneTraceAncienne() {
        Cerveau c = cerveau();
        c.penser(soi(0), List.of(j(A, 0, -20)), coups(A, 30, false));
        Decision d = c.penser(soi(1500), List.of(), List.of());
        assertEquals(Tactique.ENQUETE, d.tactique());
    }

    @Test
    void enPleineFrappe_uneCibleBloqueeEstAbandonneePourUneAutre() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(A, 0, -8), "blesse"), j(B, 20, -14));
        Decision d = c.penser(soi(0), ps, coups(A, 1, false));            // riposte
        boolean passeSurB = false;
        for (int t = 4; t < 120; t += 4) {
            d = c.penser(soi(t), ps, List.of());                          // il n'avance jamais vers A
            passeSurB |= B.equals(d.cible()) && frappe(d);
        }
        assertTrue(passeSurB, "A inatteignable depuis 5 s : il change de cible");
    }

    @Test
    void destinationBloqueeEnFrappe_laCibleDevientInatteignable() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(A, 0, -8), "blesse"), j(B, 20, -20));
        c.penser(soi(0), ps, coups(A, 1, false));
        Decision d = c.penser(soi(4), ps, List.of());
        assertEquals(A, d.cible());
        c.destinationBloquee(5);
        assertEquals(B, c.penser(soi(8), ps, List.of()).cible());
    }

    @Test
    void joueurEnCreatif_ilLObserveSansJamaisLAttaquer() {
        Cerveau c = cerveau();
        Decision d = c.penser(soi(0), List.of(creatif(avec(j(A, 0, -30), "detourne"))), List.of());
        assertEquals(Tactique.TRAQUE, d.tactique(), d.raison());
        for (int t = 1; t < 200; t++) {
            d = c.penser(soi(t), List.of(creatif(j(A, 0, -5))), List.of());
            assertNull(d.attaque(), "jamais d'attaque sur un joueur en creatif");
        }
        assertEquals(Tactique.FIGE, d.tactique());
    }

    // ------------------------------------------------------------ terrain

    @Test
    void patrouilleLesBergesEtEviteFalaisesEtLave() {
        List<PointTerrain> terrain = List.of(
                new PointTerrain(new Vec(12, 0, 0), false, 0, 0, false),
                new PointTerrain(new Vec(-12, 0, 0), true, 1.5, -1, false),
                new PointTerrain(new Vec(0, 9, 12), false, 0, 9, false),
                new PointTerrain(new Vec(0, 0, -12), false, 0, 0, true));
        for (int essai = 0; essai < 20; essai++) {
            Cerveau n = new Cerveau(Reglages.defaut(), essai);
            Decision d = n.penser(new Soi(Vec.ZERO, NORD, 1, 300, false, false, null, false, 0, terrain), List.of(), List.of());
            assertEquals(new Vec(-12, 0, 0), d.destination(), "graine " + essai);
        }
    }

    @Test
    void neRevientPasSurSesPas() {
        Cerveau c = cerveau();
        List<PointTerrain> terrain = List.of(
                new PointTerrain(new Vec(-12, 0, 0), true, 1.5, -1, false),
                new PointTerrain(new Vec(12, 0, 2), true, 1.5, -1, false));
        Decision d1 = c.penser(new Soi(Vec.ZERO, NORD, 1, 300, false, false, null, false, 0, terrain), List.of(), List.of());
        Soi arrive = new Soi(d1.destination(), NORD, 1, 300, false, false, null, false, 20, terrain);
        assertNotEquals(d1.destination(), c.penser(arrive, List.of(), List.of()).destination());
    }

    // ------------------------------------------------------------ jungle, armes a feu, directeur

    static Joueur arme(Joueur p, boolean vide) {
        return new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), Arme.FEU, false, false, false,
                p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), false, vide, p.dansDomaine());
    }

    static Joueur horsJungle(Joueur p) {
        return new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(), false, false, false,
                p.dansEau(), p.visible(), p.atteignable(), p.vitesse(), false, false, false);
    }

    @Test
    void joueurSortiDeLaJungle_ilResteALOreeEtNeLeSuitPas() {
        Cerveau c = cerveau();
        List<PointTerrain> terrain = List.of(
                new PointTerrain(new Vec(0, 0, -8), false, 0, 0, false, true, false),     // lisiere (jungle)
                new PointTerrain(new Vec(0, 0, -20), false, 0, 0, false, false, false));  // plaine
        Joueur plaine = horsJungle(avec(j(A, 0, -26), "detourne"));
        Decision d = null;
        for (long t = 0; t <= 2400; t += 4) {
            d = c.penser(new Soi(Vec.ZERO, NORD, 1, 300, false, false, null, false, t, terrain), List.of(plaine), List.of());
            assertFalse(frappe(d), "il ne frappe pas en plaine");
            assertNotEquals(Tactique.FILATURE, d.tactique(), "il ne la suit pas en plaine");
        }
        assertEquals(Tactique.OBSERVATION, d.tactique(), d.raison());
        assertEquals(new Vec(0, 0, -8), d.destination(), "il guette depuis la lisiere");
    }

    @Test
    void canonBraqueSurLui_ilDisparaitMemeDeLoin() {
        Cerveau c = cerveau();
        Decision d = c.penser(soi(0), List.of(arme(j(A, 0, -35), false)), List.of());
        assertEquals(Tactique.DISPARITION, d.tactique(), "pas de duel de regards avec un fusil : " + d.raison());
    }

    @Test
    void chargeurVide_ilProfiteDuRechargement() {
        Cerveau c = cerveau();
        jusqua(c, List.of(avec(j(C, 0, -45), "detourne")), 0, 1000, x -> false);      // phase 2
        Decision d = c.penser(soi(1004), List.of(arme(j(C, 0, -17), true)), List.of()); // il le regarde, mais recharge
        assertTrue(frappe(d), "chargeur vide : " + d.raison());
    }

    @Test
    void faceAUnCanonBraque_jamaisDeChargeEnLigneDroite() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(arme(j(C, 0, -13), false));
        c.penser(soi(0), ps, coups(C, 1, false));                 // pour ouvrir une frappe il faudrait etre au contact...
        Soi s = soi(4);
        Attaque a = ChoixAttaque.choisir(s, arme(j(C, 0, -13), false), ps, new java.util.EnumMap<>(Attaque.class), Reglages.defaut());
        assertNotEquals(Attaque.CHARGE, a, "charger un fusil braque, c'est mourir");
    }

    @Test
    void sousLeFeu_ilSeMetACouvert() {
        Cerveau c = cerveau();
        Vec abri = new Vec(-10, 0, 6);
        List<PointTerrain> terrain = List.of(new PointTerrain(abri, false, 0, 0, false, true, true),
                new PointTerrain(new Vec(10, 0, -6), false, 0, 0, false, true, false));
        Joueur tireur = arme(avec(j(A, 0, -30), "detourne"), false);
        Soi s = new Soi(Vec.ZERO, NORD, 1, 300, false, false, null, false, 0, terrain);
        Decision d = c.penser(s, List.of(tireur), List.of(new Evenement.Tir(A, tireur.pos())));
        assertEquals(Tactique.DISPARITION, d.tactique(), d.raison());
        assertEquals(abri, d.destination(), "derriere le tronc, hors de sa vue");
    }

    @Test
    void unCoupDeFeuSEntendDeLoin() {
        Cerveau c = cerveau();
        Joueur loin = arme(avec(j(A, 0, -90), "detourne"), false);          // hors de vue
        c.penser(soi(0), List.of(loin), List.of(new Evenement.Tir(A, loin.pos())));
        Decision d = c.penser(soi(40), List.of(loin), List.of());
        assertEquals(Tactique.ENQUETE, d.tactique(), "il va voir d'ou venait le coup de feu");
        assertEquals(new Vec(0, 0, -90), d.destination());
    }

    @Test
    void directeur_sansContactLongtemps_ilFlaireTaZone() {
        Cerveau c = cerveau();
        Joueur loin = avec(j(A, 100, -60), "detourne");                      // hors de portee de ses sens
        Decision d = c.penser(soi(0), List.of(loin), List.of());
        assertEquals(Tactique.ERRANCE, d.tactique(), "d'abord il ne sait rien");
        d = c.penser(soi(1300), List.of(loin), List.of());
        assertEquals(Tactique.ENQUETE, d.tactique(), d.raison());
        assertTrue(d.destination().distanceH(loin.pos()) <= Reglages.defaut().flouIndice + 0.01,
                "une zone floue autour du joueur : " + d.destination());
    }

    @Test
    void tropLongtempsSurLeDosDuJoueurSansFrapper_ilSeRetire() {
        Cerveau c = cerveau();
        // un groupe : il ne peut pas frapper, mais il reste pres pendant 3 min
        List<Joueur> groupe = List.of(avec(j(A, -2, -20), "detourne"), avec(j(B, 2, -20), "detourne"));
        Decision d = jusqua(c, groupe, 0, 4000, x -> x.raison().contains("se retire"));
        assertTrue(d.raison().contains("se retire"), d.raison());
        assertTrue(d.destination().distanceH(new Vec(0, 0, -20)) > 40, "il part loin, en coulisses");
    }
}
