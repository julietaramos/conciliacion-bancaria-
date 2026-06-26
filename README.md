# Conciliación Bancaria

Aplicación web para conciliar el **Mayor Contable** contra el **Extracto Bancario**. Sube los dos archivos, la app los cruza automáticamente y descargás un Excel con el resultado listo para usar.

---

## ¿Qué hace exactamente?

1. **Cargás dos archivos** por banco: el Mayor Contable (`.xlsx`, `.xls` o `.csv`) y el Extracto Bancario (`.csv` o `.txt`).
2. **La app los cruza** buscando movimientos que coincidan por monto y fecha (ventana de ±5 días).
3. **Genera un Excel de salida** con los movimientos conciliados y los pendientes, en el formato estándar MODELO CLAUDIO.
4. **Carry-over automático**: las partidas que quedaron pendientes el mes anterior se cargan solas en la próxima conciliación — no tenés que hacer nada.
5. Podés manejar **múltiples bancos** desde el mismo sistema.

### Formatos de archivo soportados

| Archivo | Formatos | Columnas requeridas |
|---|---|---|
| Mayor Contable | `.xlsx`, `.xls`, `.csv` | Fecha, Detalle/Concepto, Debe/Haber o Importe |
| Extracto Bancario | `.csv`, `.txt` | Fecha, Descripción, Débito/Crédito o Importe |

Bancos soportados: Galicia, Nación, Santander, BBVA, y cualquier banco con columnas estándar. El delimitador (`,` `;` tabulación) se detecta automáticamente.

> **Nota sobre Banco Provincia**: el PDF del extracto tiene texto como gráfico y no se puede leer. Exportá el extracto como Excel desde el home banking antes de subirlo.

---

## ¿Cómo se usa la aplicación?

### 1. Agregar un banco
En el menú lateral, entrá a **Bancos** → hacé clic en **Agregar banco** → escribí el nombre (ej: "Galicia Cuenta Corriente") → Guardar.

### 2. Conciliar
Desde la lista de bancos hacé clic en **Conciliar**. Se abre un formulario donde subís:
- **Mayor Contable**: el libro de tu sistema contable para ese período.
- **Extracto Bancario**: el extracto del banco para el mismo período.

Hacé clic en **Conciliar** y esperás unos segundos.

### 3. Revisar y descargar
La app muestra un resumen con la cantidad de movimientos conciliados y las partidas que quedaron pendientes. Desde ahí podés **descargar el Excel** con el resultado completo.

> Solo existe una conciliación guardada por banco. Cada vez que conciliás, reemplaza la anterior. Las partidas pendientes de la conciliación anterior se cargan automáticamente como carry-over.

---

## Cómo instalar y correr el proyecto

Este es un proyecto con dos partes: un **backend** (Python) y un **frontend** (JavaScript/React). Necesitás correr las dos al mismo tiempo para que funcione.

### Paso 1 — Crear una cuenta en GitHub (si no tenés)

1. Entrá a [github.com](https://github.com).
2. Hacé clic en **Sign up** (arriba a la derecha).
3. Seguí los pasos: ingresá un email, una contraseña y un nombre de usuario.
4. Verificá tu email cuando te llegue el correo de confirmación.

Ya con cuenta creada, podés clonar este repositorio.

---

### Paso 2 — Instalar Git

Git es la herramienta para descargar el código desde GitHub.

**En Windows:**
1. Entrá a [git-scm.com/download/win](https://git-scm.com/download/win).
2. Descargá el instalador y ejecutalo.
3. En todas las pantallas del instalador dejá las opciones por defecto y hacé clic en **Next** hasta que diga **Install**. Luego **Finish**.
4. Para verificar que quedó instalado, abrí una terminal (buscá "PowerShell" o "cmd" en el menú inicio) y escribí:
   ```
   git --version
   ```
   Tiene que aparecer algo como `git version 2.x.x`.

---

### Paso 3 — Instalar Python

1. Entrá a [python.org/downloads](https://www.python.org/downloads/).
2. Hacé clic en el botón amarillo grande **Download Python 3.x.x** (cualquier versión 3.11 o superior).
3. Ejecutá el instalador. **MUY IMPORTANTE**: en la primera pantalla del instalador, tildá la opción **"Add Python to PATH"** antes de hacer clic en Install.
4. Hacé clic en **Install Now**.
5. Para verificar, abrí una terminal nueva y escribí:
   ```
   python --version
   ```
   Tiene que aparecer `Python 3.11.x` o superior.

---

### Paso 4 — Instalar Node.js

Node.js es el entorno que necesita el frontend.

1. Entrá a [nodejs.org](https://nodejs.org).
2. Descargá la versión **LTS** (la de la izquierda, que dice "Recommended For Most Users").
3. Ejecutá el instalador y dejá todas las opciones por defecto.
4. Para verificar, abrí una terminal nueva y escribí:
   ```
   node --version
   ```
   Tiene que aparecer `v18.x.x` o superior.

---

### Paso 5 — Descargar el proyecto

Abrí una terminal (PowerShell o cmd) y ejecutá estos comandos uno por uno:

```bash
git clone https://github.com/julietaramos/conciliacion-bancaria-.git
cd conciliacion-bancaria-
```

Esto descarga el código en una carpeta llamada `conciliacion-bancaria-` y te posiciona dentro de ella.

---

### Paso 6 — Configurar el Backend (Python)

En la misma terminal, ejecutá:

```bash
cd backend
pip install -r requirements.txt
```

Esto instala todas las librerías que necesita el backend. Puede tardar un par de minutos la primera vez.

Luego creá el archivo de configuración. En Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

O si no existe `.env.example`, creá un archivo `.env` dentro de la carpeta `backend` con este contenido:

```
PORT=5000
ALLOWED_ORIGINS=http://localhost:5173
```

Ahora iniciá el servidor:

```bash
cd src
python -m uvicorn main:app --port 5000 --reload
```

Si todo salió bien, vas a ver algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:5000 (Press CTRL+C to quit)
```

**Dejá esta terminal abierta.** El backend tiene que seguir corriendo.

---

### Paso 7 — Configurar el Frontend (React)

Abrí **una segunda terminal** (sin cerrar la del backend) y navegá a la carpeta del proyecto:

```bash
cd conciliacion-bancaria-/frontend
npm install
```

Esto instala las dependencias del frontend. La primera vez puede tardar un minuto.

Luego iniciá el servidor de desarrollo:

```bash
npm run dev
```

Vas a ver algo como:
```
  VITE v5.x.x  ready in 300 ms

  ➜  Local:   http://localhost:5173/
```

**Dejá esta terminal abierta también.**

---

### Paso 8 — Usar la aplicación

Con las dos terminales corriendo, abrí tu navegador y entrá a:

```
http://localhost:5173
```

Deberías ver la aplicación lista para usar.

---

## Estructura del proyecto

```
conciliacion-bancaria-/
├── backend/
│   ├── requirements.txt        ← dependencias Python
│   └── src/
│       ├── main.py             ← servidor FastAPI (puerto 5000)
│       ├── controllers/
│       │   └── reconciliation_controller.py
│       ├── db/
│       │   ├── models.py       ← tablas: Banco, Conciliacion
│       │   ├── crud.py         ← operaciones de base de datos
│       │   └── database.py     ← conexión SQLite/PostgreSQL
│       └── utils/
│           ├── excel_parser.py     ← lee el Mayor Contable
│           ├── bank_parsers.py     ← lee el Extracto Bancario
│           ├── reconciliation.py   ← lógica de matching
│           └── excel_report.py     ← genera el Excel de salida
└── frontend/
    ├── package.json
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── HomePage.jsx
        │   ├── BancosPage.jsx
        │   ├── FileUploader.jsx
        │   └── ...
        └── index.css
```

---

## Stack tecnológico

- **Backend**: Python + FastAPI + SQLAlchemy
- **Base de datos**: SQLite (local automático) / PostgreSQL (producción vía `DATABASE_URL`)
- **Frontend**: React 18 + Vite
- **Reportes**: openpyxl (Excel de salida)

---

## Problemas frecuentes

**`python` no se reconoce como comando**
→ Reinstalá Python y asegurate de tildar "Add Python to PATH" durante la instalación. Reiniciá la terminal después.

**`npm` no se reconoce como comando**
→ Reiniciá la terminal después de instalar Node.js.

**El backend arranca pero la app no carga datos**
→ Verificá que el backend esté corriendo en el puerto 5000 y el frontend en el 5173. No cierres ninguna de las dos terminales.

**Error al instalar dependencias de Python**
→ Probá con `pip3 install -r requirements.txt` en lugar de `pip install -r requirements.txt`.
