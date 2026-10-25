# FinSight

Aplicación web local para gestionar y analizar las finanzas personales, desarrollada con Python, Flask y SQLite.

FinSight permite registrar movimientos financieros, administrar cuentas, visualizar la evolución mensual del dinero y establecer presupuestos por categoría. El proyecto se desarrolla como una aplicación local, sin depender de servicios de pago ni APIs externas.

## Objetivos del proyecto

FinSight tiene dos objetivos principales:

- **Desarrollo de producto:** construir una aplicación de finanzas personales funcional, visual y fácil de utilizar.
- **Aprendizaje de ingeniería de software:** practicar Git y GitHub mediante el control de versiones, ramas, commits, Issues, Pull Requests y documentación.

## Funcionalidades

### Dashboard financiero
- Resumen de ingresos, gastos, saldo y ahorro neto.
- Gráfico de flujo mensual de ingresos y gastos.
- Actualización de los indicadores a partir de los movimientos registrados.

### Gestión de movimientos
- Registrar ingresos y gastos.
- Editar y eliminar movimientos.
- Consultar y organizar los movimientos mediante las opciones disponibles en la interfaz.
- Clasificar los movimientos por categoría.

### Gestión de cuentas
- Consultar las cuentas y sus saldos calculados.
- Editar la información de las cuentas existentes.
- Gestionar saldos iniciales, incluidos saldos negativos.

### Presupuestos
- Definir límites de gasto por categoría y mes.
- Actualizar el importe de un presupuesto existente.
- Consultar el importe gastado, el disponible y el porcentaje utilizado.
- Visualizar indicadores de seguimiento según el nivel de uso del presupuesto.

Los presupuestos se calculan por categoría y mes. Las transferencias no se contabilizan como gastos en los resúmenes ni en el seguimiento presupuestario.

## Tecnologías

- **Python 3.11:** lenguaje de programación.
- **Flask:** framework para la aplicación web.
- **SQLite:** base de datos relacional local.
- **HTML y CSS:** estructura, estilos y visualizaciones del dashboard.
- **Git y GitHub:** control de versiones y gestión del desarrollo.
- **pytest:** herramienta declarada para pruebas automatizadas.

## Requisitos

Para ejecutar FinSight necesitas:

- Windows.
- Python 3.11 o una versión compatible.
- Git.
- Un navegador web moderno.

No se necesita contratar hosting ni configurar un servidor externo.

## Instalación y ejecución

### 1. Clonar el repositorio

Si todavía no tienes una copia local del proyecto, ejecuta:

```powershell
git clone https://github.com/sebasarellano/FinSight.git
cd FinSight
```

Si ya tienes el proyecto en tu equipo, abre su carpeta en VS Code y continúa con el siguiente paso.

### 2. Crear un entorno virtual

```powershell
python -m venv .venv
```

### 3. Activar el entorno virtual

En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la ejecución del script de activación, puedes utilizar el mecanismo de activación apropiado para tu configuración de Windows o consultar la documentación oficial de Python.

### 4. Instalar las dependencias

```powershell
python -m pip install -r requirements.txt
```

### 5. Ejecutar la aplicación

```powershell
python app.py
```

Abre la siguiente dirección en tu navegador:

http://127.0.0.1:5000

Para detener la aplicación, vuelve a la terminal y presiona `Ctrl + C`.

## Estructura del proyecto

```text
FinSight/
├── app.py                  # Aplicación Flask y rutas
├── database.py             # Gestión del esquema de SQLite
├── requirements.txt        # Dependencias de Python
├── README.md               # Documentación del proyecto
├── .gitignore              # Archivos excluidos de Git
├── instance/
│   └── finsight.db         # Base de datos local
├── templates/
│   ├── base.html           # Plantilla base
│   ├── dashboard.html      # Dashboard financiero
│   ├── transactions.html   # Gestión de movimientos
│   ├── edit_transaction.html
│   ├── accounts.html       # Gestión de cuentas
│   ├── edit_account.html
│   └── budgets.html        # Gestión de presupuestos
└── static/
    └── css/
        └── styles.css      # Estilos de la interfaz
```

## Base de datos y datos de ejemplo

FinSight utiliza SQLite para almacenar la información localmente. La base de datos se encuentra en `instance/finsight.db` y está excluida del control de versiones mediante `.gitignore`.

La versión actual utiliza datos ficticios. No introduzcas información financiera sensible en esta versión sin revisar previamente las medidas de seguridad y respaldo.

La base de datos local no se incluye en el repositorio. Al ejecutar la aplicación, se inicializa el esquema necesario y se crean las cuentas de ejemplo cuando corresponde. La aplicación no incluye un mecanismo automático de migración para modificar la estructura de tablas existentes.

## Estado del proyecto

FinSight se encuentra en desarrollo. La versión inicial se centra en las funcionalidades principales de seguimiento financiero y en el aprendizaje progresivo de herramientas de desarrollo.

Las funcionalidades futuras se incorporarán a medida que se implementen y validen.

## Autor

Sebastián Arellano

Desarrollado como proyecto personal de aprendizaje en programación, análisis de datos y gestión de versiones con Git y GitHub.
