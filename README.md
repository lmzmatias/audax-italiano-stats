# audax-italiano-stats

Estado actual del Audax Italiano, con tono editorial propio.

## Sitio web

Publicado en GitHub Pages:
https://lmzmatias.github.io/audax-italiano-stats/

## Descripción

Proyecto personal que muestra el estado actual del Audax Italiano con un lenguaje directo e irónico. La home se enfoca en actualidad: partido en vivo, último resultado, o un mensaje de espera cuando no hay actividad reciente. Los datos se obtienen via API-Football y SerpAPI, y se publican como un archivo JSON actualizado automáticamente.

## Alcance actual (v3.0)

- Un equipo: Audax Italiano
- Página web estática sin frameworks ni librerías externas
- Publicada mediante GitHub Pages
- Fuente tipográfica: Inter
- Diseño responsive inspirado en los colores del club

### Home (actualidad)
- Muestra el partido en vivo si existe
- Si no hay partido en vivo y han pasado ≤12h desde el último: muestra el resultado con su mensaje irónico
- Si han pasado >12h: muestra un mensaje de espera rotativo
- El color del mensaje indica el estado: verde (ganando), ámbar (empatando), rojo oscuro (perdiendo), gris (espera/FT)
- Datos desde `docs/data/latest.json`, actualizado automáticamente con GitHub Actions

### Partidos recientes
- Con partido en vivo activo: se muestra 1 partido FT debajo del bloque principal
- Sin partido en vivo: se muestran 2 partidos FT debajo del bloque principal
- Cada partido mantiene su mensaje irónico correspondiente
- Botón "Ver más desgracias": toggle que expande hasta 10 partidos y permite volver a la vista por defecto
- Partidos futuros filtrados automáticamente

### En vivo
- Muestra goles ⚽, tarjetas amarillas 🟨 y rojas 🟥 con minuto y jugador
- Eventos de Audax en verde, del rival en rojo oscuro
- Asistencias incluidas cuando están disponibles
- Datos desde `live.events` en `latest.json`

### Tablas de competiciones (nuevo en v3.0)
- Contexto competitivo secundario: aparece debajo de los partidos, sin competir con el bloque principal
- Se muestran solo las competiciones donde Audax participa actualmente (LDP, CDL, SUD)
- Si no hay datos cargados, el bloque no aparece
- Si hay más de una tabla, se ordenan según la competición con partidos más recientes
- Columnas: Pos, Equipo, PTS, DG
- Vista por defecto: 3 equipos arriba de Audax + Audax + 3 equipos abajo (7 filas)
- Botón neutro "Ver tabla completa" para expandir; se puede volver a la vista reducida
- Audax resaltado muy levemente (fondo casi neutro + negrita leve)
- En mobile las tablas arrancan colapsadas (accordion)
- No hay colores fuertes ni verde Audax en las tablas

**Actualización de standings:** se edita manualmente el campo `standings` en `docs/data/latest.json`
después de cada jornada. Los scripts automáticos nunca sobreescriben ese campo.

## Qué NO incluye este proyecto

- Feed de X/Twitter (previsto para una versión futura)
- Tabla de posiciones como pantalla principal
- Subpáginas
- Estadísticas históricas en la vista principal
- Estadísticas por jugador
- Filtros por competición o fecha
- Gráficos o visualizaciones
- Frameworks o librerías externas

## Actualización automática (GitHub Actions)

El workflow `.github/workflows/update-live.yml` corre automáticamente cada 5 minutos
en los servidores de GitHub. No requiere tener nada corriendo en tu computador.

### Lógica de actualización
| Situación | Frecuencia de check a API-Football |
|---|---|
| Partido en vivo | Cada 5 min (cada ejecución del workflow) |
| Sin partido, dentro de 12:00-22:00 | Cada 15 min |
| Fuera de 12:00-22:00 hora Chile | Sin requests |
| Historial (SerpAPI) + Standings | Cada 60 min dentro del horario |

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
- **API-Football (api-sports.io)**: partido en vivo en tiempo real + tablas de posiciones
  - Audax Italiano ID: `2329` | Plan Free: 100 requests/día
