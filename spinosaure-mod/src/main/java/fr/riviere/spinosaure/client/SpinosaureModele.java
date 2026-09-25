package fr.riviere.spinosaure.client;

import fr.riviere.spinosaure.SpinosaureMod;
import fr.riviere.spinosaure.entite.SpinosaureEntity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

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
}
