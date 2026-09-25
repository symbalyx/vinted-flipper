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
 * Scenarios multijoueurs. Le spinosaure est a l'origine, regard vers -Z (vers le nord),
 * sauf mention contraire.
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
                false, false, false, false, true, true);
    }

    static Vec versOrigine(double x, double z) {
        return new Vec(-x, 0, -z).unitaire();
    }

    static Joueur avec(Joueur p, String quoi) {
        return switch (quoi) {
            case "bouclier" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    true, p.accroupi(), p.sprinte(), p.dansEau(), p.visible(), p.atteignable());
            case "eau" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    p.bouclierLeve(), p.accroupi(), p.sprinte(), true, p.visible(), p.atteignable());
            case "perche" -> new Joueur(p.id(), p.pos().plus(new Vec(0, 6, 0)), p.regard(), p.sante(), p.armure(),
                    Arme.DISTANCE, false, false, false, false, true, false);
            case "accroupi" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    false, true, false, p.dansEau(), p.visible(), p.atteignable());
            case "sprint" -> new Joueur(p.id(), p.pos(), p.regard(), p.sante(), p.armure(), p.arme(),
                    false, false, true, p.dansEau(), p.visible(), p.atteignable());
            case "detourne" -> new Joueur(p.id(), p.pos(), p.regard().fois(-1), p.sante(), p.armure(), p.arme(),
                    p.bouclierLeve(), p.accroupi(), p.sprinte(), p.dansEau(), p.visible(), p.atteignable());
            case "blesse" -> new Joueur(p.id(), p.pos(), p.regard(), 0.3, 2, p.arme(),
                    p.bouclierLeve(), p.accroupi(), p.sprinte(), p.dansEau(), p.visible(), p.atteignable());
            default -> throw new IllegalArgumentException(quoi);
        };
    }

    static Cerveau cerveau() {
        return new Cerveau(Reglages.defaut(), 42);
    }

    static List<Evenement> coups(UUID source, double montant, boolean distance) {
        return List.of(new Evenement.Degats(source, montant, distance));
    }

    // ------------------------------------------------------------ perception

    @Test
    void unJoueurAccroupiDansLeDosPasseInapercu() {
        Reglages r = Reglages.defaut();
        Joueur furtif = avec(avec(j(A, 0, 10), "accroupi"), "detourne");   // 10 blocs derriere
        assertFalse(Perception.percoit(soi(0), furtif, r));
        Joueur bruyant = avec(j(A, 0, 20), "sprint");                       // 20 derriere, en sprint
        assertTrue(Perception.percoit(soi(0), bruyant, r), "un sprint s'entend a 24 blocs");
    }

    // ------------------------------------------------------------ choix de cible

    @Test
    void prefereLeJoueurIsoleAuGroupe() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, -3, -10), j(B, -1, -10), j(C, 14, -6));
        c.penser(soi(0), ps, coups(A, 1, false));           // deja en combat : pas de traque
        Decision d = c.penser(soi(1), ps, List.of());
        assertEquals(C, d.cible(), d.raison());
    }

    @Test
    void neChangePasDeCibleAChaqueTick() {
        Cerveau c = cerveau();
        int changements = 0;
        UUID avant = null;
        for (int t = 0; t < 400; t++) {
            // deux joueurs quasi equivalents qui oscillent autour de la meme distance
            double e = Math.sin(t * 0.7) * 0.8;
            List<Joueur> ps = List.of(j(A, -8, -10 + e), j(B, 8, -10 - e));
            Decision d = c.penser(soi(t), ps, t == 0 ? coups(A, 1, false) : List.of());
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
        Joueur tireur = avec(j(A, 0, -12), "perche");
        Joueur epeiste = j(B, 6, -9);
        List<Joueur> ps = List.of(tireur, epeiste);
        Decision d = null;
        for (int t = 0; t < 60; t++) {
            d = c.penser(soi(t), ps, t % 20 == 0 ? coups(A, 4, true) : List.of());
        }
        assertEquals(B, d.cible(), "il ne reste pas plante sous le pilier : " + d.raison());
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
        assertEquals(eau, d.destination(), "il plonge pour casser la ligne de vue");
    }

    // ------------------------------------------------------------ attaques

    @Test
    void encercle_balayageDeQueue() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, 0, -4), j(B, -2, 4), j(C, 2, 5));   // un devant, deux derriere
        Decision d = c.penser(soi(0), ps, coups(B, 2, false));
        assertEquals(Attaque.BALAYAGE_QUEUE, d.attaque(), d.raison());
    }

    @Test
    void bouclierLeve_griffesPuisContournement() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(avec(j(A, 0, -4), "bouclier"));
        Decision d1 = c.penser(soi(0), ps, coups(A, 1, false));
        assertEquals(Attaque.GRIFFES, d1.attaque(), "les griffes brisent le bouclier");
        Decision d2 = c.penser(soi(5), ps, List.of());
        assertEquals(Tactique.CONTOURNEMENT, d2.tactique(), "griffes en recharge : il passe sur le flanc");
        assertTrue(Math.abs(d2.destination().x()) > 2, "destination laterale : " + d2.destination());
    }

    @Test
    void attaqueParLeCoteOpposeAuxAllies() {
        Cerveau c = cerveau();
        // la cible C est au nord, hors de portee de charge ; ses deux allies sont a l'ouest d'elle
        Joueur cible = avec(j(C, 0, -24), "blesse");
        List<Joueur> ps = List.of(cible, j(A, -12, -24), j(B, -12, -26));
        c.penser(soi(0), ps, coups(C, 1, false));
        Decision d = c.penser(soi(80), ps, List.of());
        assertEquals(C, d.cible());
        assertTrue(d.destination().x() > 0, "il vient par l'est, les allies a l'ouest : " + d.destination());
    }

    @Test
    void chargeQuandLaLigneEstDegagee() {
        Cerveau c = cerveau();
        Decision d = c.penser(soi(0), List.of(j(A, 0, -13)), coups(A, 1, false));
        assertEquals(Attaque.CHARGE, d.attaque(), d.raison());
        assertEquals(Allure.CHARGE, d.allure());
    }

    // ------------------------------------------------------------ groupe

    @Test
    void unGroupeArrive_rugissementUneSeuleFois() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, -4, -18), j(B, 0, -20), j(C, 4, -18));
        Decision d = c.penser(soi(0), ps, List.of());
        assertEquals(Attaque.RUGISSEMENT, d.attaque());
        Decision d2 = c.penser(soi(20), ps, List.of());
        assertNotEquals(Attaque.RUGISSEMENT, d2.attaque());
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

        // soigne ; le joueur A (le plus rancunier) est au bord de l'eau
        List<Joueur> bord = List.of(avec(j(A, 0, -20), "eau"));
        d = c.penser(soi(900, 0.8, eau, true, true), bord, List.of());
        assertEquals(Tactique.AFFUT_EAU, d.tactique(), d.raison());
        assertEquals(A, d.cible());
    }

    @Test
    void sansEauEtPresqueMort_ilSeBatAcculé() {
        Cerveau c = cerveau();
        List<Joueur> ps = List.of(j(A, 0, -4), j(B, 3, -4));
        c.penser(soi(0, 0.5, null, false, false), ps, coups(A, 40, false));
        Decision d = c.penser(soi(5, 0.1, null, false, false), ps, coups(B, 40, false));
        assertEquals(Tactique.ACCULE, d.tactique(), d.raison());
    }

    // ------------------------------------------------------------ traque

    @Test
    void traqueFurtivePuisFigeSousLeRegard() {
        Cerveau c = cerveau();
        Joueur distrait = avec(j(A, 0, -30), "detourne");
        Decision d = c.penser(soi(0), List.of(distrait), List.of());
        assertEquals(Tactique.TRAQUE, d.tactique());
        assertEquals(Allure.FEUTREE, d.allure());
        assertNotNull(d.animation(), "il tourne la tete vers sa proie a la premiere detection");

        Decision f = c.penser(soi(5), List.of(j(A, 0, -30)), List.of());   // il se retourne et le voit
        assertEquals(Tactique.FIGE, f.tactique());

        Decision fin = null;
        for (int t = 6; t < 120; t++) {
            fin = c.penser(soi(t), List.of(j(A, 0, -30)), List.of());
        }
        assertEquals(Tactique.ENGAGEMENT, fin.tactique(), "fige trop longtemps : il passe a l'attaque");
    }

    // ------------------------------------------------------------ saisie

    @Test
    void saisieDansLEauPuisLiberationParLesAllies() {
        Cerveau c = cerveau();
        Vec eau = new Vec(0, -3, -12);
        Joueur nageur = avec(j(A, 0, -4), "eau");
        List<Joueur> ps = List.of(nageur, j(B, 6, 2));
        Decision d = c.penser(soi(0, 1, eau, true, false), ps, coups(A, 1, false));
        assertEquals(Attaque.SAISIE, d.attaque(), d.raison());

        c.priseEtablie(A, 10);
        d = c.penser(soi(11, 1, eau, true, false), ps, List.of());
        assertEquals(Tactique.MAINTIEN, d.tactique());
        assertEquals(eau, d.destination(), "il l'entraine vers l'eau profonde");

        d = c.penser(soi(20, 1, eau, true, false), ps, coups(B, 12, false));
        assertFalse(d.lacher());
        d = c.penser(soi(25, 1, eau, true, false), ps, coups(B, 10, false));
        assertTrue(d.lacher(), "22 degats des allies : il lache prise");
    }

    // ------------------------------------------------------------ memoire

    @Test
    void perdDeVue_vaVoirLaDerniereTracePuisRenifle() {
        Cerveau c = cerveau();
        c.penser(soi(0), List.of(j(A, 0, -20)), coups(A, 1, false));
        Decision d = c.penser(soi(40), List.of(), List.of());
        assertEquals(Tactique.ENQUETE, d.tactique());
        assertEquals(new Vec(0, 0, -20), d.destination());
        Soi arrive = new Soi(new Vec(0, 0, -19), NORD, 1, 300, false, false, null, false, 200);
        d = c.penser(arrive, List.of(), List.of());
        assertEquals("renifle_piste_sol", d.animation());
    }

    @Test
    void cibleBloqueeEstAbandonneePourUneAutre() {
        Cerveau c = cerveau();
        // A est derriere un obstacle : on ne peut pas s'en approcher. B est plus loin mais accessible.
        // Mini-simulation : le spinosaure avance de 0.25 bloc/tick vers sa destination, sauf vers A.
        Joueur a = avec(j(A, 0, -9), "blesse");
        List<Joueur> ps = List.of(a, j(B, 20, -14));
        Vec pos = Vec.ZERO;
        Decision d = null;
        for (int t = 0; t < 400; t++) {
            Soi s = new Soi(pos, NORD, 1, 300, false, false, null, false, t);
            d = c.penser(s, ps, t == 0 ? coups(A, 1, false) : List.of());
            if (d.destination() != null && B.equals(d.cible()) && pos.distanceH(d.destination()) > 4) {
                pos = pos.plus(d.destination().moins(pos).unitaireH().fois(0.25));
            }
        }
        assertEquals(B, d.cible(), "A est inatteignable depuis 5 s : il change de cible");
        assertTrue(pos.distanceH(new Vec(20, 0, -14)) < 8, "et il l'a rejoint : " + pos);
    }

    @Test
    void laRancuneLeFaitRevenirSurUneTraceAncienne() {
        Cerveau c = cerveau();
        c.penser(soi(0), List.of(j(A, 0, -20)), coups(A, 30, false));
        Decision d = c.penser(soi(1500), List.of(), List.of());      // 75 s plus tard, personne en vue
        assertEquals(Tactique.ENQUETE, d.tactique(), "30 degats de rancune : il n'a pas oublie");
    }
}
