package fr.riviere.spinosaure.cerveau;

import java.util.ArrayDeque;
import java.util.Collection;
import java.util.Deque;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Ce que le spinosaure retient de chaque joueur :
 * <ul>
 *   <li>la derniere position percue (pour aller voir ou il s'est cache) ;</li>
 *   <li>la MENACE, qui decroit vite : qui est dangereux en ce moment ;</li>
 *   <li>la RANCUNE, qui decroit tres lentement : qui l'a blesse, pour plus tard ;</li>
 *   <li>les coups a distance recus alors que le tireur etait inatteignable.</li>
 * </ul>
 */
public final class Memoire {

    public static final class Trace {
        public Vec derniere;
        public long tickVu = Long.MIN_VALUE / 2;
        public double menace;
        public double rancune;
        public long inatteignableJusqua = Long.MIN_VALUE / 2;
        final Deque<Long> tirsInatteignables = new ArrayDeque<>();
        public long dernierCoup = Long.MIN_VALUE / 2;
        /** Temps cumule passe a traquer ce joueur (ticks) : fait avancer les phases. */
        public double tension;
        long tickTension = Long.MIN_VALUE / 2;
    }

    private final Map<UUID, Trace> traces = new HashMap<>();
    private final Reglages r;
    private long dernierTick = Long.MIN_VALUE;
    /** Degats recus recemment, pour juger si l'echange tourne mal. */
    private final Deque<long[]> degatsRecents = new ArrayDeque<>();

    public Memoire(Reglages r) {
        this.r = r;
    }

    public Trace de(UUID id) {
        return traces.computeIfAbsent(id, k -> new Trace());
    }

    public Trace connue(UUID id) {
        return traces.get(id);
    }

    public Collection<Map.Entry<UUID, Trace>> toutes() {
        return traces.entrySet();
    }

    /** Fait decroitre menace et rancune depuis le dernier appel. */
    public void vieillir(long tick) {
        if (dernierTick != Long.MIN_VALUE && tick > dernierTick) {
            long dt = tick - dernierTick;
            double km = Math.pow(0.5, dt / r.demiVieMenace);
            double kr = Math.pow(0.5, dt / r.demiVieRancune);
            double kt = Math.pow(0.5, dt / r.demiVieTension);
            for (Trace t : traces.values()) {
                t.menace *= km;
                t.rancune *= kr;
                if (tick - t.tickTension > 40) {
                    t.tension *= kt;                 // elle ne retombe que hors de vue
                }
            }
        }
        dernierTick = tick;
        while (!degatsRecents.isEmpty() && tick - degatsRecents.peekFirst()[0] > 200) {
            degatsRecents.pollFirst();
        }
    }

    public void vu(UUID id, Vec pos, long tick) {
        Trace t = de(id);
        t.derniere = pos;
        t.tickVu = tick;
    }

    public void blesse(UUID id, double montant, boolean aDistance, boolean tireurAtteignable, long tick) {
        Trace t = de(id);
        t.menace += montant * (aDistance ? r.poidsDistance : 1.0);
        t.rancune += montant;
        t.dernierCoup = tick;
        if (aDistance && !tireurAtteignable) {
            t.tirsInatteignables.addLast(tick);
        }
        degatsRecents.addLast(new long[]{tick, Math.round(montant * 100)});
    }

    /** Nombre de tirs recus de ce joueur, inatteignable, dans la fenetre recente. */
    public int tirsInatteignables(UUID id, long tick) {
        Trace t = traces.get(id);
        if (t == null) {
            return 0;
        }
        while (!t.tirsInatteignables.isEmpty() && tick - t.tirsInatteignables.peekFirst() > r.fenetreTireur) {
            t.tirsInatteignables.pollFirst();
        }
        return t.tirsInatteignables.size();
    }

    /** Somme des degats recus dans les 10 dernieres secondes (points de vie). */
    public double degatsRecents() {
        double s = 0;
        for (long[] d : degatsRecents) {
            s += d[1] / 100.0;
        }
        return s;
    }

    /** Accumule la tension sur la proie traquee (vue sans interruption de plus de 2 s). */
    public void traquer(UUID id, long tick) {
        Trace t = de(id);
        if (tick - t.tickTension <= 40) {
            t.tension += tick - t.tickTension;
        }
        t.tickTension = tick;
    }

    public boolean inatteignable(UUID id, long tick) {
        Trace t = traces.get(id);
        return t != null && tick < t.inatteignableJusqua;
    }

    public void marquerInatteignable(UUID id, long jusqua) {
        de(id).inatteignableJusqua = jusqua;
    }

    public void oublier(UUID id) {
        traces.remove(id);
    }
}
