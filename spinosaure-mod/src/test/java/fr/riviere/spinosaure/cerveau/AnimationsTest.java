package fr.riviere.spinosaure.cerveau;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Chaque animation du modele est jouee ou ecartee pour une raison ecrite ; chaque nom demande
 * existe dans le fichier et est enregistre dans le bon controleur.
 */
class AnimationsTest {

    static final Path RACINE = trouver();

    static Path trouver() {
        for (Path p : List.of(Path.of(""), Path.of("spinosaure-mod"))) {
            if (Files.exists(p.resolve("src/main/resources/assets/spinosaure/animations/spinosaure.animation.json"))) {
                return p;
            }
        }
        throw new IllegalStateException("fichier d'animations introuvable depuis " + Path.of("").toAbsolutePath());
    }

    static Set<String> duFichier() throws IOException {
        String json = Files.readString(RACINE.resolve("src/main/resources/assets/spinosaure/animations/spinosaure.animation.json"));
        Set<String> out = new LinkedHashSet<>();
        Matcher m = Pattern.compile("\"animation\\.spinosaure\\.([a-z_]+)\"").matcher(json);
        while (m.find()) {
            out.add(m.group(1));
        }
        return out;
    }

    @Test
    void chaqueAnimationEstJoueeOuEcarteeAvecUneRaison() throws IOException {
        Set<String> fichier = duFichier();
        assertTrue(fichier.size() >= 80, fichier.size() + " animations lues");
        Set<String> usages = new HashSet<>(Animations.AMBIANCES);
        usages.addAll(Animations.ACTIONS);
        usages.addAll(Animations.MOUVEMENTS);
        List<String> orphelines = new ArrayList<>();
        for (String n : fichier) {
            if (!usages.contains(n) && !Animations.ECARTEES.containsKey(n)) {
                orphelines.add(n);
            }
        }
        assertEquals(List.of(), orphelines, "animations ni jouees ni ecartees");
    }

    @Test
    void chaqueNomDemandeExisteDansLeFichier() throws IOException {
        Set<String> fichier = duFichier();
        List<String> tous = new ArrayList<>(Animations.AMBIANCES);
        tous.addAll(Animations.ACTIONS);
        tous.addAll(Animations.MOUVEMENTS);
        for (String n : tous) {
            assertTrue(fichier.contains(n), "animation inconnue : " + n);
            assertFalse(Animations.ECARTEES.containsKey(n), "a la fois jouee et ecartee : " + n);
        }
    }

    @Test
    void lesAttaquesSontEnregistreesDansLeControleurAction() {
        for (Attaque a : Attaque.values()) {
            if (a != Attaque.CHARGE) {
                assertTrue(Animations.ACTIONS.contains(a.animation), a + " : " + a.animation);
            }
        }
    }

    /** Toute animation citee par le cerveau dans une decision doit etre une ambiance enregistree. */
    @Test
    void lesAnimationsDuCerveauSontEnregistrees() throws IOException {
        Set<String> fichier = duFichier();
        String src = Files.readString(RACINE.resolve("src/main/java/fr/riviere/spinosaure/cerveau/Cerveau.java"));
        Matcher m = Pattern.compile("\"([a-z_]+)\"").matcher(src);
        List<String> manquantes = new ArrayList<>();
        while (m.find()) {
            String n = m.group(1);
            if (fichier.contains(n) && !Animations.AMBIANCES.contains(n)) {
                manquantes.add(n);
            }
        }
        assertEquals(List.of(), manquantes, "demandees par le cerveau mais pas enregistrees");
    }
}
