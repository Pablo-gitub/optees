# Esempio Dijkstra: Percorso di consegna

Supponi che una consegna parta dal deposito `A` e debba raggiungere il cliente
`D`. Ogni arco diretto ha un costo di percorrenza:

| Arco | Peso |
| --- | ---: |
| A -> B | 4 |
| A -> C | 1 |
| C -> B | 2 |
| B -> D | 1 |
| C -> D | 8 |

Il percorso che sembra diretto `A -> B -> D` costa `5`. Dijkstra trova invece:

```text
A -> C -> B -> D
1 + 2 + 1 = 4
```

Rende definitivo `C` con distanza provvisoria `1`, migliora la distanza nota di
`B` da `4` a `3`, poi rende definitivo `D` con distanza finale `4`.

Carica `examples/shortest_path_delivery.json` per riprodurre il grafo. Prova a
modificare il peso `C -> D`: il percorso cambia solo quando il suo costo totale
diventa minore di `4`.

Per una strada non diretta, disattiva **Archi diretti**. Un arco inserito potra'
allora essere percorso in entrambi i versi.
