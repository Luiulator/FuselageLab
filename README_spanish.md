# FuselageLab

FuselageLab es una aplicación en Python para explorar el diseño de geometrías de fuselaje, estimar su aerodinámica a partir de correlaciones empíricas y exportar resultados.
Incluye una interfaz de escritorio moderna (CustomTkinter) que permite ajustar la configuración mediante un formulario categorizado, ejecutar los cálculos y visualizar un modelo 3D del fuselaje.

## Características

- **Interfaz Moderna**: Construida con CustomTkinter para una experiencia elegante y en modo oscuro.
- **Geometrías**: Se centra en formas aerodinámicas (series Haack, etc.) para minimizar la resistencia en regímenes subsónicos y transónicos.
- **Aerodinámica**: Correlaciones de fricción (laminar/transición/turbulento) y estimaciones basadas en Hoerner.
- **Análisis**: Calcula área mojada, volumen, posiciones del CG y propiedades de peso.
- **Salidas**: Perfiles CSV, resultados JSON y exportaciones STL (ASCII/Binario).
- **Visualización**: Visor 3D de *wireframe* integrado.

![Plane Airframe Geometry](readme/images/geom1.png)

## Requisitos

- Python 3.10+
- Paquetes:
  - `customtkinter`
  - `packaging`
  - `numpy`
  - `matplotlib`
  - `vtk` (opcional, para 3D avanzado)
  - `plotly` (opcional, para 3D interactivo)
  - `pywebview` (opcional, para 3D interactivo incrustado)

## Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/yourusername/FuselageLab.git
    cd FuselageLab
    ```

2.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Nota: En Arch/Manjaro, usa un entorno virtual o `--break-system-packages` si es necesario)*

## Ejecución

- **Iniciar la App**:
  ```bash
  python main.py
  ```
- **Modo Legado**:
  Si necesitas la interfaz antigua de Tkinter, ejecuta:
  ```bash
  python main_legacy.py
  ```

## Uso de la GUI

- **Barra Lateral**:
  - **Load/Save**: Gestiona tus archivos de configuración JSON.
  - **Configuration**: Pestañas para Geometría, Operación, Modelo CF, Constructor, Masa, E/S y Gráficas.
  - **Results**: Resumen en tiempo real de coeficientes aerodinámicos y propiedades geométricas.
  - **Actions**: Ejecutar la tubería, exportar archivos STL o abrir la carpeta de resultados.

- **Vista 3D**:
  - El panel izquierdo muestra una representación *wireframe* 3D de tu fuselaje.
  - Se actualiza automáticamente tras una ejecución exitosa.

## Estructura del Proyecto

- `main.py`: Nuevo punto de entrada (App CustomTkinter).
- `main_legacy.py`: Antiguo punto de entrada (Tkinter Estándar).
- `src/gui/`:
  - `app.py`: Lógica principal de la aplicación.
  - `views/`: Componentes de la interfaz (ConfigForm, ResultsPanel).
  - `viewers/`: Implementaciones del visor 3D.
- `src/pipeline.py`: Orquesta el flujo de cálculo.
- `src/build.py`: Generación de geometría.
- `src/calcs.py`: Cálculos aerodinámicos y geométricos.
- `results/`: Directorio de salida.

## Licencia

No se ha definido ninguna licencia en este repositorio.
