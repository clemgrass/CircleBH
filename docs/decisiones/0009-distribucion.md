---
estado: aceptado
fecha: 2026-11-18
---

# Distribuir con PyInstaller en zips por sistema, con release por tag

## Contexto y problema

En un portafolio, quien no puede jugar en dos minutos no juega. Un reclutador no tiene uv; un desarrollador quiere leer el código. Hay que decidir por qué canales se distribuye, con qué se arman los ejecutables y cómo se versiona.

## Factores de decisión

- Que sea fácil jugar sin instalar herramientas.
- Que los builds sean reproducibles desde la CI.
- Que se pueda mostrar el avance del proyecto.

## Opciones consideradas

- Canales: Releases y código fuente; solo código fuente; o Releases y PyPI.
- Empaquetado: PyInstaller en carpeta (onedir); PyInstaller en un solo archivo; Nuitka; o cx_Freeze (no discutida).
- Versiones: SemVer 0.x con release por tag; un solo release al terminar el MVP; o SemVer con un CHANGELOG.md a mano.

## Resultado de la decisión

- **Canales:** ejecutables en GitHub Releases, y `uv run circlebh` desde el código.
- **Empaquetado:**
  - PyInstaller 6.22.3, que funciona sin configuración extra porque pygame-ce trae su propio hook;
  - modo carpeta, comprimida en un zip por sistema;
  - una matriz en la CI para Windows x64, macOS ARM y Linux x64, porque PyInstaller no compila para otros sistemas.
- **Sin firma de código:** el README explica cómo abrir el juego la primera vez.
- **`balance.json`:** va dentro del paquete y se lee con `importlib.resources` (ADR 0004).
- **Versiones:**
  - SemVer 0.x desde la primera versión jugable, y 1.0.0 es el MVP completo;
  - la versión vive solo en `pyproject.toml` y se sube con `uv version --bump`.
- **Release:**
  - un tag `vX.Y.Z` en `main` dispara el workflow;
  - el workflow arma los tres zips, los prueba abriéndolos en modo demo sin ventana y crea el Release;
  - las notas las genera GitHub a partir de los títulos de los PRs, y no hay `CHANGELOG.md`.

### Consecuencias

- Bueno: cualquiera descarga y juega, y quien quiere leer el código lo corre con uv.
- Bueno: el portafolio muestra el avance versión por versión.
- Malo: hay un workflow de tres sistemas que mantener.
- Malo: SmartScreen en Windows y Gatekeeper en macOS advierten, porque no hay firma (no verificado).
- Malo: hay que descomprimir el zip y buscar el ejecutable adentro.

### Confirmación

- El workflow de release falla si un ejecutable no arranca en modo demo. Así se comprueba también que `balance.json` viajó dentro.
- Pendiente de verificar al armar: que el runner de macOS sea ARM y que el driver de video sin ventana funcione en los tres sistemas.

## Pros y contras de las opciones

### Releases y código fuente
- Bueno: sirve a los dos públicos.
- Malo: hay que mantener el workflow de release.

### Solo código fuente
- Bueno: no hay builds que mantener.
- Malo: exige tener uv.

### Releases y PyPI
- Bueno: basta con `uvx circlebh`.
- Malo: es otro canal que mantener.

### PyInstaller en carpeta
- Bueno: abre rápido y tiene menos falsos positivos de antivirus (no verificado).
- Malo: hay que descomprimir.

### PyInstaller en un solo archivo
- Bueno: es lo más cómodo.
- Malo: arranca lento y los antivirus lo marcan más (no verificado).

### Nuitka
- Bueno: compila a C.
- Malo: necesita un compilador por sistema, tarda más y declara soporte solo hasta Python 3.14.

### cx_Freeze (no discutida)
- Bueno: soporta Python 3.14 y 3.15.
- Malo: se usa menos con Pygame, y pygame-ce no trae un hook para él (no verificado).

### Release por tag desde 0.x
- Bueno: se ve el avance.
- Malo: hay que cuidar los títulos de los PRs.

### Solo al terminar el MVP
- Bueno: hay menos que mantener mientras tanto.
- Malo: no hay nada jugable hasta el final.

### CHANGELOG.md a mano
- Bueno: se lee mejor.
- Malo: es un paso más en cada release.

## Más información

- https://pyinstaller.org/en/stable/usage.html ("no es un compilador cruzado"; consultado el 2026-11-18)
- https://github.com/pygame-community/pygame-ce/tree/main/src_py/__pyinstaller (consultado el 2026-11-18)
- https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes (consultado el 2026-11-18)
- `uv version --help`, uv 0.13.4
