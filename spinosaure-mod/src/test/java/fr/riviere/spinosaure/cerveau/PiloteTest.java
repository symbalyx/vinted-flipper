package fr.riviere.spinosaure.cerveau;

import fr.riviere.spinosaure.cerveau.Decision.Allure;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Le pilote est simule avec le meme modele cinematique que Minecraft : a chaque tick le
 * corps avance de vitesseSol(v) blocs dans la direction de son lacet.
 */
class PiloteTest {

    /** Etat simule : position + lacet. Lacet 180 = nord (-Z). */
    static final class Corps {
        Vec pos = Vec.ZERO;
        float lacet = 180;
        Pilote.Commande derniere;

        Pilote.Commande pas(Pilote p, Vec vise, List<Vec> suivants, Allure allure) {
            derniere = p.piloter(pos, lacet, vise, suivants, allure);
            lacet = derniere.lacet();
            double rad = Math.toRadians(lacet), s = Pilote.vitesseSol(derniere.vitesse());
            pos = pos.plus(new Vec(-Math.sin(rad) * s, 0, Math.cos(rad) * s));
            return derniere;
        }
    }

    static Pilote lance(Corps c, Allure allure) {
        Pilote p = new Pilote();
        for (int i = 0; i < 60; i++) {
            c.pas(p, c.pos.plus(new Vec(0, 0, -50)), List.of(), allure);   // droit devant, au nord
        }
        return p;
    }

    @Test
    void lesRayonsDeBraquageSontCeuxDUnGrosAnimal() {
        assertTrue(Pilote.rayon(Allure.MARCHE.vitesse) < 1.0, "au pas il tourne court");
        double course = Pilote.rayon(Allure.COURSE.vitesse), charge = Pilote.rayon(Allure.CHARGE.vitesse);
        assertTrue(course > 2 && course < 4, "course : " + course);
        assertTrue(charge > 4 && charge < 7, "charge : " + charge);
        assertEquals(5.1, Pilote.vitesseSol(Allure.COURSE.vitesse) * 20, 0.2, "course en blocs/s");
    }

    @Test
    void cibleDerriere_ilPivoteSurPlaceSansAvancer() {
        Pilote p = new Pilote();
        Corps c = new Corps();                              // a l'arret, face au nord
        Vec derriere = new Vec(0, 0, 12);
        Pilote.Commande k = c.pas(p, derriere, List.of(), Allure.COURSE);
        assertEquals(Pilote.Geste.PIVOT, k.geste());
        assertTrue(Math.abs(Pilote.ecart(180, k.lacet())) <= Pilote.PIVOT_DEG + 1e-6);
        for (int i = 0; i < 30; i++) {
            c.pas(p, derriere, List.of(), Allure.COURSE);
        }
        assertTrue(c.pos.distanceH(Vec.ZERO) < 0.5, "il a pivote presque sur place : " + c.pos);
        for (int i = 0; i < 60; i++) {
            c.pas(p, derriere, List.of(), Allure.COURSE);
        }
        assertTrue(c.pos.z() > 3, "puis il est reparti vers la cible : " + c.pos);
    }

    @Test
    void accelereProgressivement() {
        Pilote p = new Pilote();
        Corps c = new Corps();
        int ticks = 0;
        while (c.pas(p, new Vec(0, 0, -200), List.of(), Allure.COURSE).vitesse() < Allure.COURSE.vitesse) {
            ticks++;
        }
        assertTrue(ticks >= 30, "de l'arret a la course en " + ticks + " ticks");
    }

    @Test
    void chargeRatee_ilDepasseLargementAvantDeRevenir() {
        Corps c = new Corps();
        Pilote p = lance(c, Allure.CHARGE);
        // esquive : le joueur se retrouve 3 blocs DERRIERE lui ; il le vise toujours en charge
        Vec joueur = c.pos.plus(new Vec(0, 0, 3));
        double loin = 0;
        for (int i = 0; i < 60; i++) {
            c.pas(p, joueur, List.of(), Allure.CHARGE);
            loin = Math.max(loin, c.pos.distanceH(joueur));
        }
        assertTrue(loin > 9, "lance, il ne fait pas demi-tour sur place : il s'eloigne a " + loin
                + " blocs avant de revenir, la fenetre de contre-attaque des joueurs");
    }

    @Test
    void neTournePasIndefinimentAutourDUnPointProche() {
        Corps c = new Corps();
        Pilote p = lance(c, Allure.COURSE);
        Vec cote = c.pos.plus(new Vec(-2.5, 0, 0));        // 2.5 blocs sur sa gauche
        int t = 0;
        while (c.pos.distanceH(cote) > 1.0 && t < 200) {
            c.pas(p, cote, List.of(), Allure.COURSE);
            t++;
        }
        assertTrue(t < 120, "il ralentit pour l'atteindre au lieu d'orbiter (" + t + " ticks)");
    }

    @Test
    void freineAvantUnVirageSerre() {
        Corps c = new Corps();
        Pilote p = lance(c, Allure.COURSE);
        Vec coin = c.pos.plus(new Vec(0, 0, -12));
        Vec apres = coin.plus(new Vec(-12, 0, 0));          // virage a 90 degres sur la gauche
        double auCoin = 0;
        while (c.pos.distanceH(coin) > 1.0) {
            auCoin = c.pas(p, coin, List.of(apres), Allure.COURSE).vitesse();
        }
        assertTrue(auCoin < 0.8, "vitesse a l'entree du virage : " + auCoin);
    }

    @Test
    void sEssouffleEnCourantTropLongtempsPuisRecupere() {
        Corps c = new Corps();
        Pilote p = new Pilote();
        int t = 0;
        while (!p.essouffle() && t < 1000) {
            c.pas(p, c.pos.plus(new Vec(0, 0, -50)), List.of(), Allure.COURSE);
            t++;
        }
        assertTrue(p.essouffle(), "jamais essouffle");
        assertTrue(t > 200 && t < 330, "essouffle apres " + t + " ticks de course");
        for (int i = 0; i < 20; i++) {
            c.pas(p, c.pos.plus(new Vec(0, 0, -50)), List.of(), Allure.COURSE);
        }
        assertTrue(p.vitesseCourante() <= Allure.MARCHE.vitesse + 1e-9, "essouffle : il marche");
        for (int i = 0; i < 200; i++) {
            c.pas(p, c.pos.plus(new Vec(0, 0, -50)), List.of(), Allure.MARCHE);
        }
        assertFalse(p.essouffle(), "10 s de marche : il a repris son souffle");
    }

    @Test
    void arretEnPleineCourse_gesteDeFreinage() {
        Corps c = new Corps();
        Pilote p = lance(c, Allure.COURSE);
        assertEquals(Pilote.Geste.FREINAGE, c.pas(p, null, List.of(), Allure.ARRET).geste());
        assertNotEquals(Pilote.Geste.FREINAGE, c.pas(p, null, List.of(), Allure.ARRET).geste(), "une seule fois");
    }

    @Test
    void virageRapide_gesteDeVirageDuBonCote() {
        Corps c = new Corps();                               // face au nord (-Z) : l'est (+X) est a droite
        Pilote p = lance(c, Allure.COURSE);
        Pilote.Commande k = c.pas(p, c.pos.plus(new Vec(10, 0, -6)), List.of(), Allure.COURSE);
        assertEquals(Pilote.Geste.VIRAGE_DROITE, k.geste());
    }

    /** Chemin en escalier (un pas en X, un pas en Z...) comme en produit la grille vanilla. */
    static List<Vec> escalier(int n) {
        List<Vec> out = new java.util.ArrayList<>();
        int x = 0, z = 0;
        for (int i = 0; i < n; i++) {
            if (i % 2 == 0) {
                x++;
            } else {
                z--;
            }
            out.add(new Vec(x, 0, z));
        }
        return out;
    }

    /** [vitesse moyenne, oscillation moyenne du cap en degres/tick] */
    static double[] mesure(double anticipation) {
        List<Vec> chemin = escalier(80);
        Corps c = new Corps();
        c.lacet = 225;                                          // deja oriente nord-est
        Pilote p = new Pilote();
        int suivant = 0;
        double somme = 0, oscillation = 0;
        float lacetAvant = c.lacet;
        int t = 0;
        while (suivant < chemin.size() - 1 && t < 2000) {
            // la navigation vanilla avance au noeud suivant a 1.7 bloc (demi-largeur)
            while (suivant < chemin.size() - 1 && c.pos.distanceH(chemin.get(suivant)) < 1.7) {
                suivant++;
            }
            List<Vec> reste = chemin.subList(suivant, chemin.size());
            int n = anticipation > 0 ? Pilote.fenetre(c.pos, reste, anticipation) : 0;
            Vec vise = n > 0 ? Pilote.viseeMoyenne(c.pos, reste, anticipation) : reste.get(0);
            int k = Math.max(n - 1, 0);
            List<Vec> apres = reste.subList(Math.min(k + 1, reste.size()), Math.min(k + 5, reste.size()));
            somme += c.pas(p, vise, apres, Allure.COURSE).vitesse();
            oscillation += Math.abs(Pilote.ecart(lacetAvant, c.lacet));
            lacetAvant = c.lacet;
            t++;
        }
        return new double[]{somme / t, oscillation / t};
    }

    @Test
    void cheminEnEscalier_lAnticipationEviteLesSaccades() {
        double[] sans = mesure(0), avec = mesure(Pilote.ANTICIPATION);
        System.out.printf("MESURE sans: vitesse %.3f cap %.3f deg/tick | avec: vitesse %.3f cap %.3f%n",
                sans[0], sans[1], avec[0], avec[1]);
        assertTrue(avec[0] > 0.85, "en diagonale il garde son allure de course : " + avec[0]);
        // les animations de virage se declenchent a 2.5 deg/tick : il faut rester bien en dessous
        assertTrue(avec[1] < 1.0, "cap stable sur une diagonale droite : " + avec[1] + " deg/tick");
    }
}
