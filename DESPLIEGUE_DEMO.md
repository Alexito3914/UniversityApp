# Despliegue demo para el decano (enlace público)

Hay **dos opciones**. La recomendada para mandar un enlace estable es **Render** (gratis).

---

## Opción A — Render (recomendada, enlace fijo)

URL tipo: `https://ucjc-horarios.onrender.com`

### 1. Subir el código a GitHub

En PowerShell, desde la carpeta `ucjc_horarios_v3`:

```powershell
git init
git add .
git commit -m "Despliegue demo UCJC Horarios"
```

Crea un repositorio vacío en GitHub (por ejemplo `ucjc-horarios`) y:

```powershell
git remote add origin https://github.com/TU_USUARIO/ucjc-horarios.git
git branch -M main
git push -u origin main
```

### 2. Crear servicio en Render

1. Entra en [https://render.com](https://render.com) (cuenta gratis; puedes usar “Sign in with GitHub”).
2. **New → Blueprint**.
3. Conecta tu cuenta de GitHub si aún no lo has hecho.
4. Selecciona el repositorio `ucjc-horarios` — Render detectará `render.yaml` (web + PostgreSQL gratis).
5. Pulsa **Apply** y confirma la creación de los recursos.
6. Espera 5–10 minutos al primer despliegue (build: migrate + datos demo).

Si el build falla, abre **Logs** en el servicio web y revisa el mensaje de error.

### 3. Enlace para el decano

Cuando termine, Render muestra la URL pública. Envía:

**`https://ucjc-horarios.onrender.com`** (o la que asigne Render)

**Login decano:** `decano` / `ucjc1234`

Otros usuarios demo: `profesor`, `estudiante`, `it` — contraseña `ucjc1234`

> Nota: en plan gratis la app “duerme” tras inactividad; la primera carga puede tardar ~30 s.

---

## Opción B — Túnel rápido (hoy mismo, tu PC encendida)

Si necesitas un enlace **ya** sin GitHub:

```powershell
cd "c:\Users\aniet\Downloads\ucjc_horarios_v3 (1)\ucjc_horarios_v3"
.\scripts\demo_tunnel.ps1
```

El script arranca la app y muestra una URL `https://....loca.lt`. **Tu ordenador debe seguir encendida** mientras el decano la use.

Copia la URL que salga y envíasela al decano con las mismas credenciales.

---

## Después del despliegue

1. Entra como `decano` y revisa el dashboard.
2. Importa el Excel real si hace falta (desde IT, vía consola Render o local):
   ```bash
   python manage.py import_horarios_excel --file HORARIOS.xlsx --year 2026-2027 --clear-eps
   ```
3. Genera y **aprueba** un horario para que alumnos/profesores vean datos publicados.

---

## Credenciales demo

| Usuario      | Contraseña | Rol        |
|-------------|------------|------------|
| `decano`    | `ucjc1234` | Decanato   |
| `profesor`  | `ucjc1234` | Profesor   |
| `estudiante`| `ucjc1234` | Alumno     |
| `it`        | `ucjc1234` | IT         |
