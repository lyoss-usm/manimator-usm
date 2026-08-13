# Backend — Manimator USM

API, cola de tareas y motor de renderizado de Manim.

## Stack

- **Python 3.14** (ver `backend/.python-version`)
- **FastAPI + Uvicorn** — API HTTP.
- **Celery + Redis** — procesamiento asíncrono y estado de tareas.
- **Manim** — generación de animaciones matemáticas.
- **SymPy** — parseo de LaTeX y diferenciación simbólica.
- `antlr4-python3-runtime==4.11` — versión pinned requerida por el parser de LaTeX de SymPy.

## Estructura

```
app/
├── main.py            # Aplicación FastAPI y endpoints
├── schemas.py         # Modelos Pydantic de la API
├── tasks.py           # Tarea de Celery
└── manim_generator.py # Escenas Manim y renderizado
```

## Endpoints

| Método | Ruta                    | Descripción                                                        |
| ------ | ----------------------- | ------------------------------------------------------------------ |
| POST   | `/render`               | Encoda una tarea de renderizado y devuelve `{"task_id": "..."}`.   |
| GET    | `/status/{task_id}`     | Estado de la tarea (ver abajo).                                    |
| GET    | `/videos/{archivo}.mp4` | Sirve los videos generados (estático, `720p30`).                   |

### Cuerpo de `POST /render`

```json
{
  "f_tex": "(\\cos(t), \\sin(t))",
  "a_tex": "0",
  "b_tex": "2\\pi",
  "included_scenes": {
    "tracing": true,
    "rotation": false,
    "tangentvector": false,
    "tangentline": false,
    "normal": false,
    "arclength": false
  },
  "scene_config": { "preserve_aspect_ratio": false }
}
```

### Estados de `GET /status/{task_id}`

| Estado     | Significado                                                |
| ---------- | ---------------------------------------------------------- |
| `pending`  | En cola o en ejecución inicial.                            |
| `progress` | Video(s) parcialmente listos, devuelve `video_urls`.       |
| `done`     | Terminada, devuelve `video_urls` completos.                |
| `error`    | Falló, devuelve `error`.                                   |

## Flujo de renderizado

1. **`main.py`** recibe la petición y encola `render_manim_task` (Celery).
2. **`tasks.py`** itera sobre las escenas seleccionadas y llama a `render_scene` por cada una, actualizando el estado a `PROGRESS` con los URLs ya disponibles.
3. **`manim_generator.py`**:
   - **Parsing**: convierte `f_tex` a vectores columna LaTeX y la evalúa con `sympy.parse_latex`. Sustituye `e`, `pi` y `tau` por sus valores numéricos y lamdbdifica para evaluar numéricamente.
   - **Cálculo simbólico**: deriva la velocidad y la aceleración con `sympy.diff` y las vuelve a LaTeX para mostrarlas en pantalla.
   - **Dimensión**: evalúa `f(a)` y decide si la escena es 2D o 3D (usa `Axes` o `ThreeDAxes`).
   - **Ejes**: calcula automáticamente los rangos y pasos de los ejes a partir de los valores de la curva (con pasos "redondos" estilo ejes de graficadora), y respeta `preserve_aspect_ratio`.
   - **Escenas**: cada subclase de `BaseCurveScene(ThreeDScene)` anima un aspecto distinto usando un `ValueTracker` compartido para el parámetro `t`.

### Escenas y clases

| Clave          | Clase                | Método de animación     |
| -------------- | -------------------- | ----------------------- |
| `tracing`      | `TracingCurveScene`  | `trace_curve`           |
| `rotation`     | `RotatingCurveScene` | `rotate_curve`          |
| `tangentvector`| `TangentVectorScene` | `animate_tangent_vector`|
| `tangentline`  | `TangentLineScene`   | `animate_tangent_line`  |
| `normal`       | `NormalScene`        | `animate_normal`        |
| `arclength`    | `ArcLengthScene`     | `animate_arc_length`    |

## Cache de videos

`render_scene` construye un nombre de archivo determinista a partir de `f_tex`, `a_tex`, `b_tex`, la escena y `preserve_aspect_ratio`. Si el `.mp4` ya existe en `/manim/media/videos/720p30/`, se omite el renderizado y se devuelve el URL existente.

## Cómo agregar una nueva escena

1. Crear una subclase de `BaseCurveScene` con su método `construct`.
2. Agregar el `scene_key` al diccionario `scene_class` en `render_scene`.
3. Registrar la clave en `IncludedScenes` (schemas.py) y, si corresponde, en el frontend.

## Ejecución

- En desarrollo: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Worker: `celery -A app.tasks worker --loglevel=info`
- Ambos requieren un broker Redis en `redis://redis:6379/0` y el directorio de salida `/manim/media` (ver `docker-compose.yml` en la raíz).
