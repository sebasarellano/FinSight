
from flask import Flask

# Crear la aplicación web
app = Flask(__name__)


# Definir la página principal
@app.route("/")
def home():
    return "<h1>FinSight</h1><p>Mi aplicación de finanzas personales está funcionando.</p>"


# Ejecutar el servidor local
if __name__ == "__main__":
    app.run(debug=True)
