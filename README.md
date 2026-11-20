# CircleBH

Un juego del género survivors hecho en Python con [pygame-ce](https://pyga.me/). Todo se dibuja con código: no hay sprites ni imágenes. El escenario es un plano cartesiano y las armas son curvas matemáticas (una recta, un círculo, un seno, una espiral y una rosa) que se trazan en vivo.

`CircleBH` es un nombre provisorio.

> En construcción. La 0.1.0 es la primera versión jugable: un punto que dispara solo contra hexágonos. Las curvas llegan después.

## Jugar

Descarga el zip de tu sistema desde [Releases](https://github.com/clemgrass/CircleBH/releases): Windows x64, macOS con Apple Silicon o Linux x64. Descomprímelo y abre `circlebh` (en Windows, `circlebh.exe`) dentro de la carpeta `circlebh`.

| Acción | Teclado | Control |
|---|---|---|
| Moverse | WASD o flechas | stick izquierdo o cruceta |
| Reiniciar al morir | R | ✕ o □ en PlayStation; A o X en Xbox |
| Pantalla completa | F11 | |
| Salir | Escape | |

### La primera vez

El juego no está firmado, así que el sistema avisa la primera vez que lo abres.

- **Windows:** aparece el aviso azul de SmartScreen. Elige **Más información** y después **Ejecutar de todas formas**. Si tienes activado el Control inteligente de aplicaciones de Windows 11, no deja abrirlo.
- **macOS:** el sistema dice que no puede verificar `circlebh`. Ve a **Configuración del Sistema > Privacidad y seguridad**, busca el aviso en **Seguridad** y elige **Abrir de todos modos**. El botón dura cerca de una hora después del intento. Si vuelve a avisar por otros archivos de la carpeta, quítale la cuarentena a toda la carpeta desde la Terminal:

  ```
  xattr -dr com.apple.quarantine circlebh
  ```

- **Linux:** abre `./circlebh` desde la carpeta.

Si prefieres no abrir un ejecutable sin firma, juega desde el código con `uv run circlebh` (ver [Desarrollo](#desarrollo)).

## Documentos

- [Diseño del juego](docs/diseno-del-juego.md): qué es y cómo se juega.
- [Decisiones](docs/decisiones/): los ADR del stack, la arquitectura, los tests y el proceso.
- [Planes](docs/planes/): las tareas en curso.
- [AGENTS.md](AGENTS.md): cómo se trabaja en el repo, para personas y agentes.

## Desarrollo

Necesitas [uv](https://docs.astral.sh/uv/) 0.13.7. Descarga el Python correcto e instala las dependencias:

```
uv sync
uv run pre-commit install
```

`pre-commit install` hace que cada commit corra `uv run poe fast`. Los comandos del día a día están en [AGENTS.md](AGENTS.md).

Si trabajas con Claude Code, instala una vez por clon el plugin que activa `.claude/settings.json`:

```
claude plugin install superpowers@claude-plugins-official --scope project
```

## Licencia

[MIT](LICENSE).
