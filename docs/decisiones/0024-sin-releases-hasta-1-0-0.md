---
estado: aceptado
fecha: 2026-11-20
---

# Sin Releases hasta la 1.0.0

Reemplaza la parte de los releases del ADR 0009: "SemVer 0.x desde la primera versión jugable" y "un tag `vX.Y.Z` en `main` dispara el workflow" en cada versión. El empaquetado, el workflow y el resto del ADR 0009 siguen vigentes.

## Contexto y problema

El ADR 0009 pide un Release en GitHub por cada versión 0.x. La 0.1.0 quedó lista en `main` el 2026-11-20, con el workflow de release probado en los tres sistemas. Antes de crear el tag, el autor decidió no publicar nada hasta la 1.0.0.

## Factores de decisión

- En un portafolio, un juego a medias da peor impresión que no tener descarga.
- Cada Release cuesta trabajo (tag, revisar los zips, las notas) y no aporta mientras nadie juegue.
- Que el workflow de release siga probado, para que la 1.0.0 no sea la primera vez que corre.

## Opciones consideradas

- Sin tags ni Releases hasta la 1.0.0
- Tags 0.x sin Release
- Un Release por versión 0.x, como pide el ADR 0009

## Resultado de la decisión

Elegimos **sin tags ni Releases hasta la 1.0.0** (decisión del autor, 2026-11-20):

- Las versiones 0.x siguen: viven en `pyproject.toml`, se suben con `uv version --bump` y nombran los milestones.
- No se crea ningún tag `vX.Y.Z` hasta la 1.0.0. Así `release.yml` no cambia: solo publica con un tag.
- Mientras tanto, se juega desde el código con `uv run circlebh`. El README no ofrece descargas.
- Los zips se siguen armando y probando a mano con `workflow_dispatch`, y en cada PR que cambia `release.yml`.
- La 1.0.0 es el primer Release. Las instrucciones para abrir el zip sin firma vuelven al README en ese momento.

### Consecuencias

- Bueno: lo único que se publica es el MVP completo.
- Bueno: no hay trabajo de release en cada versión 0.x.
- Malo: quien no tiene uv no puede jugar hasta la 1.0.0.
- Malo: el workflow de release solo se prueba si alguien lo corre a mano. El smoke se rompió entre el 2026-11-19 y el 2026-11-20 sin que nadie lo viera (PR #47).
- Malo: el historial de git no marca dónde termina cada versión 0.x. Los milestones y el commit que sube la versión cumplen ese papel.

### Confirmación

- `git tag --list 'v*'` no muestra nada mientras la versión de `pyproject.toml` sea 0.x.
- El README no enlaza a Releases antes de la 1.0.0.
- Al cerrar cada milestone 0.x, se corre el workflow de release con `workflow_dispatch` y queda en verde.

## Pros y contras de las opciones

### Sin tags ni Releases hasta la 1.0.0
- Bueno: no hay que cambiar el workflow.
- Bueno: es lo más simple.
- Malo: git no marca las versiones 0.x.

### Tags 0.x sin Release
- Bueno: git marca dónde termina cada versión.
- Malo: hay que cambiar `release.yml` para que no publique antes de la 1.0.0. Es una condición más que mantener.

### Un Release por versión 0.x
- Bueno: cualquiera juega cada versión sin uv, y se ve el avance.
- Malo: publica un juego a medias en el portafolio.
- Malo: cada versión carga con el trabajo de release.

## Más información

- ADR 0009, sección "Release por tag desde 0.x" y "Solo al terminar el MVP".
- PR #47: la 0.1.0 y el arreglo del smoke.
