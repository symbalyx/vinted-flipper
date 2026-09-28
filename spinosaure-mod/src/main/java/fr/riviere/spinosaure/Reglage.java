package fr.riviere.spinosaure;

import net.minecraftforge.common.ForgeConfigSpec;

/**
 * Reglages du serveur, dans config/spinosaure-common.toml (cree au premier lancement,
 * modifiable sans recompiler). Ne concernent que l'apparition NATURELLE : l'oeuf et
 * /summon ne sont jamais limites.
 */
public final class Reglage {

    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.BooleanValue APPARITION_NATURELLE;
    public static final ForgeConfigSpec.IntValue MAX_PAR_ZONE;
    public static final ForgeConfigSpec.IntValue RAYON_ZONE;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.push("apparition");
        APPARITION_NATURELLE = b.comment("Le spinosaure apparait-il tout seul en jungle ? (false pour un evenement ou on les place a la main)")
                .define("naturelle", true);
        MAX_PAR_ZONE = b.comment("Nombre maximum de spinosaures dans une zone (rayon ci-dessous) pour qu'un nouveau apparaisse")
                .defineInRange("max_par_zone", 1, 0, 64);
        RAYON_ZONE = b.comment("Rayon de la zone, en blocs (compte a l'horizontale)")
                .defineInRange("rayon_zone", 160, 16, 2048);
        b.pop();
        SPEC = b.build();
    }

    private Reglage() {
    }
}
