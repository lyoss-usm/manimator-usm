# Frontend — Manimator USM

Interfaz de usuario para el renderizador de curvas paramétricas.

## Stack

- **React 19** + **TypeScript**
- **Vite 8** con plugin de React y **React Compiler** habilitado.
- **Tailwind CSS 4** (plugin de Vite).
- **shadcn/ui** sobre **Radix UI** (botones, cards, checkboxes, inputs, etc.).
- **lucide-react** y **react-icons** para iconografía; `react-flag-icons` para el selector de idioma.
- Fuente **Geist** (`@fontsource-variable/geist`).

## Scripts

| Comando          | Descripción                          |
| ---------------- | ------------------------------------ |
| `npm run dev`    | Servidor de desarrollo con HMR.      |
| `npm run build`  | Typecheck (`tsc -b`) + build de Vite.|
| `npm run lint`   | ESLint.                              |
| `npm run preview`| Previsualiza el build de producción. |

## Estructura

```
src/
├── App.tsx            # SPA completa: formulario, escenas, reproductor y footer
├── main.tsx           # Punto de entrada
├── index.css          # Estilos globales y tema Tailwind
├── lib/utils.ts       # Utilidades (cn)
├── components/ui/     # Componentes shadcn/ui (button, card, checkbox, field, input, label, separator)
└── assets/            # Recursos estáticos
```

## Cómo funciona

- **Formulario**: ingresa `f(t)` en LaTeX, límites `a` y `b`, opción de preservar relación de aspecto y las escenas a generar. Los valores por defecto son `(\cos(t), \sin(t))` en `[0, 2\pi]`.
- **Envío**: `POST /api/render` con `f_tex`, `a_tex`, `b_tex`, `included_scenes` y `scene_config`. El backend responde con un `task_id`.
- **Polling**: se consulta `GET /api/status/{task_id}` cada 2 segundos. Los videos aparecen progresivamente en las pestañas conforme el worker los termina (`status = progress` → `done`).
- **Reproductor**: pestañas por escena con indicador de carga (spinner) y check verde cuando el video está listo.
- **i18n**: diccionarios `translations` con los idiomas `es` y `en`; el botón con la bandera alterna entre ambos.
- Al terminar el renderizado se muestra un enlace a una encuesta de retroalimentación (Google Forms).

## Comunicación con el backend

En desarrollo, Vite redirige las peticiones bajo `/api` y `/videos` mediante el proxy de Nginx en producción (ver `nginx.conf`):

- `location /api/` → `backend:8000/`
- `location /videos/` → `backend:8000/videos/`

El frontend construye los URLs de video como `` `${API_URL}${videoUrl}` `` usando la constante `API_URL = "/api"`.
