# audax-italiano-stats

Estado actual del Audax Italiano, con tono editorial propio.

## Sitio web

Publicado en GitHub Pages:
https://lmzmatias.github.io/audax-italiano-stats/

## Descripción

Proyecto personal que muestra el estado actual del Audax Italiano con un lenguaje directo e irónico. La home se enfoca en actualidad: partido en vivo, último resultado, o un mensaje de espera cuando no hay actividad reciente. Los datos se obtienen via SerpAPI y se publican como un archivo JSON actualizado manualmente.

## Alcance actual (v2.2)

- Un equipo: Audax Italiano
- Página web estática sin frameworks ni librerías externas
- Publicada mediante GitHub Pages
- Fuente tipográfica: Inter
- Diseño responsive inspirado en los colores del club

### Home (actualidad)
- Muestra el partido en vivo si existe
- Si no hay partido en vivo y han pasado ≤12h desde el último: muestra el resultado con su mensaje irónico
- Si han pasado >12h: muestra un mensaje de espera rotativo
- Debajo del bloque principal: hasta 10 partidos recientes (5 visibles, expandibles)
- El color del mensaje indica el estado: verde (ganando), ámbar (empatando), rojo oscuro (perdiendo), gris (espera/FT)
- Datos desde `docs/data/latest.json`, actualizado con SerpAPI
- Partidos futuros filtrados automáticamente (no se muestran)
- Hasta 6 partidos recientes reales (5 visibles + "ver más desgracias")

## Qué NO incluye este proyecto

- Tabla de posiciones
- Subpáginas
- Estadísticas históricas en la vista principal
- Estadísticas por jugador
- Filtros por competición o fecha
- Actualización automática en tiempo real
- Gráficos o visualizaciones

## Cómo actualizar los datos recientes

```
python scripts/update_latest.py --api-key TU_KEY
```

Luego hacer commit y push de `docs/data/latest.json`.
