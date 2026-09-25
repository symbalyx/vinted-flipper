package fr.riviere.spinosaure.cerveau;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class DeblocageTest {

    @Test
    void coinceIlEssaieSauterReculerContournerPuisAbandonne() {
        Deblocage d = new Deblocage();
        List<Deblocage.Action> actions = new ArrayList<>();
        for (int t = 0; t < 300; t++) {
            Deblocage.Action a = d.evaluer(10.0, true);              // la distance ne baisse jamais
            if (a != Deblocage.Action.RIEN) {
                actions.add(a);
            }
            if (a == Deblocage.Action.ABANDONNER) {
                break;
            }
        }
        assertEquals(List.of(Deblocage.Action.SAUTER, Deblocage.Action.RECULER,
                Deblocage.Action.CONTOURNER, Deblocage.Action.ABANDONNER), actions);
    }

    @Test
    void reculerNeCompteParCommeUnProgres() {
        Deblocage d = new Deblocage();
        double dist = 10;
        List<Deblocage.Action> actions = new ArrayList<>();
        boolean recule = false;
        for (int t = 0; t < 300 && !actions.contains(Deblocage.Action.CONTOURNER); t++) {
            if (recule) {
                dist += 0.1;                                      // il s'eloigne en reculant
            }
            Deblocage.Action a = d.evaluer(dist, true);
            if (a == Deblocage.Action.RECULER) {
                recule = true;
            }
            if (a != Deblocage.Action.RIEN) {
                actions.add(a);
            }
        }
        assertTrue(actions.contains(Deblocage.Action.CONTOURNER), "l'echelle a continue : " + actions);
    }

    @Test
    void quandIlAvanceRienNeSeDeclenche() {
        Deblocage d = new Deblocage();
        for (int t = 0; t < 300; t++) {
            assertEquals(Deblocage.Action.RIEN, d.evaluer(40 - t * 0.1, true));
        }
    }

    @Test
    void aLArretVoulu_pasDeBlocage() {
        Deblocage d = new Deblocage();
        for (int t = 0; t < 300; t++) {
            assertEquals(Deblocage.Action.RIEN, d.evaluer(10, false));
        }
    }
}
