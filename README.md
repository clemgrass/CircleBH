[English](README.en.md)

# CircleBH

Un juego del género survivors hecho en Python con [pygame-ce](https://pyga.me/). Todo se dibuja con código: no hay sprites ni imágenes. El escenario es un plano cartesiano, y cada ataque es un punto que sigue una función matemática. Mejorar un arma es cambiar su función.

`CircleBH` es un nombre provisorio.

> En construcción. La 0.2.0 trae diez enemigos y una partida con la forma de un tema de house, que termina en un modo infinito cada vez más difícil. El punto dispara solo en línea recta. Al subir de nivel eliges una tarjeta: mejorar un arma, mejorarte a ti o sumar otro punto. El catálogo de mejoras llega después.

## Jugar

Por ahora se juega desde el código. Los ejecutables para Windows, macOS y Linux llegan con la 1.0.0. Necesitas [uv](https://docs.astral.sh/uv/) 0.13.9:

```
git clone https://github.com/clemgrass/CircleBH.git
cd CircleBH
uv run circlebh
```

| Acción | Teclado | Control |
|---|---|---|
| Moverse | WASD o flechas | stick izquierdo o cruceta |
| Reiniciar al morir | R | ✕ o □ en PlayStation; A o X en Xbox |
| Pantalla completa | F11 | |
| Salir | Escape | |

Página en itch.io: https://cgrassdev.itch.io/circle-bh

## Las armas

Todo ataque es un punto. Cada arma es una función que dice dónde está el punto `t` segundos después del disparo. Partes con `f₁`, que avanza en línea recta:

```
f₁(t) = p₀ + v·t·û
```

`p₀` es donde estabas al disparar, `v` es la rapidez y `û` la dirección. El punto apunta a donde se va a cruzar con el enemigo, no a donde está.

Al subir de nivel puedes sumar `f₂`, `f₃` y `f₄`. Cada una parte igual a `f₁` y se mejora por su lado. La `k`-ésima apunta al `k`-ésimo enemigo más cercano, y si hay menos enemigos que armas, la cuenta da la vuelta: con dos enemigos, `f₃` vuelve al más cercano. Así el fuego se reparte solo.

## Documentos

- [Diseño del juego](docs/diseno-del-juego.md): qué es y cómo se juega.
- [Decisiones](docs/decisiones/): los ADR del stack, la arquitectura, los tests y el proceso.
- [Planes](docs/planes/): las tareas en curso.
- [AGENTS.md](AGENTS.md): cómo se trabaja en el repo, para personas y agentes.

## Desarrollo

Necesitas [uv](https://docs.astral.sh/uv/) 0.13.9. Descarga el Python correcto e instala las dependencias:

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

[MIT](LICENSE). Lo que el repo incluye de terceros, con su licencia, está en [CREDITS.md](CREDITS.md).
