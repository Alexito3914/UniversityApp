# UCJC Horarios — V3 (UI integrada)

Sistema Django de gestión de horarios académicos para la Universidad Camilo José Cela, ahora con la **interfaz visual integrada** (rojo y blanco institucional, sidebar fijo, navbar con notificaciones, tabla visual con colores por titulación, etc).

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo               # carga datos de prueba
python manage.py createsuperuser         # opcional, para acceder al admin
python manage.py runserver
```

Abre http://127.0.0.1:8000/ en el navegador.

## Usuarios de demo (creados por `seed_demo`)

| Usuario      | Contraseña | Rol            |
|--------------|------------|----------------|
| `decano`     | `ucjc1234` | Decanato       |
| `profesor`   | `ucjc1234` | Profesor       |
| `estudiante` | `ucjc1234` | Estudiante     |
| `it`         | `ucjc1234` | IT             |

## Novedades de la V3

- **Interfaz nueva** basada en el diseño aprobado: navbar rojo UCJC con campana de notificaciones, sidebar lateral fijo, navegación tipo SPA visual.
- **Colores por titulación** en la tabla del horario: azul (Informática), verde (Robótica), ámbar (Telemática), violeta (Doble Grado).
- **Notificaciones in-app** con modelo persistente, dropdown en navbar y página dedicada.
- **Configuración de franjas horarias** desde la web (sin tocar el admin).
- **Animación de contadores** en las métricas del dashboard al cargar.
- **Badge "Transversal"** en cada tarjeta de asignatura compartida.
- **Botones de acción contextuales** según rol y estado del horario (workflow DRAFT → REVIEW → APPROVED).
- **Logout por POST** (estándar de seguridad de Django 5).

## Estructura del proyecto

```
config/                    Configuración Django
horarios/
  models.py                14 entidades + Notification
  views.py                 Vistas con RBAC, workflow, exportación CSV, JSON API
  forms.py                 Formularios con validación de conflictos
  urls.py                  Rutas
  services.py              Motor de generación + validación de restricciones
  context_processors.py    Inyecta datos navbar/sidebar
  templates/horarios/      10 templates con el nuevo diseño
  templatetags/            Filtro get_item para tablas
  management/commands/     seed_demo
static/
  css/site.css             ~830 líneas con todo el diseño
  js/site.js               Bell dropdown + animación de contadores
  img/logo-uni.png         Logo UCJC
  img/ucjc_logo.svg        Logo SVG (legacy)
```

## URLs principales

| Ruta                                | Vista              | Acceso              |
|-------------------------------------|--------------------|---------------------|
| `/`                                 | Dashboard          | Todos               |
| `/horarios/`                        | Lista de horarios  | Todos               |
| `/horarios/<pk>/`                   | Tabla visual       | Todos               |
| `/horarios/<pk>/sesiones/nueva/`    | Añadir sesión      | DEAN, IT (DRAFT)    |
| `/horarios/<pk>/exportar/csv/`      | Exportar CSV       | Todos               |
| `/disponibilidad/`                  | Disponibilidad     | PROF (propia), DEAN, IT |
| `/titulaciones/`                    | Catálogo           | Todos               |
| `/informes/`                        | Informe cobertura  | Todos               |
| `/notificaciones/`                  | Notificaciones     | Todos               |
| `/configuracion/`                   | Franjas horarias   | DEAN, IT            |
| `/admin/`                           | Admin Django       | Superuser           |
