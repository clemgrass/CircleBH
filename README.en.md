[Español](README.md)

# CircleBH

A survivors-like game made in Python with [pygame-ce](https://pyga.me/). Everything is drawn with code: there are no sprites or images. The arena is a Cartesian plane, and every attack is a point that follows a mathematical function. Upgrading a weapon means changing its function.

`CircleBH` is a working title.

> Work in progress. Version 0.2.0 brings ten enemies and a run shaped like a house track, which ends in an endless mode that keeps getting harder. The point shoots on its own in a straight line. When you level up, you pick a card: upgrade a weapon, upgrade yourself or add another point. The upgrade catalog comes later.

## Play

For now, you play from source. Builds for Windows, macOS and Linux arrive with 1.0.0. You need [uv](https://docs.astral.sh/uv/) 0.13.9:

```
git clone https://github.com/clemgrass/CircleBH.git
cd CircleBH
uv run circlebh
```

| Action | Keyboard | Gamepad |
|---|---|---|
| Move | WASD or arrow keys | left stick or D-pad |
| Restart after dying | R | ✕ or □ on PlayStation; A or X on Xbox |
| Fullscreen | F11 | |
| Quit | Escape | |

itch.io page: https://cgrassdev.itch.io/circle-bh

## Weapons

Every attack is a point. Each weapon is a function that tells where the point is `t` seconds after the shot. You start with `f₁`, which moves in a straight line:

```
f₁(t) = p₀ + v·t·û
```

`p₀` is where you were when you shot, `v` is the speed and `û` the direction. The point aims at where it will meet the enemy, not at where the enemy is.

When you level up, you can add `f₂`, `f₃` and `f₄`. Each one starts out equal to `f₁` and is upgraded on its own. The `k`-th one aims at the `k`-th nearest enemy, and if there are fewer enemies than weapons, the count wraps around: with two enemies, `f₃` goes back to the nearest one. That way the fire spreads out by itself.

## Documents

The documents are in Spanish.

- [Game design](docs/diseno-del-juego.md): what the game is and how it plays.
- [Decisions](docs/decisiones/): the ADRs for the stack, the architecture, the tests and the process.
- [Plans](docs/planes/): the tasks in progress.
- [AGENTS.md](AGENTS.md): how work is done in the repo, for people and agents.

## Development

You need [uv](https://docs.astral.sh/uv/) 0.13.9. Download the right Python and install the dependencies:

```
uv sync
uv run pre-commit install
```

`pre-commit install` makes every commit run `uv run poe fast`. The everyday commands are in [AGENTS.md](AGENTS.md).

If you work with Claude Code, install once per clone the plugin that `.claude/settings.json` enables:

```
claude plugin install superpowers@claude-plugins-official --scope project
```

## License

[MIT](LICENSE). Third-party material included in the repo, with its license, is listed in [CREDITS.md](CREDITS.md).
