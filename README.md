# FinSight

Aplicación web **local** de finanzas personales, desarrollada con Python, Flask y SQLite. Permite registrar movimientos, consultar cuentas y controlar presupuestos mensuales por categoría, sin depender de servicios externos, cuentas de pago ni claves de API.

FinSight nació con dos objetivos: construir una herramienta útil y visualmente cuidada, y aprender ingeniería de software real con Git y GitHub (ramas, commits, Issues, Pull Requests, pruebas automáticas y releases).

> **Aviso:** FinSight es un proyecto personal de aprendizaje. Usa **datos ficticios**. No introduzcas información bancaria ni datos financieros sensibles reales.

## Funcionalidades de la versión 0.1.0

### Dashboard
- Saldo total y saldo de cada cuenta.
- Ingresos, gastos y ahorro neto del mes actual.
- Gráfico de barras con los ingresos y gastos de los últimos seis meses.
- Últimos movimientos registrados.

### Movimientos
- Registrar ingresos y gastos con descripción, importe, categoría, fecha y cuenta.
- Editar y eliminar movimientos (con confirmación).
- Validación de los datos en el servidor: importes entre 0,01 y 1.000.000.000 con dos decimales, fechas reales, categorías y cuentas existentes.

### Cuentas
- Consultar las cuentas con su saldo inicial y su saldo actual.
- Editar nombre, tipo y saldo inicial (se admiten saldos negativos para deudas).

### Presupuestos
- Definir un límite mensual por categoría de gasto.
- Ver lo gastado, lo disponible y el porcentaje de uso, con aviso visual al llegar al 80 % y al superar el 100 %.
- Actualizar un presupuesto volviendo a guardarlo para la misma categoría y mes, o eliminarlo.

Las transferencias entre cuentas no cuentan como ingresos ni gastos.

## Limitaciones conocidas

Esta es una primera versión. Lo siguiente **no está incluido** todavía:

- Filtros, búsqueda y ordenamiento de movimientos.
- Importación y exportación de archivos CSV.
- Distribución de gastos por categoría en el dashboard.
- Crear o eliminar cuentas desde la interfaz, y crear transferencias (la base de datos ya las contempla).
- Autenticación: la aplicación es de un solo usuario y solo para uso local. Los formularios no incluyen protección CSRF, por lo que **no debe exponerse a internet ni a una red compartida**.
- Migraciones de la base de datos: si el esquema cambia en una versión futura, habrá que recrear la base local.
- Los importes se guardan como números decimales de coma flotante, adecuado para uso personal pero no para contabilidad formal.

## Tecnologías

- **Python 3.11**
- **Flask**: framework web.
- **SQLite**: base de datos local, incluida en Python.
- **HTML y CSS**: interfaz y visualizaciones.
- **pytest**: pruebas automáticas.
- **GitHub Actions**: ejecuta las pruebas en cada Pull Request.

## Requisitos

- Windows (probado en Windows con PowerShell y Visual Studio Code).
- Python 3.11 o superior.
- Git.
- Un navegador web moderno.

## Instalación y ejecución

### 1. Clonar el repositorio

```powershell
git clone https://github.com/sebasarellano/FinSight.git
cd FinSight
```

### 2. Crear y activar un entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell muestra un error de ejecución de scripts, permite los scripts firmados localmente para tu usuario y vuelve a activar:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Alternativa sin cambiar ninguna política: usa el Símbolo del sistema (CMD) y ejecuta `.venv\Scripts\activate.bat`.

Sabrás que el entorno está activo porque verás `(.venv)` al inicio de la línea de la terminal.

### 3. Instalar las dependencias

```powershell
python -m pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```powershell
python app.py
```

Abre <http://127.0.0.1:5000> en tu navegador. Para detener la aplicación, vuelve a la terminal y pulsa `Ctrl + C`.

La primera vez que se ejecuta, FinSight crea automáticamente la carpeta `instance/` con la base de datos y tres cuentas de ejemplo (Efectivo, Cuenta bancaria y Ahorros).

> `python app.py` inicia el servidor de desarrollo de Flask con el modo de depuración activado. Es adecuado para uso local, pero no para exponerlo en una red.

## Pruebas automáticas

Con el entorno virtual activado:

```powershell
python -m pytest -v
```

Las pruebas usan una base de datos temporal, así que nunca modifican tus datos locales. GitHub Actions las ejecuta en cada Pull Request y en cada cambio a `main`.

## Estructura del proyecto

```text
FinSight/
├── app.py                      # Aplicación Flask: rutas, validación y cálculos
├── database.py                 # Conexión y esquema de SQLite
├── requirements.txt            # Dependencias de Python
├── pytest.ini                  # Configuración de pytest
├── README.md                   # Esta documentación
├── .gitignore                  # Archivos excluidos de Git
├── .github/
│   └── workflows/
│       └── tests.yml           # Pruebas automáticas en GitHub Actions
├── templates/                  # Plantillas HTML (Jinja2)
│   ├── base.html
│   ├── dashboard.html
│   ├── transactions.html
│   ├── edit_transaction.html
│   ├── accounts.html
│   ├── edit_account.html
│   └── budgets.html
├── static/
│   └── css/
│       └── styles.css          # Estilos de la interfaz
└── tests/
    ├── conftest.py             # Preparación común: base de datos temporal
    ├── test_transactions.py    # Pruebas de movimientos y saldos
    └── test_budgets.py         # Pruebas de presupuestos
```

La carpeta `instance/` se crea al ejecutar la aplicación y **no se incluye en el repositorio**.

## Seguridad y datos locales

- La base de datos está en `instance/finsight.db`.
- La clave secreta de Flask se genera al azar la primera vez y se guarda en `instance/secret_key`.
- Ambos archivos están excluidos de Git mediante `.gitignore`. Nunca los subas al repositorio.
- Si una clave o dato sensible llegara a subirse a GitHub, añadirlo después a `.gitignore` **no lo elimina del historial**: habría que tratarlo como comprometido y reemplazarlo.

## Estado del proyecto

Primera versión (v0.1.0). Las siguientes versiones están pensadas para incluir filtros y búsqueda, importación y exportación CSV, gráficos por categoría y una interfaz más cuidada.

## Licencia

Distribuido bajo la licencia MIT. Consulta el archivo [LICENSE](LICENSE).

## Autor

Sebastián Arellano
