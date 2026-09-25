package fr.riviere.spinosaure.client;

import fr.riviere.spinosaure.SpinosaureMod;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = SpinosaureMod.MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class ClientSetup {

    private ClientSetup() {
    }

    @SubscribeEvent
    public static void rendus(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer(SpinosaureMod.SPINOSAURE.get(), SpinosaureRendu::new);
    }
}
