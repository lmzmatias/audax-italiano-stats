# audax-italiano-stats

Estado actual del Audax Italiano, con tono editorial propio.

## Sitio web

Publicado en GitHub Pages:
https://lmzmatias.github.io/audax-italiano-stats/

## Descripción

Proyecto personal que muestra el estado actual del Audax Italiano con un lenguaje directo e irónico. La home se enfoca en actualidad: partido en vivo, último resultado, o un mensaje de espera cuando no hay actividad reciente. Los datos se obtienen via SerpAPI y se publican como un archivo JSON actualizado manualmente.

## Alcance actual (v2.4)

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

### En vivo (v2.3)
- Muestra goles ⚽, tarjetas amarillas 🟨 y rojas 🟥 con minuto y jugador
- Eventos de Audax en verde, del rival en rojo oscuro
- Asistencias incluidas cuando están disponibles
- Datos desde `live.events` en `latest.json`

## Qué NO incluye este proyecto

- Tabla de posiciones
- Subpáginas
- Estadísticas históricas en la vista principal
- Estadísticas por jugador
- Filtros por competición o fecha
- Gráficos o visualizaciones

## Actualización automática (GitHub Actions) — recomendado

El workflow `.github/workflows/update-live.yml` corre automáticamente cada 5 minutos
en los servidores de GitHub. No requiere tener nada corriendo en tu computador.

### Lógica de actualización
| Situación | Frecuencia de check a API-Football |
|---|---|
| Partido en vivo | Cada 5 min (cada ejecución del workflow) |
| Sin partido, dentro de 12:00-22:00 | Cada 15 min |
| Fuera de 12:00-22:00 hora Chile | Sin requests |
| Historial (SerpAPI) | Cada 60 min dentro del horario |

Consumo estimado: ~58 req/día con 1 partido → dentro del límite Free (100/día).

### Configurar los secrets en GitHub

1. Ir a **Settings → Secrets and variables → Actions** en el repositorio
2. Agregar los siguientes secrets:

| Secret | Valor |
|---|---|
| `APIFOOTBALL_KEY` | Tu API key de api-sports.io |
| `SERPAPI_KEY` | Tu API key de SerpAPI |

3. Hacer push del workflow (`.github/workflows/update-live.yml`) al repositorio
4. El workflow se activa automáticamente. También se puede correr manualmente desde
   **Actions → Update live data → Run workflow**

### Actualización manual (desde tu computador)

#### Una vez
```
python scripts/update_latest.py --serpapi-key TU_SERPAPI_KEY --apifootball-key TU_APIFOOTBALL_KEY
```

#### Loop de en vivo (mientras tenés el computador abierto)
```
python scripts/update_live.py --apifootball-key TU_APIFOOTBALL_KEY
```
- Con partido en vivo: refresca cada 2 minutos
- Sin partido: chequea cada 5 minutos
- Detener: Ctrl+C

### APIs utilizadas
- **SerpAPI**: historial de partidos recientes
- **API-Football (api-sports.io)**: partido en vivo en tiempo real
  - Audax Italiano ID: `2329` | Plan Free: 100 requests/día
