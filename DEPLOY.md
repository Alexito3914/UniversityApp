# Despliegue en producción — UCJC Horarios

Guía para el equipo de IT de la universidad.

## Requisitos del servidor

- Python 3.11+
- PostgreSQL 14+ (recomendado)
- Nginx o Apache como proxy inverso
- Certificado TLS (HTTPS)

## 1. Preparar entorno

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # editar con valores reales
```

Variables críticas en `.env`:

| Variable | Descripción |
|----------|-------------|
| `DJANGO_DEBUG` | `False` en producción |
| `DJANGO_SECRET_KEY` | Clave aleatoria larga (obligatoria si DEBUG=False) |
| `DJANGO_ALLOWED_HOSTS` | Dominio(s) del servicio |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://horarios.ucjc.es` |
| `DB_ENGINE` | `postgresql` |
| `DB_*` | Credenciales PostgreSQL |

## 2. Base de datos y datos iniciales

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py import_horarios_excel --file ruta/HORARIOS.xlsx --year 2026-2027 --clear-eps
```

Marca el año académico actual en Admin → Años académicos (`is_current`).

## 3. Usuarios y roles

Cada usuario necesita:

1. Cuenta Django (`User`)
2. Perfil `UserProfile` con rol: `DEAN`, `IT`, `PROF`, `STUD`
3. **Profesores**: el email del `User` debe coincidir con `Professor.email`
4. **Estudiantes**: acceden con rol `STUD` y eligen titulación/curso al entrar

Para demo local: `python manage.py seed_demo`

## 4. Arrancar con Gunicorn

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 120
```

## 5. Nginx (ejemplo)

```nginx
server {
    listen 443 ssl;
    server_name horarios.ucjc.es;

    location /static/ {
        alias /ruta/al/proyecto/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

## 6. Flujo operativo anual

1. **IT/Decanato**: importar Excel de ofertas docentes
2. **IT**: generar horarios (borrador) y revisar conflictos
3. **Decanato**: enviar a revisión → aprobar
4. **Profesores y alumnos**: consultan horario **publicado** (solo `APPROVED`)
5. **Profesores**: registran disponibilidad en `/disponibilidad/`

## 7. Copias de seguridad

- Base PostgreSQL: backup diario automatizado
- Fichero `logs/audit.log`: trazabilidad de cambios

## 8. Pendiente para integración institucional (fase 2)

Estos puntos requieren coordinación con la universidad:

- **SSO / LDAP** (login con cuenta corporativa `@ucjc.es`)
- **Sincronización de alumnos** desde matrícula (en lugar de selección manual)
- **Correo electrónico** además de notificaciones in-app
- **Entorno de preproducción** para pruebas antes del curso

## Comprobar salud

```bash
python manage.py test horarios
python manage.py check --deploy
```
