"""Journaux ecrits trouves dans les coffres : l'histoire de Site B, en morceaux.

Ils donnent aussi aux joueurs des objectifs possibles pour un evenement : relancer le groupe
de secours (sous-sol des labos), rejoindre le relais radio, trouver l'antre (grotte de la
cascade), survivre jusqu'au ponton."""

JOURNAUX = {
    'directeur': ('Rapport S-01', 'Dr H. Varenne', [
        "Sujet S-01, Spinosaurus. ADN comble avec du genome d'amphibien (lot 44). Resultat : "
        "il respire plus longtemps sous l'eau que prevu. Beaucoup plus.",
        "Semaine 9. Il ne mange pas quand on le regarde. Il attend que l'equipe se retourne. "
        "Les soigneurs appellent ca de la timidite. Moi pas.",
        "Semaine 14. Il a appris le rythme des rondes. Il suit les equipes depuis la riviere, "
        "a la meme vitesse qu'elles. Sans bruit.",
        "La tempete a coupe le courant. Clotures a zero. Le bassin communique avec la riviere "
        "par la breche nord. Il est dehors depuis 3 jours et personne ne l'a vu.",
        "Si vous lisez ceci : le groupe de secours est au sous-sol des labos. Cinq leviers. "
        "Le sous-sol est noye. Le tunnel de drainage donne sur son bassin.",
    ]),
    'bungalow': ('Carnet de peche', 'L. Moreau', [
        "Jour 2. Plus un poisson dans le lagon. Les filets sont revenus dechires, "
        "net, comme au couteau.",
        "Jour 4. La nuit, une voile passe devant le ponton. Elle depasse de l'eau de deux "
        "metres. Elle ne fait aucune vague.",
        "Jour 5. Les autres partent vers le campus par la piste de la tour. Moi je reste "
        "en hauteur. Il ne monte pas aux pilotis. Pas encore.",
    ]),
    'grotte': ('Derniere page', 'inconnu', [
        "C'est ici qu'il revient. Les os sont ranges. Pas jetes : ranges.",
        "Il m'a vu entrer. Il n'est pas entre. Il attend au bord de l'eau, sous la chute. "
        "Il sait que je dois ressortir.",
        "A qui trouvera ceci : ne courez pas pres de l'eau. Il entend les pas. Et ne "
        "regardez pas trop longtemps la riviere : c'est la qu'il vous regarde.",
    ]),
    'delta': ('Station Delta - releves', 'Dr A. Sy', [
        "Empreintes dans la vase : 1,10 m. Pas de trace de queue. Il nage plus qu'il ne marche.",
        "Il remonte le bras principal jusqu'au lac central. Ilot au milieu du lac : "
        "restes de carcasses. Nous l'appelons le Repaire.",
        "La mangrove n'est pas sure. L'eau y fait moins d'un metre, mais il s'y couche a plat. "
        "On ne voit que les yeux.",
    ]),
    'phare': ('Journal du gardien', 'P. Lenoir', [
        "Le feu s'est eteint le 14. Le generateur du phare est sec. Le relais radio a l'est "
        "fonctionne encore sur batterie, d'apres le campus.",
        "Depuis la galerie on voit toute l'ile. On voit aussi les sillons dans la riviere. "
        "Ils vont toujours vers le campus.",
        "Personne n'est venu relever le phare. Je descends vers le campement. Si je ne "
        "reviens pas, gardez la lumiere de ce coffre.",
    ]),
    'mine': ('Galerie 3', 'contremaitre R. Diaz', [
        "Il ne rentre pas dans les galeries. Trop etroit pour lui. Il le sait.",
        "Alors il attend dehors. Deux jours. Il s'eloigne quand on appelle, il revient "
        "quand on se tait.",
        "Il reste des vivres pour une semaine et de la TNT. On fera sauter l'entree "
        "s'il le faut. Ou on tentera la piste de la tour, de jour.",
    ]),
    'temple': ('Notes de fouille', 'Pr. E. Ruiz', [
        "La fresque au sommet montre une silhouette a voile, au-dessus d'une riviere. "
        "Bien plus ancienne que le parc.",
        "Les habitants lui laissaient des offrandes au bord de l'eau, et ne se retournaient "
        "jamais en partant. Je comprends pourquoi maintenant.",
    ]),
    'bunker': ('Ordres de l\'abri 4', 'Cdt. Marchal', [
        "Tenir l'abri jusqu'a l'evacuation. Signal : fusee depuis le ponton sud.",
        "Regle 1 : jamais seul. Il choisit toujours celui qui s'ecarte du groupe.",
        "Regle 2 : a court de munitions, on se tait et on recharge a couvert. Il attend "
        "ce moment-la. Il l'attend a chaque fois.",
        "L'evacuation n'est pas venue. Le ponton sud est la seule sortie.",
    ]),
}


def livre(cle):
    """Etiquette NBT (1.20.1) d'un livre ecrit : titre, auteur, pages en texte JSON."""
    import json
    import nbt
    titre, auteur, pages = JOURNAUX[cle]
    return nbt.Compound({
        'title': nbt.String(titre), 'author': nbt.String(auteur), 'resolved': nbt.Byte(1),
        'pages': nbt.List('string', [nbt.String(json.dumps({'text': p}, ensure_ascii=False)) for p in pages]),
    })
