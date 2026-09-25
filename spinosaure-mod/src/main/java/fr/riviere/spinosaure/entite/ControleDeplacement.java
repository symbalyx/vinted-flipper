package fr.riviere.spinosaure.entite;

import net.minecraft.util.Mth;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.control.MoveControl;

/**
 * Deplacement amphibie, sur le modele du noye vanilla : au sol, le controle standard ;
 * dans l'eau, une nage en 3D (il plonge et remonte vers sa destination au lieu de
 * flotter en surface comme un mob terrestre).
 */
final class ControleDeplacement extends MoveControl {

    private final SpinosaureEntity spino;

    ControleDeplacement(SpinosaureEntity spino) {
        super(spino);
        this.spino = spino;
    }

    @Override
    public void tick() {
        if (!spino.isInWater()) {
            if (!spino.onGround()) {
                spino.setDeltaMovement(spino.getDeltaMovement().add(0.0D, -0.008D, 0.0D));
            }
            super.tick();
            return;
        }
        if (this.operation != MoveControl.Operation.MOVE_TO || spino.getNavigation().isDone()) {
            spino.setSpeed(0.0F);
            return;
        }
        double dx = this.wantedX - spino.getX();
        double dy = this.wantedY - spino.getY();
        double dz = this.wantedZ - spino.getZ();
        double d = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (d < 1.0E-4) {
            spino.setSpeed(0.0F);
            return;
        }
        dy /= d;
        float cap = (float) (Mth.atan2(dz, dx) * Mth.RAD_TO_DEG) - 90.0F;
        spino.setYRot(this.rotlerp(spino.getYRot(), cap, 20.0F));   // gros animal : virage lent
        spino.yBodyRot = spino.getYRot();
        float cible = (float) (this.speedModifier * spino.getAttributeValue(Attributes.MOVEMENT_SPEED));
        float v = Mth.lerp(0.125F, spino.getSpeed(), cible);
        spino.setSpeed(v);
        spino.setDeltaMovement(spino.getDeltaMovement().add(v * dx * 0.005D, v * dy * 0.1D, v * dz * 0.005D));
    }
}
