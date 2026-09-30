package fr.riviere.spinosaure.cerveau;

import java.util.List;
import java.util.Map;

/**
 * Repertoire des animations du modele et de leur usage. Un test verifie que chaque animation
 * du fichier est jouee quelque part, ou ecartee pour une raison ecrite ici, et que chaque nom
 * demande par le cerveau est bien enregistre (un nom non enregistre est ignore sans bruit par
 * GeckoLib : c'est ainsi que « tete_inclinee_fixe » n'a jamais ete jouee).
 */
public final class Animations {

    private Animations() {
    }

    /** Ponctuelles, controleur « ambiance » : demandees par le cerveau ou par le corps. */
    public static final List<String> AMBIANCES = List.of(
            // traque, perception
            "renifle_piste_sol", "renifle_air", "ecoute_joueur", "marche_regard_fixe_droite",
            "marche_regard_fixe_gauche", "tete_inclinee_fixe", "spasmes_cou", "hurle_court", "hurle_long",
            "communication_congeneres", "inspecte_obstacle",
            // coups recus, proie
            "degats", "degats_eau", "secoue_proie", "mange_carcasse", "mange_carcasse_regard_droite",
            "mange_carcasse_regard_gauche", "rugissement_territorial_cinematique",
            // repos et sommeil
            "se_couche_ror", "se_releve_ror", "endormissement", "reveil",
            // deplacements
            "ralentissement_course_arret", "saut", "attaque_saut_sol_ror",
            // eau
            "entree_eau", "plongeon_rapide", "plongeon_hauteur", "plonge", "remonte_surface",
            "emergence_lente", "sortie_eau_terre_redressement", "secoue_eau", "boit", "peche_gueule_eau");

    /**
     * Nom symbolique demande par le cerveau a l'arrivee d'un point d'errance : le corps choisit
     * selon ce qui l'entoure (peche dans l'eau, boit au bord, appelle un congenere, flaire...).
     */
    public static final String PAUSE_ERRANCE = "pause_errance";

    /** Attaques, controleur « action » : le repertoire et ses variantes selon le terrain. */
    public static final List<String> ACTIONS = List.of(
            "morsure_rapide", "morsure_laterale", "coup_griffes_double", "coup_de_queue_pivot", "bond_joueur",
            "saisie_joueur", "hurle_intimidation",
            "coup_griffes_gauche_ror", "coup_griffes_droit_ror", "frappe_queue_eau", "embuscade_jaillissement",
            "dash_morsure_bateau", "attaque_saut_eau_ror", "bond_hors_eau_ror", "saut_attaque_hors_eau",
            "rugit_en_nageant_ror");

    /** En boucle, controleur « mouvement » (choisies d'apres la tactique, l'allure et le milieu). */
    public static final List<String> MOUVEMENTS = List.of(
            "repos", "respiration_lourde", "fige_en_traque", "traque_lente", "tourne_sur_place", "chute",
            "marche", "marche_boiteuse", "marche_feutree", "marche_observation", "avance_menacante", "grimpe",
            "course", "hurle_en_courant", "ruee_griffes_ror", "charge", "virage_serre_droite", "virage_serre_gauche",
            "maintien_joueur", "dort", "assis_ror", "mort", "mort_eau",
            "marche_eau_peu_profonde", "nage_surface", "nage_sous_eau", "nage_rapide_ror", "affut_eau",
            "traque_eau_affleurante");

    /** Ecartees, avec la raison. */
    public static final Map<String, String> ECARTEES = Map.of(
            "pose_reference", "pose de reference de la modelisation, pas une animation",
            "creuse_enfouissement", "le modele descend de 10 blocs sous ses pieds : il faudrait creuser le terrain",
            "sort_terre_quatre_pattes", "sortie d'enfouissement : meme raison",
            "creuse_et_ressort_quatre_pattes", "enfouissement complet : meme raison",
            "nage_derive_ror", "corps cabre de 35 degres, queue pendante : se lisait comme une escalade pendant la nage",
            "capture_joueur_sous_eau", "modele abaisse de 3 blocs : le joueur tenu (a hauteur de la machoire de la "
                    + "boite de collision) flotterait hors de la gueule",
            "transport_joueur_sous_eau", "meme raison que la capture sous l'eau");
}
