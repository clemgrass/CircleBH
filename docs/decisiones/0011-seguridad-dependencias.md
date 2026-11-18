---
estado: aceptado
fecha: 2026-11-18
---

# Actualizar dependencias a mano y auditar con uv audit

## Contexto y problema

El proyecto no tiene secretos, ni web, ni datos de usuarios. El riesgo está en la cadena de suministro y en la CI. Hay que decidir cómo se mantienen al día las dependencias, cómo se detectan las vulnerabilidades conocidas y qué se endurece en GitHub.

## Factores de decisión

- Tener pocas piezas que mantener, porque trabaja una sola persona.
- Enterarse de las vulnerabilidades conocidas.
- Darle al token de la CI el mínimo de permisos.

## Opciones consideradas

- Actualizaciones: Dependabot con cooldown de 7 días, Renovate, o a mano.
- Vulnerabilidades: solo las alertas de Dependabot, `uv audit` en `poe check`, o `pip-audit` en `poe check`.
- Análisis: CodeQL en su configuración por defecto, CodeQL con zizmor, o nada.

## Resultado de la decisión

- **Actualizaciones a mano**, al empezar cada milestone: `uv lock --upgrade`, que respeta `exclude-newer` (ADR 0002), y una revisión de los SHA de las acciones. A favor: no hay PRs automáticos que revisar, y cada subida de versión es una decisión consciente.
- **Vulnerabilidades:**
  - `uv audit --locked --preview-features audit-command` corre dentro de `poe check`, no en `poe fast`. A favor: se ve en local y en la CI sin sumar dependencias;
  - si un aviso no aplica, se ignora con `--ignore <ID>` y el motivo queda escrito junto a la configuración;
  - las alertas de Dependabot quedan encendidas, sin PRs.
- **Sin análisis automático del código** (ni CodeQL ni zizmor). A favor: es lo más simple, y bastan las reglas de la CI endurecida y la revisión.
- **CI endurecida:**
  - `permissions: contents: read` por defecto, y `contents: write` solo en el job de release;
  - `actions/checkout` con `persist-credentials: false`;
  - acciones fijadas por SHA, con la versión en un comentario;
  - nunca `pull_request_target`.
- **En el repo:**
  - secret scanning con push protection;
  - reporte privado de vulnerabilidades;
  - *immutable releases*;
  - sin `SECURITY.md`.

### Consecuencias

- Bueno: hay pocas piezas, y cada actualización es una decisión.
- Malo: entre milestones, las versiones envejecen, y actualizar los SHA a mano es tedioso.
- Malo: `uv audit` es experimental. Puede cambiar, aunque fijar uv en 0.13.4 (ADR 0002) lo estabiliza.
- Malo: `poe check` necesita red, y la CI se puede poner roja por un aviso nuevo que no tiene que ver con el cambio.
- Malo: nadie revisa los workflows de forma automática.

### Confirmación

- `uv audit` corre en `poe check`.
- Los workflows declaran `permissions` y fijan sus acciones por SHA. Se ve en la revisión.
- La configuración de seguridad del repo se revisa con `gh api`.
- Pendiente de verificar al armar: el alcance de *immutable releases*.

## Pros y contras de las opciones

### Dependabot con cooldown
- Bueno: es nativo y alinea el cooldown con `exclude-newer`.
- Malo: abre PRs semanales.
- Malo: dice soportar uv v0.11, y no sabemos cómo trata nuestro `required-version` (no verificado).

### Renovate
- Bueno: es muy configurable.
- Malo: necesita una app de terceros con acceso al repo.

### A mano
- Bueno: no hay automatización que mantener.
- Malo: las versiones envejecen.

### Solo las alertas de Dependabot
- Bueno: no necesita red en el chequeo.
- Malo: no se ve en local.

### `uv audit`
- Bueno: no suma dependencias.
- Malo: es experimental y necesita red.

### `pip-audit`
- Bueno: es estable.
- Malo: es una dependencia más y también necesita red.

### CodeQL
- Bueno: es gratis y no hay que mantenerlo.
- Malo: es una pieza más de configuración.

### CodeQL con zizmor
- Bueno: revisa mejor los workflows.
- Malo: es otra dependencia.

### Nada
- Bueno: es lo más simple.
- Malo: no hay una segunda mirada automática.

## Más información

- https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference (consultado el 2026-11-18)
- https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection (consultado el 2026-11-18)
- `uv audit --help`, uv 0.13.4. Probado el 2026-11-18 en un proyecto temporal: funciona y avisa que es experimental.
