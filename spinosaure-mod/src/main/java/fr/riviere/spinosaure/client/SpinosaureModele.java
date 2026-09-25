package fr.riviere.spinosaure.client;

import fr.riviere.spinosaure.SpinosaureMod;
import fr.riviere.spinosaure.entite.SpinosaureEntity;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.model.data.EntityModelData;

/** Fichiers exportes depuis Blockbench (voir LISEZMOI.md). */
public class SpinosaureModele extends GeoModel<SpinosaureEntity> {

    private static final ResourceLocation GEO = new ResourceLocation(SpinosaureMod.MODID, "geo/spinosaure.geo.json");
    private static final ResourceLocation TEXTURE = new ResourceLocation(SpinosaureMod.MODID, "textures/entity/spinosaure.png");
    private static final ResourceLocation ANIMATIONS = new ResourceLocation(SpinosaureMod.MODID, "animations/spinosaure.animation.json");

    @Override
    public ResourceLocation getModelResource(SpinosaureEntity spino) {
        return GEO;
    }

    @Override
    public ResourceLocation getTextureResource(SpinosaureEntity spino) {
        return TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(SpinosaureEntity spino) {
        return ANIMATIONS;
    }

    /**
     * La tete suit ce qu'il regarde (sa cible, le joueur qu'il observe), PAR-DESSUS
     * l'animation en cours : 40 % sur le cou, 60 % sur la tete, lacet borne a 55 degres et
     * tangage a 25. C'est ce qui montre au joueur qu'il est repere.
     */
    @Override
    public void setCustomAnimations(SpinosaureEntity spino, long instanceId, AnimationState<SpinosaureEntity> etat) {
        super.setCustomAnimations(spino, instanceId, etat);
        EntityModelData donnees = etat.getData(DataTickets.ENTITY_MODEL_DATA);
        if (donnees == null || spino.isDeadOrDying()) {
            return;
        }
        float lacet = Mth.clamp(donnees.netHeadYaw(), -55F, 55F) * Mth.DEG_TO_RAD;
        float tangage = Mth.clamp(donnees.headPitch(), -25F, 25F) * Mth.DEG_TO_RAD;
        CoreGeoBone cou = getAnimationProcessor().getBone("neck");
        CoreGeoBone tete = getAnimationProcessor().getBone("head");
        if (cou != null) {
            cou.setRotY(cou.getRotY() + lacet * 0.4F);
            cou.setRotX(cou.getRotX() + tangage * 0.3F);
        }
        if (tete != null) {
            tete.setRotY(tete.getRotY() + lacet * 0.6F);
            tete.setRotX(tete.getRotX() + tangage * 0.5F);
        }
    }
}
