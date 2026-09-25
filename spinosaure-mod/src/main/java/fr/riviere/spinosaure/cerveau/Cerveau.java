package fr.riviere.spinosaure.cerveau;

import fr.riviere.spinosaure.cerveau.Decision.Allure;
import fr.riviere.spinosaure.cerveau.Decision.Tactique;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.UUID;

/**
 * Le cerveau du spinosaure. Aucune dependance a Minecraft : il recoit un instantane
 * (lui-meme, les joueurs, ce qui vient de se passer) et rend une {@link Decision}.
 *
 * <p>Ordre de priorite a chaque reflexion :
 * <ol>
 *   <li>tenir un joueur saisi, ou le lacher si ses allies le liberent ;</li>
 *   <li>survivre : repli vers l'eau profonde et regeneration quand il perd a plusieurs ;</li>
 *   <li>ne pas se faire farmer : rompre la ligne de vue d'un tireur inatteignable ;</li>
 *   <li>face a un groupe qui arrive : rugir pour le disperser ;</li>
 *   <li>proie seule et distraite : traque, figé sous le regard, affut dans l'eau ;</li>
 *   <li>combat : cible choisie par score, attaque choisie par geometrie, approche par le
 *       cote oppose aux allies de la cible, detection de blocage ;</li>
 *   <li>sans personne : enquete sur la derniere trace, sinon errance.</li>
 * </ol>
 */
public final class Cerveau {

    private final Reglages r;
    private final Memoire m;
    private final Random alea;
    private final Map<Attaque, Long> pret = new EnumMap<>(Attaque.class);

    private Tactique tactique = Tactique.ERRANCE;
    private long tactiqueDepuis;
    private UUID cible;
    private long cibleDepuis;

    private UUID tenu;
    private long tenuDepuis;
    private double degatsAllies, degatsVictime;

    private double meilleureDistance = Double.MAX_VALUE;
    private long tickProgres;
    private long esquiveJusqua = Long.MIN_VALUE / 2;
    private long figeDepuis = -1;
    private boolean groupeSalue;
    private long dernierContact = Long.MIN_VALUE / 2;
    private Vec pointErrance;
    private long errancePlanifiee = Long.MIN_VALUE / 2;
    private boolean renifle;

    public Cerveau(Reglages r, long graine) {
        this.r = r;
        this.m = new Memoire(r);
        this.alea = new Random(graine);
    }

    public Memoire memoire() {
        return m;
    }

    public Tactique tactique() {
        return tactique;
    }

    public UUID cible() {
        return cible;
    }

    public UUID tenu() {
        return tenu;
    }

    /** Le corps confirme que la saisie a reussi : le joueur est dans la gueule. */
    public void priseEtablie(UUID victime, long tick) {
        tenu = victime;
        tenuDepuis = tick;
        degatsAllies = 0;
        degatsVictime = 0;
        changer(Tactique.MAINTIEN, tick);
    }

    /** Le corps a du lacher (mort, deconnexion, teleportation...). */
    public void priseRompue(long tick) {
        tenu = null;
        changer(Tactique.ENGAGEMENT, tick);
    }

    // ================================================================== reflexion

    public Decision penser(Soi soi, List<Joueur> joueurs, List<Evenement> evts) {
        long tick = soi.tick();
        m.vieillir(tick);

        Map<UUID, Joueur> parId = new HashMap<>();
        for (Joueur j : joueurs) {
            parId.put(j.id(), j);
        }
        List<Joueur> percus = new ArrayList<>();
        for (Joueur j : joueurs) {
            if (Perception.percoit(soi, j, r)) {
                percus.add(j);
            }
        }
        for (Evenement e : evts) {
            if (e instanceof Evenement.Degats d) {
                Joueur j = parId.get(d.source());
                boolean atteignable = j == null || (j.atteignable() && !m.inatteignable(j.id(), tick));
                m.blesse(d.source(), d.montant(), d.aDistance(), atteignable, tick);
                if (j != null && !percus.contains(j)) {
                    percus.add(j);                       // il sait d'ou vient le coup
                }
                if (tenu != null) {
                    if (d.source().equals(tenu)) {
                        degatsVictime += d.montant();
                    } else {
                        degatsAllies += d.montant();
                    }
                }
            } else if (e instanceof Evenement.Bruit b) {
                if (b.pos().distance(soi.pos()) <= b.portee()) {
                    m.vu(b.source(), b.pos(), tick);
                }
            }
        }
        for (Joueur j : percus) {
            m.vu(j.id(), j.pos(), tick);
        }
        if (!percus.isEmpty()) {
            dernierContact = tick;
        } else if (tick - dernierContact > 400) {
            groupeSalue = false;
        }

        Decision d;
        if ((d = maintien(soi, parId, percus)) != null) {
            return d;
        }
        if ((d = survie(soi, percus)) != null) {
            return d;
        }
        if ((d = esquiveTireur(soi, percus)) != null) {
            return d;
        }
        if (percus.isEmpty()) {
            return sansPersonne(soi);
        }
        return combat(soi, percus);
    }

    // ------------------------------------------------------------------ 1. maintien

    private Decision maintien(Soi soi, Map<UUID, Joueur> parId, List<Joueur> percus) {
        if (tenu == null) {
            return null;
        }
        long tick = soi.tick();
        Joueur v = parId.get(tenu);
        String pourquoi = null;
        if (v == null) {
            pourquoi = "victime disparue";
        } else if (degatsAllies >= r.liberationParAllies) {
            pourquoi = "ses allies l'ont libere (" + Math.round(degatsAllies) + " degats)";
        } else if (degatsVictime >= r.liberationParVictime) {
            pourquoi = "la victime s'est debattue";
        } else if (tick - tenuDepuis >= r.maintienMax) {
            pourquoi = "fin du maintien";
        }
        if (pourquoi != null) {
            UUID lache = tenu;
            tenu = null;
            changer(Tactique.ENGAGEMENT, tick);
            pret.put(Attaque.SAISIE, tick + Attaque.SAISIE.recharge);
            return new Decision(Tactique.ENGAGEMENT, lache, null, Allure.ARRET, null, null, true, null,
                    "lache : " + pourquoi);
        }
        // entrainer la victime : vers l'eau profonde, sinon a l'oppose de ses allies
        Vec but;
        String ou;
        if (soi.eauProfonde() != null && !soi.submerge()) {
            but = soi.eauProfonde();
            ou = "vers l'eau profonde";
        } else if (soi.submerge()) {
            but = soi.pos().plus(new Vec(0, -3, 0));
            ou = "au fond";
        } else {
            Vec c = centre(percus, tenu);
            Vec fuite = c == null ? soi.regard().fois(-1) : soi.pos().moins(c).unitaireH();
            but = soi.pos().plus(fuite.fois(10));
            ou = "loin de ses allies";
        }
        Allure a = soi.dansEau() ? Allure.NAGE : Allure.MARCHE;
        return new Decision(Tactique.MAINTIEN, tenu, but, a, null, null, false, null, "entraine sa proie " + ou);
    }

    // ------------------------------------------------------------------ 2. survie

    private Decision survie(Soi soi, List<Joueur> percus) {
        long tick = soi.tick();
        int adversaires = compterProches(soi, percus, r.rayonGroupe);
        boolean perd = m.degatsRecents() / soi.santeMax() > 0.20;
        boolean enRepli = tactique == Tactique.REPLI || tactique == Tactique.REGENERATION;

        if (enRepli && soi.sante() >= r.seuilRetour) {
            // soigne : il revient, en embuscade, pour celui qui lui en veut le plus
            UUID vise = plusRancunier(percus);
            changer(Tactique.AFFUT_EAU, tick);
            if (vise != null) {
                viser(vise, tick);
            }
            return null;
        }
        boolean doitFuir = soi.sante() < r.seuilRepli && (adversaires >= 2 || perd);
        if (!doitFuir && !enRepli) {
            return null;
        }
        if (soi.eauProfonde() == null && !soi.submerge()) {
            if (soi.sante() < r.seuilAcculeSansEau) {
                changer(Tactique.ACCULE, tick);    // pas d'eau : il se bat jusqu'au bout
            }
            return null;
        }
        if (soi.submerge()) {
            changer(Tactique.REGENERATION, tick);
            Joueur proche = plusProche(soi, percus);
            Vec but = proche == null ? null
                    : soi.pos().plus(soi.pos().moins(proche.pos()).unitaireH().fois(6)).plus(new Vec(0, -2, 0));
            return new Decision(Tactique.REGENERATION, null, but, Allure.NAGE, null, null, false, null,
                    "se soigne au fond (" + Math.round(soi.sante() * 100) + " %)");
        }
        changer(Tactique.REPLI, tick);
        Allure a = soi.dansEau() ? Allure.NAGE_RAPIDE : Allure.COURSE;
        return new Decision(Tactique.REPLI, null, soi.eauProfonde(), a, null, null, false,
                tactiqueDepuis == tick ? "plonge" : null,
                "repli vers l'eau : " + adversaires + " adversaires, " + Math.round(soi.sante() * 100) + " % de vie");
    }

    // ------------------------------------------------------------------ 3. tireur

    private Decision esquiveTireur(Soi soi, List<Joueur> percus) {
        long tick = soi.tick();
        boolean quelquUnAtteignable = false;
        for (Joueur j : percus) {
            if (j.atteignable() && !m.inatteignable(j.id(), tick)) {
                quelquUnAtteignable = true;
                break;
            }
        }
        if (quelquUnAtteignable) {
            return null;                    // il a mieux a faire : le selecteur s'en charge
        }
        Joueur tireur = null;
        for (Joueur j : percus) {
            if (m.tirsInatteignables(j.id(), tick) >= r.coupsTireurAvantEsquive) {
                tireur = j;
            }
        }
        if (tireur != null) {
            esquiveJusqua = tick + r.dureeEsquive;
        }
        if (tick >= esquiveJusqua) {
            return null;
        }
        changer(Tactique.ESQUIVE_TIR, tick);
        Vec but;
        String comment;
        if (soi.eauProfonde() != null || soi.submerge()) {
            but = soi.submerge() ? soi.pos().plus(new Vec(0, -2, 0)) : soi.eauProfonde();
            comment = "plonge pour rompre la ligne de tir";
        } else {
            Vec depuis = tireur != null ? tireur.pos() : centre(percus, null);
            Vec fuite = depuis == null ? soi.regard().fois(-1) : soi.pos().moins(depuis).unitaireH();
            but = soi.pos().plus(fuite.fois(16));
            comment = "s'eloigne hors de portee du tireur perche";
        }
        Allure a = soi.dansEau() ? Allure.NAGE_RAPIDE : Allure.COURSE;
        return new Decision(Tactique.ESQUIVE_TIR, null, but, a, null, null, false, null, comment);
    }

    // ------------------------------------------------------------------ 7. personne

    private Decision sansPersonne(Soi soi) {
        long tick = soi.tick();
        figeDepuis = -1;
        Memoire.Trace piste = null;
        UUID pisteId = null;
        for (Map.Entry<UUID, Memoire.Trace> e : m.toutes()) {
            Memoire.Trace t = e.getValue();
            // la rancune prolonge la memoire : il n'oublie pas qui l'a blesse
            if (t.derniere != null && tick - t.tickVu <= r.dureeMemoire + t.rancune * 40) {
                if (piste == null || t.tickVu + t.rancune * 10 > piste.tickVu + piste.rancune * 10) {
                    piste = t;
                    pisteId = e.getKey();
                }
            }
        }
        if (piste != null) {
            if (tactique != Tactique.ENQUETE) {
                changer(Tactique.ENQUETE, tick);
                renifle = false;
            }
            double d = soi.pos().distanceH(piste.derniere);
            if (d < 3.0) {
                String anim = renifle ? null : "renifle_piste_sol";
                renifle = true;
                return new Decision(Tactique.ENQUETE, pisteId, null, Allure.ARRET, null, null, false, anim,
                        "flaire la derniere trace");
            }
            return new Decision(Tactique.ENQUETE, pisteId, piste.derniere, Allure.MARCHE, null, null, false,
                    null, "va voir ou il l'a percu pour la derniere fois");
        }
        changer(Tactique.ERRANCE, tick);
        cible = null;
        if (pointErrance == null || tick >= errancePlanifiee || soi.pos().distanceH(pointErrance) < 2) {
            Vec base = soi.eauProfonde() != null && alea.nextDouble() < 0.6 ? soi.eauProfonde() : soi.pos();
            double a = alea.nextDouble() * Math.PI * 2, rr = 6 + alea.nextDouble() * 12;
            pointErrance = base.plus(new Vec(Math.cos(a) * rr, 0, Math.sin(a) * rr));
            errancePlanifiee = tick + 200 + alea.nextInt(200);
        }
        return new Decision(Tactique.ERRANCE, null, pointErrance, soi.dansEau() ? Allure.NAGE : Allure.MARCHE,
                null, null, false, null, "patrouille le long de l'eau");
    }

    // ------------------------------------------------------------------ 4-6. combat

    private Decision combat(Soi soi, List<Joueur> percus) {
        long tick = soi.tick();
        SelecteurCible.Resultat choix = SelecteurCible.choisir(soi, percus, m, r, cible, cibleDepuis);
        if (choix.cible() == null) {
            return sansPersonne(soi);
        }
        Tactique avant = tactique;
        if (!choix.cible().equals(cible)) {
            viser(choix.cible(), tick);
        }
        Joueur j = null;
        for (Joueur p : percus) {
            if (p.id().equals(cible)) {
                j = p;
            }
        }
        double d = soi.pos().distanceH(j.pos());

        // 4. un groupe arrive : rugir d'abord, une fois par rencontre
        int proches = compterProches(soi, percus, r.rayonGroupe);
        Joueur premier = plusProche(soi, percus);
        boolean arrive = premier.pos().distance(soi.pos()) > r.porteeMorsure + 2.5;   // pas encore au contact
        if (!groupeSalue && arrive && proches >= r.surnombre && !soi.attaqueEnCours()
                && ChoixAttaque.dispo(pret, Attaque.RUGISSEMENT, tick)) {
            groupeSalue = true;
            pret.put(Attaque.RUGISSEMENT, tick + Attaque.RUGISSEMENT.recharge);
            changer(Tactique.INTIMIDATION, tick);
            return new Decision(Tactique.INTIMIDATION, cible, null, Allure.ARRET, centre(percus, null),
                    Attaque.RUGISSEMENT, false, null, proches + " joueurs approchent : rugissement");
        }

        // 5. proie seule et distraite : traque ou affut
        Memoire.Trace t = m.connue(j.id());
        boolean enCombat = tick - (t == null ? Long.MIN_VALUE / 2 : t.dernierCoup) < 200
                || m.degatsRecents() > 0 || proches >= 2;
        boolean enChasse = tactique == Tactique.TRAQUE || tactique == Tactique.FIGE
                || tactique == Tactique.AFFUT_EAU || tactique == Tactique.ERRANCE || tactique == Tactique.ENQUETE;
        if (!enCombat && enChasse && d > r.traqueContact) {
            Decision furtif = chasse(soi, j, d, avant);
            if (furtif != null) {
                return furtif;
            }
        }
        figeDepuis = -1;

        // 6. combat
        if (tactique != Tactique.ACCULE) {
            changer(Tactique.ENGAGEMENT, tick);
        }
        blocage(soi, j, d);

        Attaque a = soi.attaqueEnCours() ? null : ChoixAttaque.choisir(soi, j, percus, pret, r);
        if (a != null) {
            pret.put(a, tick + a.recharge);
            Vec regard = a == Attaque.BALAYAGE_QUEUE ? null : j.pos();
            return new Decision(tactique, cible, a == Attaque.CHARGE ? j.pos() : null,
                    a == Attaque.CHARGE ? Allure.CHARGE : Allure.ARRET, regard, a, false, null,
                    raisonAttaque(a, soi, j, percus));
        }

        Vec allies = centre(percus, j.id());
        Allure allure = soi.dansEau() ? Allure.NAGE_RAPIDE : (d > 12 ? Allure.COURSE : Allure.MARCHE);
        if (j.bouclierLeve() && d <= r.porteeGriffes + 3) {
            // bouclier et griffes en recharge : on passe sur le flanc, du cote sans allie
            Vec lat = soi.pos().moins(j.pos()).unitaireH().perpH();
            if (allies != null && lat.scal(allies.moins(j.pos())) > 0) {
                lat = lat.fois(-1);
            }
            changer(Tactique.CONTOURNEMENT, tick);
            return new Decision(Tactique.CONTOURNEMENT, cible, j.pos().plus(lat.fois(r.porteeMorsure * 0.8)),
                    Allure.MARCHE, j.pos(), null, false, null, "contourne le bouclier");
        }
        Vec but = j.pos();
        String comment = "fonce sur sa cible";
        if (allies != null && d < 32) {
            // se placer de l'autre cote de la cible : ses allies doivent la contourner
            Vec cote = j.pos().moins(allies).unitaireH();
            but = j.pos().plus(cote.fois(r.porteeMorsure * 0.7));
            comment = "attaque par le cote oppose a ses allies";
        }
        return new Decision(tactique, cible, but, allure, j.pos(), null, false, null, comment);
    }

    private Decision chasse(Soi soi, Joueur j, double d, Tactique avant) {
        long tick = soi.tick();
        boolean eau = j.dansEau() || (soi.dansEau() && soi.eauProfonde() != null && j.pos().distance(soi.eauProfonde()) < 8);
        if (eau && (soi.dansEau() || soi.submerge())) {
            changer(Tactique.AFFUT_EAU, tick);
            Vec sous = new Vec(j.pos().x(), Math.min(j.pos().y(), soi.pos().y()) - 1.5, j.pos().z());
            return new Decision(Tactique.AFFUT_EAU, cible, sous, Allure.NAGE, j.pos(), null, false, null,
                    "approche sous l'eau, sans remous");
        }
        if (Perception.meRegarde(soi, j, r)) {
            if (figeDepuis < 0) {
                figeDepuis = tick;
            }
            if (tick - figeDepuis > r.figeMax) {
                figeDepuis = -1;
                changer(Tactique.ENGAGEMENT, tick);
                return null;                                 // il a assez attendu : il attaque
            }
            changer(Tactique.FIGE, tick);
            return new Decision(Tactique.FIGE, cible, null, Allure.ARRET, j.pos(), null, false, null,
                    "se fige sous son regard");
        }
        figeDepuis = -1;
        changer(Tactique.TRAQUE, tick);
        String anim = null;
        if (avant == Tactique.ERRANCE || avant == Tactique.ENQUETE) {
            // premiere detection : il tourne brusquement la tete et le fixe en marchant
            Vec v = j.pos().moins(soi.pos());
            double croix = soi.regard().x() * v.z() - soi.regard().z() * v.x();
            anim = croix > 0 ? "marche_regard_fixe_droite" : "marche_regard_fixe_gauche";
        }
        return new Decision(Tactique.TRAQUE, cible, j.pos(), Allure.FEUTREE, j.pos(), null, false, anim,
                "traque une proie qui ne l'a pas vu");
    }

    // ------------------------------------------------------------------ utilitaires

    /** Sans progres vers la cible pendant `delaiBlocage`, elle est jugee inatteignable. */
    private void blocage(Soi soi, Joueur j, double d) {
        long tick = soi.tick();
        if (d <= r.porteeMorsure + 1) {
            meilleureDistance = d;
            tickProgres = tick;
            return;
        }
        if (d < meilleureDistance - 1.0) {
            meilleureDistance = d;
            tickProgres = tick;
        } else if (tick - tickProgres > r.delaiBlocage) {
            m.marquerInatteignable(j.id(), tick + r.dureeInatteignable);
            meilleureDistance = Double.MAX_VALUE;
            tickProgres = tick;
        }
    }

    private void viser(UUID id, long tick) {
        cible = id;
        cibleDepuis = tick;
        meilleureDistance = Double.MAX_VALUE;
        tickProgres = tick;
    }

    private void changer(Tactique t, long tick) {
        if (tactique != t) {
            tactique = t;
            tactiqueDepuis = tick;
        }
    }

    private static int compterProches(Soi soi, List<Joueur> ps, double rayon) {
        int n = 0;
        for (Joueur p : ps) {
            if (p.pos().distance(soi.pos()) <= rayon) {
                n++;
            }
        }
        return n;
    }

    private static Joueur plusProche(Soi soi, List<Joueur> ps) {
        Joueur best = null;
        for (Joueur p : ps) {
            if (best == null || p.pos().distance(soi.pos()) < best.pos().distance(soi.pos())) {
                best = p;
            }
        }
        return best;
    }

    /** Barycentre des joueurs, sauf `exclu` ; null s'il n'en reste aucun. */
    private static Vec centre(List<Joueur> ps, UUID exclu) {
        double x = 0, y = 0, z = 0;
        int n = 0;
        for (Joueur p : ps) {
            if (!p.id().equals(exclu)) {
                x += p.pos().x();
                y += p.pos().y();
                z += p.pos().z();
                n++;
            }
        }
        return n == 0 ? null : new Vec(x / n, y / n, z / n);
    }

    private UUID plusRancunier(List<Joueur> ps) {
        UUID best = null;
        double r0 = 0;
        for (Joueur p : ps) {
            Memoire.Trace t = m.connue(p.id());
            if (t != null && t.rancune > r0) {
                r0 = t.rancune;
                best = p.id();
            }
        }
        return best;
    }

    private String raisonAttaque(Attaque a, Soi soi, Joueur j, List<Joueur> percus) {
        return switch (a) {
            case BALAYAGE_QUEUE -> ChoixAttaque.dansLeDos(soi, percus, r) + " joueur(s) dans le dos : balayage de queue";
            case GRIFFES -> j.bouclierLeve() ? "griffes pour briser le bouclier" : "griffes au contact";
            case SAISIE -> "saisit sa proie dans l'eau";
            case CHARGE -> "charge en ligne droite";
            case BOND -> "bondit pour combler la distance";
            case MORSURE_LATERALE -> "morsure sur le flanc";
            case MORSURE -> "morsure";
            case RUGISSEMENT -> "rugissement";
        };
    }
}
