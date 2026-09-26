package fr.riviere.spinosaure.cerveau;

/**
 * Vue et ouie. Un joueur accroupi dans le dos du spinosaure peut passer ; un joueur
 * qui sprinte s'entend a 24 blocs, meme cache. C'est ce qui rend la furtivite
 * possible sans que l'IA soit aveugle.
 */
public final class Perception {

    private Perception() {
    }

    public static boolean voit(Soi soi, Joueur j, Reglages r) {
        if (!j.visible()) {
            return false;
        }
        double d = soi.pos().distance(j.pos());
        double portee = r.porteeVue;
        if (soi.submerge() && !j.dansEau()) {
            portee *= r.vueDepuisEau;              // la surface brouille la vue
        }
        if (j.accroupi()) {
            portee *= 0.5;
        }
        if (d > portee) {
            return false;
        }
        Vec versJoueur = j.pos().moins(soi.pos());
        return Vec.angleH(soi.regard(), versJoueur) <= r.coneVue / 2;
    }

    public static boolean entend(Soi soi, Joueur j, Reglages r) {
        double d = soi.pos().distance(j.pos());
        if (d <= r.proximiteSentie) {
            return true;
        }
        double portee = j.sprinte() ? r.ouieSprint : (j.accroupi() ? r.ouieAccroupi : r.ouieMarche);
        if (soi.submerge() != j.dansEau()) {
            portee *= 0.6;                            // l'interface eau/air etouffe les sons
        }
        if (j.dansEau() && !j.accroupi()) {
            portee = Math.max(portee, r.ouieNage);    // les remous portent, quel que soit le milieu
        }
        return d <= portee;
    }

    public static boolean percoit(Soi soi, Joueur j, Reglages r) {
        return voit(soi, j, r) || entend(soi, j, r);
    }

    /** Le joueur a-t-il les yeux poses sur le spinosaure ? */
    public static boolean meRegarde(Soi soi, Joueur j, Reglages r) {
        if (!j.visible()) {
            return false;
        }
        Vec versMoi = soi.pos().plus(new Vec(0, 2.5, 0)).moins(j.pos());
        return Vec.angle(j.regard(), versMoi) <= r.angleRegard;
    }
}
