# Conciliación Bancaria

Aplicación web para conciliar el **Mayor Contable** contra el **Extracto Bancario**. Subís los dos archivos, la app los cruza automáticamente y descargás un Excel con el resultado listo para usar.

---

## Cómo instalar y usar (guía para el contador)

### Paso 1 — Instalar Python

1. Abrí el navegador y entrá a **https://www.python.org/downloads/**
2. Hacé clic en el botón grande amarillo de descarga.
3. Ejecutá el instalador.
4. **MUY IMPORTANTE**: antes de hacer clic en "Install Now", tildá la opción que dice **"Add Python to PATH"** (está abajo del todo en la primera pantalla).
5. Hacé clic en **Install Now** y esperá que termine.

---

### Paso 2 — Instalar Node.js

1. Abrí el navegador y entrá a **https://nodejs.org**
2. Hacé clic en el botón de la izquierda que dice **LTS**.
3. Ejecutá el instalador con todas las opciones por defecto (seguí haciendo clic en "Next" hasta que diga "Finish").

---

### Paso 3 — Descargar el programa

1. Entrá a **https://github.com/julietaramos/conciliacion-bancaria-**
2. Hacé clic en el botón verde que dice **"< > Code"**.
3. Hacé clic en **"Download ZIP"**.
4. Descomprimí el ZIP en una carpeta de tu computadora (por ejemplo, en el Escritorio o en Documentos).

---

### Paso 4 — Abrir el programa

1. Abrí la carpeta que descomprimiste.
2. Hacé **doble clic** en el archivo **`iniciar.bat`**.

> La primera vez va a instalar algunos componentes automáticamente — puede tardar unos minutos. Las veces siguientes arranca directo.

3. Se va a abrir el programa en el navegador. Listo.

---

### ¿Cómo cerrar el programa cuando terminás?

En la barra de tareas (abajo), vas a ver dos ventanas minimizadas llamadas **"Backend - Conciliacion"** y **"Frontend - Conciliacion"**. Clic derecho → Cerrar ventana en cada una.

---

## Cómo usar la aplicación

### 1. Agregar un banco
En el menú lateral, entrá a **Bancos** → hacé clic en **Agregar banco** → escribí el nombre (ej: "Galicia Cuenta Corriente") → Guardar.

### 2. Conciliar
Desde la lista de bancos hacé clic en **Conciliar**. Se abre un formulario donde subís:
- **Mayor Contable**: el libro de tu sistema contable para ese período (`.xlsx`, `.xls` o `.csv`).
- **Extracto Bancario**: el extracto del banco para el mismo período (`.csv` o `.txt`).

Hacé clic en **Conciliar** y esperás unos segundos.

### 3. Descargar el resultado
La app muestra un resumen con los movimientos conciliados y las partidas pendientes. Desde ahí podés **descargar el Excel** con el resultado completo.

> **Carry-over automático**: las partidas que quedaron pendientes el mes anterior se cargan solas en la próxima conciliación — no tenés que hacer nada.

### Formatos de archivo soportados

| Archivo | Formatos |
|---|---|
| Mayor Contable | `.xlsx`, `.xls`, `.csv` |
| Extracto Bancario | `.csv`, `.txt` |

Bancos soportados: Galicia, Nación, Santander, BBVA y cualquier banco con columnas estándar.

> **Banco Provincia**: exportá el extracto como Excel desde el home banking — el PDF no es compatible.

---

## Problemas frecuentes

**El archivo `iniciar.bat` no abre o da error de Python**
→ Revisá que durante la instalación de Python hayas tildado **"Add Python to PATH"**. Si no lo hiciste, desinstalá Python y volvé a instalarlo tildando esa opción. Reiniciá la computadora.

**El programa no abre en el navegador automáticamente**
→ Abrí el navegador manualmente y escribí en la barra de direcciones: `http://localhost:5173`

**Error al instalar componentes (paso de la primera vez)**
→ Revisá que tengas conexión a internet y volvé a hacer doble clic en `iniciar.bat`.

---

## Stack técnico

- **Backend**: Python + FastAPI + SQLAlchemy
- **Base de datos**: SQLite local (se crea automáticamente)
- **Frontend**: React 18 + Vite
