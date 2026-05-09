# audax-italiano-stats

Estadísticas y estado actual del Audax Italiano, con datos actualizados manualmente.

## Sitio web

El sitio está publicado y disponible públicamente en GitHub Pages:
https://lmzmatias.github.io/audax-italiano-stats/

## Descripción

Proyecto personal que muestra el estado actual y las estadísticas históricas del Audax Italiano. Los resultados recientes se obtienen via SerpAPI y se publican como un archivo JSON. Las estadísticas históricas se calculan desde un CSV mantenido manualmente.

## Alcance actual (v2.1)

- Un equipo: Audax Italiano
- Una temporada: 2026
- Página web estática sin frameworks ni librerías externas
- Publicada mediante GitHub Pages
- Diseño visual responsive inspirado en los colores del club

### Bloque principal (datos recientes)
- Muestra el partido en vivo si existe, o el último partido jugado
- Incluye un mensaje contextual según el resultado
- Datos obtenidos desde `docs/data/latest.json`, actualizado con SerpAPI

### Estadísticas históricas (CSV)
- Partidos jugados, victorias, empates, derrotas
- Goles a favor y goles en contra
- Datos desde `docs/data/audax-2026.csv`, mantenido manualmente

## Qué NO incluye este proyecto

- Tabla de posiciones
- Estadísticas por jugador
- Filtros por competición o fecha
- Actualización automática en tiempo real
- Gráficos o visualizaciones

## Cómo actualizar los datos recientes

Ejecutar el script con una API key de SerpAPI:

```
python scripts/update_latest.py --api-key TU_KEY
```

O usando variable de entorno:

```
SERPAPI_KEY=TU_KEY python scripts/update_latest.py
```

Luego hacer commit y push de `docs/data/latest.json`.
