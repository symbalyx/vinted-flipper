package fr.riviere.spinosaure.cerveau;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Choix de la cible parmi plusieurs joueurs. Un predateur ne fonce pas sur le plus
 * proche : il pese
 * <ul>
 *   <li>la MENACE (qui lui fait mal en ce moment) ;</li>
 *   <li>la VULNERABILITE (peu de vie, peu d'armure) ;</li>
 *   <li>l'ISOLEMENT (loin de ses allies, personne pour le secourir) ;</li>
 *   <li>le TERRAIN (un joueur dans l'eau est chez lui) ;</li>
 *   <li>la RANCUNE (celui qui l'a blesse la derniere fois) ;</li>
 * </ul>
 * et penalise la distance, les boucliers leves et les joueurs inatteignables (piliers,
 * trous) : il ne reste pas bloque sous un tireur perche s'il a mieux a faire.
 * Une hysteresis evite de changer de cible a chaque tick entre deux joueurs proches.
 */
public final class SelecteurCible {

    public record Resultat(UUID cible, double score, Map<UUID, Double> scores) {
    }

    private SelecteurCible() {
    }

    public static double score(Soi soi, Joueur j, List<Joueur> tous, Memoire m, Reglages r) {
        Memoire.Trace t = m.connue(j.id());
        double menace = t == null ? 0 : t.menace / (t.menace + 20.0);
        double rancune = t == null ? 0 : Math.min(t.rancune / 30.0, 1.0);
        double vuln = (1 - j.sante()) * 0.8 + (1 - j.armure() / 20.0) * 0.4;

        double allie = Double.MAX_VALUE;
        for (Joueur o : tous) {
            if (!o.id().equals(j.id())) {
                allie = Math.min(allie, o.pos().distance(j.pos()));
            }
        }
        double isole = Math.min(allie, r.isolement) / r.isolement;

        double d = soi.pos().distance(j.pos());
        double eau = j.dansEau() && (soi.dansEau() || soi.eauProfonde() != null) ? 0.3 : 0.0;
        double s = 1.2 * menace + 0.9 * vuln + 0.8 * isole + eau + 0.25 * rancune
                - 1.0 * d / r.porteeVue
                - (j.bouclierLeve() ? 0.15 : 0.0);
        if (!j.atteignable() || m.inatteignable(j.id(), soi.tick())) {
            s = s * 0.25 - 0.5;            // reste choisissable si c'est le seul
        }
        return s;
    }

    /**
     * @param actuelle      cible en cours (ou null)
     * @param engageDepuis  tick ou la cible actuelle a ete choisie
     */
    public static Resultat choisir(Soi soi, List<Joueur> percus, Memoire m, Reglages r,
                                   UUID actuelle, long engageDepuis) {
        Map<UUID, Double> scores = new HashMap<>();
        UUID meilleur = null;
        double best = -Double.MAX_VALUE;
        Double scoreActuel = null;
        for (Joueur j : percus) {
            double s = score(soi, j, percus, m, r);
            scores.put(j.id(), s);
            if (j.id().equals(actuelle)) {
                scoreActuel = s;
            }
            if (s > best) {
                best = s;
                meilleur = j.id();
            }
        }
        if (meilleur == null) {
            return new Resultat(null, 0, scores);
        }
        if (scoreActuel != null && !meilleur.equals(actuelle)) {
            // l'engagement minimal ne retient pas une cible devenue inatteignable
            boolean tropTot = soi.tick() - engageDepuis < r.engagementMin && scoreActuel > 0;
            // comparaison robuste au signe : l'ecart doit depasser une marge relative
            double marge = Math.abs(scoreActuel) * (r.hysteresis - 1) + 0.05;
            if (tropTot || best < scoreActuel + marge) {
                return new Resultat(actuelle, scoreActuel, scores);
            }
        }
        return new Resultat(meilleur, best, scores);
    }
}
