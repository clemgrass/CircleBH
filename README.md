# CircleBH

Un juego del género survivors hecho en Python con [pygame-ce](https://pyga.me/). Todo se dibuja con código: no hay sprites ni imágenes. El escenario es un plano cartesiano y las armas son curvas matemáticas (una recta, un círculo, un seno, una espiral y una rosa) que se trazan en vivo.

`CircleBH` es un nombre provisorio.

> En construcción. Todavía no hay nada jugable.

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
