package fr.riviere.spinosaure;

import fr.riviere.spinosaure.entite.SpinosaureEntity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.SpawnPlacements;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraftforge.common.ForgeSpawnEggItem;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.event.entity.SpawnPlacementRegisterEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

@Mod(SpinosaureMod.MODID)
public class SpinosaureMod {

    public static final String MODID = "spinosaure";

    /** Echelle de rendu du modele Blockbench (9.6 blocs de haut a l'echelle 1). */
    public static final float ECHELLE = 0.7F;

    public static final DeferredRegister<EntityType<?>> ENTITES =
            DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, MODID);
    public static final DeferredRegister<Item> OBJETS =
            DeferredRegister.create(ForgeRegistries.ITEMS, MODID);

    // Boite de collision plus etroite que le modele : le pathfinding vanilla gere mal
    // les mobs de plus de 3.5 blocs de large (forets, berges).
    public static final RegistryObject<EntityType<SpinosaureEntity>> SPINOSAURE = ENTITES.register("spinosaure",
            () -> EntityType.Builder.of(SpinosaureEntity::new, MobCategory.MONSTER)
                    .sized(3.4F, 5.0F)
                    .clientTrackingRange(12)
                    .build(MODID + ":spinosaure"));

    public static final RegistryObject<Item> OEUF = OBJETS.register("spinosaure_spawn_egg",
            () -> new ForgeSpawnEggItem(SPINOSAURE, 0x5A4632, 0xC9A227, new Item.Properties()));

    public SpinosaureMod() {
        IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
        ENTITES.register(bus);
        OBJETS.register(bus);
        bus.addListener(this::attributs);
        bus.addListener(this::apparition);
        bus.addListener(this::onglets);
        MinecraftForge.EVENT_BUS.register(EvenementsJeu.class);
    }

    private void attributs(EntityAttributeCreationEvent e) {
        e.put(SPINOSAURE.get(), SpinosaureEntity.attributs().build());
    }

    private void apparition(SpawnPlacementRegisterEvent e) {
        e.register(SPINOSAURE.get(), SpawnPlacements.Type.ON_GROUND, Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                SpinosaureEntity::peutApparaitre, SpawnPlacementRegisterEvent.Operation.REPLACE);
    }

    private void onglets(BuildCreativeModeTabContentsEvent e) {
        if (e.getTabKey() == CreativeModeTabs.SPAWN_EGGS) {
            e.accept(OEUF);
        }
    }
}
