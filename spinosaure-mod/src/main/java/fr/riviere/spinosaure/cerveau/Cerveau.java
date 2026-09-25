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
    private long dernierContact = Long.MIN_VALUE / 2;
    private Vec pointErrance;
    private long errancePlanifiee = Long.MIN_VALUE / 2;
    private boolean renifle;

    /** Centre du territoire : premiere position connue, ou fixe par l'entite (sauvegarde). */
    private Vec territoire;
    /** Derniers points d'errance visites : il ne tourne pas en rond. */
    private final java.util.ArrayDeque<Vec> visites = new java.util.ArrayDeque<>();
    /** Destinations physiquement bloquees, evitees jusqu'a expiration. */
    private final List<long[]> interditsExpiration = new ArrayList<>();
    private final List<Vec> interdits = new ArrayList<>();
    /** Frappe eclair en cours (hit and run) et disparition. */
    private long frappeJusqua = Long.MIN_VALUE / 2;
    private boolean frappeOuverte;
    private int attaquesFrappe;
    private double santeDebutFrappe;
    private long disparaitJusqua = Long.MIN_VALUE / 2;
    private String raisonDisparition = "";
    private long dernierePose = Long.MIN_VALUE / 2;
    /** Sens dans lequel il tourne autour de sa proie (+1 / -1), revu toutes les 3 s. */
    private int sens = 1;
    private long sensDepuis = Long.MIN_VALUE / 2;
    /** Derniere destination demandee au corps (pour savoir quoi abandonner). */
    private Vec derniereDestination;

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

    public void definirTerritoire(Vec centre) {
        territoire = centre;
    }

    public Vec territoire() {
        return territoire;
    }

    /**
     * Le corps n'arrive pas a atteindre la destination demandee malgre saut, recul et
     * contournement : on la raye pour un moment et on en choisit une autre.
     */
    public void destinationBloquee(long tick) {
        Vec d = derniereDestination;
        if (d == null) {
            return;
        }
        interdits.add(d);
        interditsExpiration.add(new long[]{tick + 1200});
        if (cible != null && (tactique == Tactique.ENGAGEMENT || tactique == Tactique.CONTOURNEMENT
                || tactique == Tactique.TRAQUE || tactique == Tactique.ACCULE)) {
            m.marquerInatteignable(cible, tick + r.dureeInatteignable);
        }
        if (tactique == Tactique.ERRANCE || tactique == Tactique.ENQUETE) {
            visites.addLast(d);
            pointErrance = null;
        }
    }

    private boolean interdit(Vec p, long tick) {
        for (int i = interdits.size() - 1; i >= 0; i--) {
            if (interditsExpiration.get(i)[0] <= tick) {
                interdits.remove(i);
                interditsExpiration.remove(i);
            } else if (interdits.get(i).distanceH(p) < 5) {
                return true;
            }
        }
        return false;
    }

    /** Le corps a du lacher (mort, deconnexion, teleportation...). */
    public void priseRompue(long tick) {
        tenu = null;
        changer(Tactique.ENGAGEMENT, tick);
    }

    // ================================================================== reflexion

    public Decision penser(Soi soi, List<Joueur> joueurs, List<Evenement> evts) {
        Decision d = reflechir(soi, joueurs, evts);
        derniereDestination = d.destination();
        return d;
    }

    private Decision reflechir(Soi soi, List<Joueur> joueurs, List<Evenement> evts) {
        long tick = soi.tick();
        m.vieillir(tick);
        if (territoire == null) {
            territoire = soi.pos();
        }

        Map<UUID, Joueur> parId = new HashMap<>();
        for (Joueur j : joueurs) {
            parId.put(j.id(), j);
        }
        List<Joueur> percus = new ArrayList<>();
        List<Joueur> observes = new ArrayList<>();
        for (Joueur j : joueurs) {
            if (Perception.percoit(soi, j, r)) {
                (j.inoffensif() ? observes : percus).add(j);
            }
        }
        for (Evenement e : evts) {
            if (e instanceof Evenement.Degats d) {
                Joueur j = parId.get(d.source());
                boolean atteignable = j == null || (j.atteignable() && !m.inatteignable(j.id(), tick));
                m.blesse(d.source(), d.montant(), d.aDistance(), atteignable, tick);
                if (j != null && !j.inoffensif() && !percus.contains(j)) {
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
            if (!observes.isEmpty() && !(tactique == Tactique.ENQUETE && m.degatsRecents() > 0)) {
                return observer(soi, observes);
            }
            return sansPersonne(soi);
        }
        return combat(soi, percus);
    }

    /**
     * Joueur en creatif : il ne peut pas le blesser, mais il ne l'ignore pas. Il le fixe,
     * le suit a distance a pas feutres et se fige des qu'on le regarde. Le comportement
     * de traque reste visible en creatif ; le combat se teste en survie.
     */
    private Decision observer(Soi soi, List<Joueur> observes) {
        long tick = soi.tick();
        Joueur j = plusProche(soi, observes);
        Tactique avant = tactique;
        double d = soi.pos().distanceH(j.pos());
        if (Perception.meRegarde(soi, j, r)) {
            changer(Tactique.FIGE, tick);
            return new Decision(Tactique.FIGE, j.id(), null, Allure.ARRET, j.pos(), null, false, null,
                    "se fige sous le regard d'un joueur en creatif");
        }
        changer(Tactique.TRAQUE, tick);
        String anim = null;
        if (avant == Tactique.ERRANCE || avant == Tactique.ENQUETE) {
            Vec v = j.pos().moins(soi.pos());
            anim = soi.regard().x() * v.z() - soi.regard().z() * v.x() > 0
                    ? "marche_regard_fixe_droite" : "marche_regard_fixe_gauche";
        }
        if (d < 14) {
            return new Decision(Tactique.TRAQUE, j.id(), null, Allure.ARRET, j.pos(), null, false, anim,
                    "observe un joueur en creatif (il ne l'attaque pas)");
        }
        Vec but = j.pos().plus(soi.pos().moins(j.pos()).unitaireH().fois(14));
        return new Decision(Tactique.TRAQUE, j.id(), but, Allure.FEUTREE, j.pos(), null, false, anim,
                "suit un joueur en creatif a distance");
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
        Vec eau = choisirEau(soi, percus, tenu);
        if (eau != null && !soi.submerge()) {
            but = eau;
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
        Vec eau = choisirEau(soi, percus, null);
        if (eau == null && !soi.submerge()) {
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
        // (pas d'animation « plonge » ici : elle enfonce le corps de 4 blocs, faite pour
        //  un animal immobile en surface, elle le ferait traverser le sol en courant)
        return new Decision(Tactique.REPLI, null, eau, a, null, null, false, null,
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
        Vec eau = choisirEau(soi, percus, null);
        if (eau != null || soi.submerge()) {
            but = soi.submerge() ? soi.pos().plus(new Vec(0, -2, 0)) : eau;
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
            if (pointErrance != null) {
                visites.addLast(pointErrance);
                while (visites.size() > 6) {
                    visites.removeFirst();
                }
            }
            pointErrance = choisirErrance(soi);
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
        Vec devant = interception(soi, j, d > 12 ? Allure.COURSE : Allure.MARCHE);

        // 4-5. horreur : observer, filer, disparaitre... et frapper seulement a l'ouverture
        if (frappeOuverte && tick > frappeJusqua + 40) {
            frappeOuverte = false;              // perimee (repli, maintien... entre-temps) : on la referme
        }
        boolean frappe = frappeOuverte && tick < frappeJusqua;
        boolean finie = frappeOuverte && (tick >= frappeJusqua || attaquesFrappe >= r.attaquesParFrappe
                || santeDebutFrappe - soi.sante() >= r.degatsFinFrappe);
        if (finie && tactique != Tactique.ACCULE) {
            // frappe eclair terminee (coups portes, riposte encaissee ou temps ecoule) :
            // il ne reste pas se battre, il s'efface
            frappeOuverte = false;
            frappeJusqua = Long.MIN_VALUE / 2;
            Memoire.Trace t = m.de(j.id());
            t.tension = Math.min(t.tension, r.phaseFilature);          // il reprend la traque de zero ou presque
            return disparaitre(soi, percus, j, true, "a frappe, il s'efface avant qu'on riposte");
        }
        if (!frappe && tactique != Tactique.ACCULE) {
            Decision h = horreur(soi, percus, j, d, avant);
            if (h != null) {
                return h;
            }
        }
        figeDepuis = -1;

        // 6. frappe eclair (ou combat accule)
        if (tactique != Tactique.ACCULE) {
            changer(Tactique.ENGAGEMENT, tick);
        }
        blocage(soi, j, d);

        Attaque a = soi.attaqueEnCours() ? null : ChoixAttaque.choisir(soi, j, percus, pret, r);
        if (a != null) {
            pret.put(a, tick + a.recharge);
            attaquesFrappe++;
            Vec regard = a == Attaque.BALAYAGE_QUEUE ? null : j.pos();
            return new Decision(tactique, cible, a == Attaque.CHARGE ? interception(soi, j, Allure.CHARGE) : null,
                    a == Attaque.CHARGE ? Allure.CHARGE : Allure.ARRET, regard, a, false, null,
                    raisonAttaque(a, soi, j, percus));
        }

        Vec allies = centre(percus, j.id());
        // il court jusqu'a portee : la marche a 1.5 bloc/s se lisait comme de l'indifference
        Allure allure = soi.dansEau() ? Allure.NAGE_RAPIDE : (d > r.porteeMorsure + 1 ? Allure.COURSE : Allure.MARCHE);
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
        if (d <= r.porteeMorsure * 0.9) {
            // a portee, attaques en recharge : il ne pousse pas contre le joueur (ce qui le
            // faisait se croire bloque et reculer) ; il tourne autour, cote oppose aux allies
            Vec rayon = soi.pos().moins(j.pos()).unitaireH();
            if (rayon == Vec.ZERO) {
                rayon = soi.regard().fois(-1);
            }
            if (tick - sensDepuis > 60) {
                sens = allies != null && rayon.perpH().scal(allies.moins(j.pos())) > 0 ? -1 : (alea.nextBoolean() ? 1 : -1);
                sensDepuis = tick;
            }
            double pas = Math.toRadians(35) * sens;
            Vec tourne = new Vec(rayon.x() * Math.cos(pas) - rayon.z() * Math.sin(pas), 0,
                    rayon.x() * Math.sin(pas) + rayon.z() * Math.cos(pas));
            return new Decision(tactique, cible, j.pos().plus(tourne.fois(r.porteeMorsure * 0.75)), Allure.MARCHE,
                    j.pos(), null, false, null, "tourne autour de sa proie en attendant l'ouverture");
        }
        Vec but = devant;
        String comment = devant.distanceH(j.pos()) > 1.5 ? "coupe la route de sa cible" : "fonce sur sa cible";
        if (allies != null && d < 32) {
            // se placer de l'autre cote de la cible : ses allies doivent la contourner
            Vec cote = j.pos().moins(allies).unitaireH();
            but = devant.plus(cote.fois(r.porteeMorsure * 0.7));
            comment = "attaque par le cote oppose a ses allies";
        }
        return new Decision(tactique, cible, but, allure, j.pos(), null, false, null, comment);
    }

    /**
     * Le coeur du mod d'horreur. Renvoie null quand il faut frapper (la frappe eclair est
     * alors ouverte et le code de combat prend le relais).
     */
    private Decision horreur(Soi soi, List<Joueur> percus, Joueur j, double d, Tactique avant) {
        long tick = soi.tick();
        Memoire.Trace t = m.de(j.id());
        for (Joueur p : percus) {
            m.traquer(p.id(), tick);              // il les surveille tous : celui qui s'isolera est deja « mur »
        }

        // en train de s'effacer : il finit de disparaitre
        if (tick < disparaitJusqua) {
            return disparaitre(soi, percus, j, false, raisonDisparition);
        }
        // blesse : au contact il riposte, de loin il se derobe
        Joueur agresseur = null;
        for (Joueur p : percus) {
            Memoire.Trace tp = m.connue(p.id());
            if (tp != null && tick - tp.dernierCoup < 40 && (agresseur == null
                    || p.pos().distanceH(soi.pos()) < agresseur.pos().distanceH(soi.pos()))) {
                agresseur = p;
            }
        }
        if (agresseur != null) {
            if (agresseur.pos().distanceH(soi.pos()) <= r.distanceRiposte) {
                ouvrirFrappe(soi);
                return null;
            }
            t.tension += 300;                               // il reviendra, plus decide
            return commencerDisparition(soi, percus, j, "blesse de loin : il se derobe");
        }
        // l'eau est son domaine : il y approche par en dessous et saisit
        if (j.dansEau() && (soi.dansEau() || soi.submerge())) {
            if (d <= r.porteeSaisie + 2) {
                ouvrirFrappe(soi);
                return null;
            }
            changer(Tactique.AFFUT_EAU, tick);
            Vec sous = new Vec(j.pos().x(), Math.min(j.pos().y(), soi.pos().y()) - 1.5, j.pos().z());
            return new Decision(Tactique.AFFUT_EAU, cible, sous, Allure.NAGE, j.pos(), null, false, null,
                    "approche sous l'eau, sans remous");
        }

        int phase = t.tension < r.phaseFilature ? 1 : (t.tension < r.phaseFrappe ? 2 : 3);
        double allie = Double.MAX_VALUE;
        for (Joueur p : percus) {
            if (!p.id().equals(j.id())) {
                allie = Math.min(allie, p.pos().distanceH(j.pos()));
            }
        }
        boolean isole = allie > r.isolementFrappe;
        boolean regarde = Perception.meRegarde(soi, j, r);

        // l'ouverture : proie isolee (ou traque interminable), dos tourne, assez pres
        boolean ouverture = phase == 3 && !regarde && d <= r.distanceFrappe && (isole || t.tension >= r.tensionGroupe);
        ouverture |= phase >= 2 && isole && j.sante() < 0.35 && d <= r.distanceFrappe;     // proie affaiblie
        if (ouverture) {
            ouvrirFrappe(soi);
            return null;
        }
        // on le regarde : de pres il disparait, de loin il se fige et soutient le regard
        if (regarde) {
            if (d <= r.distanceDisparition) {
                return commencerDisparition(soi, percus, j, "vu de trop pres : il disparait");
            }
            if (figeDepuis < 0) {
                figeDepuis = tick;
            }
            if (tick - figeDepuis > r.figeMax) {
                figeDepuis = -1;
                return commencerDisparition(soi, percus, j, "soutient le regard puis s'efface");
            }
            changer(Tactique.FIGE, tick);
            return new Decision(Tactique.FIGE, cible, null, Allure.ARRET, j.pos(), null, false, null,
                    "se fige et soutient ton regard");
        }
        figeDepuis = -1;

        String anim = null;
        if (avant == Tactique.ERRANCE || avant == Tactique.ENQUETE) {
            // premiere detection : il tourne brusquement la tete et le fixe en marchant
            Vec v = j.pos().moins(soi.pos());
            anim = soi.regard().x() * v.z() - soi.regard().z() * v.x() > 0
                    ? "marche_regard_fixe_droite" : "marche_regard_fixe_gauche";
        }
        // phase 1, ou un groupe qui le tient a distance : il observe de loin, planque
        if (phase == 1 || (!isole && t.tension < r.tensionGroupe)) {
            changer(Tactique.OBSERVATION, tick);
            Vec poste = posteObservation(soi, j);
            if (poste.distanceH(soi.pos()) < 3) {
                if (anim == null && tick - dernierePose > 400 && alea.nextInt(3) == 0) {
                    anim = "tete_inclinee_fixe";                     // la tete qui se penche...
                    dernierePose = tick;
                }
                return new Decision(Tactique.OBSERVATION, cible, null, Allure.ARRET, j.pos(), null, false, anim,
                        isole ? "t'observe de loin" : "un groupe : il observe et attend qu'un joueur s'isole");
            }
            Allure a = soi.dansEau() ? Allure.NAGE : (poste.distanceH(soi.pos()) > 10 ? Allure.MARCHE : Allure.FEUTREE);
            return new Decision(Tactique.OBSERVATION, cible, poste, a, j.pos(), null, false, anim,
                    "gagne un poste d'observation");
        }
        // phases 2 et 3 : il la file, derriere elle, hors de son champ de vision
        changer(Tactique.FILATURE, tick);
        double recul = phase == 3 ? r.distanceFilatureProche : r.distanceFilature;
        Vec dos = new Vec(j.regard().x(), 0, j.regard().z()).unitaireH();
        Vec poste = dos == Vec.ZERO ? j.pos().plus(soi.pos().moins(j.pos()).unitaireH().fois(recul))
                : j.pos().moins(dos.fois(recul));
        if (poste.distanceH(soi.pos()) < 2.5) {
            return new Decision(Tactique.FILATURE, cible, null, Allure.ARRET, j.pos(), null, false, anim,
                    phase == 3 ? "juste derriere toi, il attend l'ouverture" : "te suit, derriere toi");
        }
        Allure a = soi.dansEau() ? Allure.NAGE : (poste.distanceH(soi.pos()) > 20 ? Allure.MARCHE : Allure.FEUTREE);
        return new Decision(Tactique.FILATURE, cible, interceptionPoint(poste, j), a, j.pos(), null, false, anim,
                phase == 3 ? "se rapproche dans ton dos" : "te file a distance, sans bruit");
    }

    /** Le poste suit le deplacement de la proie : on vise ou il sera. */
    private static Vec interceptionPoint(Vec poste, Joueur j) {
        Vec v = j.vitesse() == null ? Vec.ZERO : new Vec(j.vitesse().x(), 0, j.vitesse().z());
        return poste.plus(v.fois(20));
    }

    /**
     * Poste d'observation : a ~28 blocs de la proie, de preference dans l'eau (il y guette,
     * a demi immerge) ; sinon dans l'axe ou il se trouve deja.
     */
    private Vec posteObservation(Soi soi, Joueur j) {
        Vec best = null;
        double bestScore = -Double.MAX_VALUE;
        for (PointTerrain p : soi.voisinage()) {
            double dj = p.pos().distanceH(j.pos());
            if (p.danger() || dj < r.distanceObservation - 6 || dj > r.distanceObservation + 8 || interdit(p.pos(), soi.tick())) {
                continue;
            }
            double s = (p.eau() ? 4 : 0) - Math.abs(dj - r.distanceObservation) * 0.3 - p.pos().distanceH(soi.pos()) * 0.1;
            if (s > bestScore) {
                bestScore = s;
                best = p.pos();
            }
        }
        if (best != null) {
            return best;
        }
        Vec axe = soi.pos().moins(j.pos()).unitaireH();
        if (axe == Vec.ZERO) {
            axe = soi.regard().fois(-1);
        }
        return j.pos().plus(axe.fois(r.distanceObservation));
    }

    private void ouvrirFrappe(Soi soi) {
        frappeOuverte = true;
        frappeJusqua = soi.tick() + r.dureeFrappe;
        attaquesFrappe = 0;
        santeDebutFrappe = soi.sante();
        disparaitJusqua = Long.MIN_VALUE / 2;
    }

    private Decision commencerDisparition(Soi soi, List<Joueur> percus, Joueur j, String raison) {
        disparaitJusqua = soi.tick() + r.dureeDisparition;
        raisonDisparition = raison;
        return disparaitre(soi, percus, j, true, raison);
    }

    /** Il s'efface : sous l'eau s'il y en a, sinon loin, a l'oppose de la proie. */
    private Decision disparaitre(Soi soi, List<Joueur> percus, Joueur j, boolean debut, String raison) {
        long tick = soi.tick();
        if (debut && disparaitJusqua < tick) {
            disparaitJusqua = tick + r.dureeDisparition;
            raisonDisparition = raison;
        }
        changer(Tactique.DISPARITION, tick);
        Vec eau = choisirEau(soi, percus, null);
        Vec but;
        if (soi.submerge()) {
            but = soi.pos().plus(soi.pos().moins(j.pos()).unitaireH().fois(6)).plus(new Vec(0, -2, 0));
        } else if (eau != null && eau.distanceH(soi.pos()) < 40) {
            but = eau;
        } else {
            Vec fuite = soi.pos().moins(j.pos()).unitaireH();
            if (fuite == Vec.ZERO) {
                fuite = soi.regard().fois(-1);
            }
            but = soi.pos().plus(fuite.fois(32));
        }
        Allure a = soi.dansEau() ? Allure.NAGE_RAPIDE : Allure.COURSE;
        return new Decision(Tactique.DISPARITION, cible, but, a, null, null, false, null, raison);
    }

    // ------------------------------------------------------------------ deplacement

    /**
     * Ou sera la cible quand il l'atteindra : sa position plus sa vitesse multipliee par
     * le temps de trajet (plafonne a 1.5 s pour ne pas partir sur une extrapolation folle).
     * Un joueur qui fuit en ligne droite se fait couper la route au lieu d'etre suivi.
     */
    Vec interception(Soi soi, Joueur j, Allure allure) {
        Vec v = j.vitesse() == null ? Vec.ZERO : new Vec(j.vitesse().x(), 0, j.vitesse().z());
        if (v.normeH() < 0.02) {
            return j.pos();
        }
        double mienne = Math.max(Pilote.vitesseSol(allure.vitesse), 0.05);
        double t = Math.min(soi.pos().distanceH(j.pos()) / mienne, 30);
        return j.pos().plus(v.fois(t));
    }

    /**
     * Eau profonde ou se refugier. Pas forcement la plus proche : celle qui l'eloigne des
     * joueurs, et surtout pas une eau qu'il faudrait atteindre en leur passant au travers.
     */
    Vec choisirEau(Soi soi, List<Joueur> percus, UUID ignorer) {
        List<Vec> candidats = new ArrayList<>();
        for (PointTerrain p : soi.voisinage()) {
            if (p.profonde() && !p.danger()) {
                candidats.add(p.pos());
            }
        }
        if (soi.eauProfonde() != null) {
            candidats.add(soi.eauProfonde());
        }
        Vec best = null;
        double bestScore = -Double.MAX_VALUE;
        for (Vec c : candidats) {
            if (interdit(c, soi.tick())) {
                continue;
            }
            double s = -soi.pos().distanceH(c);
            for (Joueur j : percus) {
                if (j.id().equals(ignorer)) {
                    continue;
                }
                s += 1.5 * Math.min(j.pos().distanceH(c), 20) / Math.max(1, percus.size());
                if (distanceSegment(j.pos(), soi.pos(), c) < 5) {
                    s -= 30;                    // il faudrait leur passer au travers
                }
            }
            if (s > bestScore) {
                bestScore = s;
                best = c;
            }
        }
        return best;
    }

    /**
     * Point d'errance : il patrouille les berges de son territoire. Jamais une falaise ni de
     * la lave, pas un point visite recemment, et il revient vers son territoire s'il s'en
     * eloigne. Sans terrain echantillonne, un point au hasard autour de l'eau.
     */
    Vec choisirErrance(Soi soi) {
        Vec best = null;
        double bestScore = -Double.MAX_VALUE;
        for (PointTerrain p : soi.voisinage()) {
            if (p.danger() || Math.abs(p.denivele()) > 4 || interdit(p.pos(), soi.tick())) {
                continue;
            }
            double s = alea.nextDouble() * 2;
            if (p.rive()) {
                s += 3;
            } else if (p.profonde()) {
                s += 1.5;
            }
            if (territoire != null) {
                s -= 0.15 * Math.max(0, p.pos().distanceH(territoire) - 32);
            }
            for (Vec v : visites) {
                if (v.distanceH(p.pos()) < 10) {
                    s -= 4;
                }
            }
            if (s > bestScore) {
                bestScore = s;
                best = p.pos();
            }
        }
        if (best != null) {
            return best;
        }
        Vec base = soi.eauProfonde() != null && alea.nextDouble() < 0.6 ? soi.eauProfonde() : soi.pos();
        double a = alea.nextDouble() * Math.PI * 2, rr = 6 + alea.nextDouble() * 12;
        return base.plus(new Vec(Math.cos(a) * rr, 0, Math.sin(a) * rr));
    }

    /** Distance horizontale du point p au segment [a, b]. */
    static double distanceSegment(Vec p, Vec a, Vec b) {
        Vec ab = new Vec(b.x() - a.x(), 0, b.z() - a.z());
        Vec ap = new Vec(p.x() - a.x(), 0, p.z() - a.z());
        double l2 = ab.scal(ab);
        double t = l2 < 1e-9 ? 0 : Math.max(0, Math.min(1, ap.scal(ab) / l2));
        return ap.moins(ab.fois(t)).normeH();
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
