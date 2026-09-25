package fr.riviere.spinosaure.client;

import fr.riviere.spinosaure.SpinosaureMod;
import fr.riviere.spinosaure.entite.SpinosaureEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

public class SpinosaureRendu extends GeoEntityRenderer<SpinosaureEntity> {

    public SpinosaureRendu(EntityRendererProvider.Context contexte) {
        super(contexte, new SpinosaureModele());
        withScale(SpinosaureMod.ECHELLE);
        this.shadowRadius = 2.4F;
    }
}
