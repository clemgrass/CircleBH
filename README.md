[English](README.en.md)

# CircleBH

Un juego del género survivors hecho en Python con [pygame-ce](https://pyga.me/). Todo se dibuja con código: no hay sprites ni imágenes. El escenario es un plano cartesiano y las armas son curvas matemáticas (una recta, un círculo, un seno, una espiral y una rosa) que se trazan en vivo.

`CircleBH` es un nombre provisorio.

> En construcción. La 0.2.0 trae diez enemigos y una partida con la forma de un tema de house, que termina en un modo infinito cada vez más difícil. El punto dispara solo en línea recta, y al subir de nivel puedes sumar el círculo. Las demás curvas llegan después.

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

Cada arma es una fórmula. El **círculo** es una curva polar centrada en el jugador, que crece a `v` unidades por segundo hasta su alcance `R`, donde revienta:

```
ρ(θ, t) = min(v·t, R)
```

Daña por barrido. En cada paso, la curva se muestrea en puntos, y cada punto actúa como una bala que va de donde estaba a donde está. Como la bala, el anillo se gasta donde pega: le quita al enemigo la primera línea que barre, la que mira al jugador, y pierde el arco que lo cubría. Un enemigo de radio `r` a distancia `d` se lleva el arco `φ ± asin(r/d)`, y ahí el anillo queda con un hueco. El círculo se toma como arma nueva al subir de nivel.

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
