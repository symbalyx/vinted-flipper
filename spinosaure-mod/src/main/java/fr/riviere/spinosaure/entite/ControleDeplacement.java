package fr.riviere.spinosaure.entite;

import fr.riviere.spinosaure.cerveau.Decision.Allure;
import fr.riviere.spinosaure.cerveau.Pilote;
import fr.riviere.spinosaure.cerveau.Vec;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.control.MoveControl;

import java.util.List;

/**
 * Remplace le controle vanilla (pivot de 90 degres par tick, vitesse instantanee) par le
 * {@link Pilote} : lacet borne selon la vitesse, inertie, freinage avant les virages du
 * chemin. Au sol le corps avance dans la direction de son lacet ; dans l'eau il nage en 3D
 * vers le point vise.
 */
final class ControleDeplacement extends MoveControl {

    private final SpinosaureEntity spino;

    ControleDeplacement(SpinosaureEntity spino) {
        super(spino);
        this.spino = spino;
    }

    @Override
    public void tick() {
        Locomotion loco = spino.locomotion();
        Vec pos = Instantane.vec(spino.position());
        if (this.operation == MoveControl.Operation.MOVE_TO) {
            this.operation = MoveControl.Operation.WAIT;      // la navigation le reposera au tick suivant
            Vec vise = loco.viseeLissee(new Vec(this.wantedX, this.wantedY, this.wantedZ));
            Pilote.Commande k = loco.pilote.piloter(pos, spino.getYRot(), vise, loco.suivants(4), loco.allure);
            appliquer(k, vise);
            // marche trop haute pour le pas automatique : saut (meme regle que le vanilla)
            double dx = this.wantedX - spino.getX(), dz = this.wantedZ - spino.getZ();
            double dy = this.wantedY - spino.getY();
            if (!spino.isInWater() && dy > spino.maxUpStep() && dx * dx + dz * dz < Math.max(1.0F, spino.getBbWidth())) {
                spino.getJumpControl().jump();
                this.operation = MoveControl.Operation.JUMPING;
            }
        } else if (this.operation == MoveControl.Operation.JUMPING) {
            spino.setSpeed((float) (loco.pilote.vitesseCourante() * spino.getAttributeValue(Attributes.MOVEMENT_SPEED)));
            if (spino.onGround()) {
                this.operation = MoveControl.Operation.WAIT;
            }
        } else {
            // pas de destination : il freine progressivement au lieu de s'arreter net
            appliquer(loco.pilote.piloter(pos, spino.getYRot(), null, List.of(), Allure.ARRET), null);
        }
    }

    private void appliquer(Pilote.Commande k, Vec vise) {
        spino.setYRot(k.lacet());
        spino.yBodyRot = k.lacet();
        float v = (float) (k.vitesse() * spino.getAttributeValue(Attributes.MOVEMENT_SPEED));
        spino.setSpeed(v);                                     // avance selon son lacet
        if (spino.isInWater() && vise != null) {
            double d = Math.max(1e-3, vise.distance(Instantane.vec(spino.position())));
            double dy = (vise.y() - spino.getY()) / d;
            spino.setDeltaMovement(spino.getDeltaMovement().add(0, v * dy * 0.08, 0));   // plonge ou remonte
        }
        spino.locomotion().geste(k.geste());
    }
}
