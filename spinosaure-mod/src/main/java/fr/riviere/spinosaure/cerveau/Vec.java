package fr.riviere.spinosaure.cerveau;

/**
 * Vecteur minimal, sans aucune dependance a Minecraft : le cerveau entier se teste
 * hors du jeu. Repere Minecraft : Y vers le haut, l'horizontale est le plan XZ.
 */
public record Vec(double x, double y, double z) {

    public static final Vec ZERO = new Vec(0, 0, 0);

    public Vec plus(Vec o) {
        return new Vec(x + o.x, y + o.y, z + o.z);
    }

    public Vec moins(Vec o) {
        return new Vec(x - o.x, y - o.y, z - o.z);
    }

    public Vec fois(double k) {
        return new Vec(x * k, y * k, z * k);
    }

    public double scal(Vec o) {
        return x * o.x + y * o.y + z * o.z;
    }

    public double norme() {
        return Math.sqrt(x * x + y * y + z * z);
    }

    public double normeH() {
        return Math.sqrt(x * x + z * z);
    }

    public double distance(Vec o) {
        return moins(o).norme();
    }

    public double distanceH(Vec o) {
        return moins(o).normeH();
    }

    public Vec unitaire() {
        double n = norme();
        return n < 1e-9 ? ZERO : fois(1.0 / n);
    }

    /** Direction horizontale unitaire (Y ecrase). */
    public Vec unitaireH() {
        double n = normeH();
        return n < 1e-9 ? ZERO : new Vec(x / n, 0, z / n);
    }

    /** Rotation de +90 degres dans le plan horizontal (vers la gauche vu du dessus). */
    public Vec perpH() {
        return new Vec(-z, 0, x);
    }

    /** Angle horizontal non signe, en degres, entre deux directions. */
    public static double angleH(Vec a, Vec b) {
        Vec u = a.unitaireH(), v = b.unitaireH();
        if (u == ZERO || v == ZERO) {
            return 0;
        }
        double c = Math.max(-1, Math.min(1, u.scal(v)));
        return Math.toDegrees(Math.acos(c));
    }

    /** Angle 3D non signe, en degres. */
    public static double angle(Vec a, Vec b) {
        Vec u = a.unitaire(), v = b.unitaire();
        if (u == ZERO || v == ZERO) {
            return 0;
        }
        double c = Math.max(-1, Math.min(1, u.scal(v)));
        return Math.toDegrees(Math.acos(c));
    }
}
