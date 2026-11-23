[Español](README.md)

# CircleBH

A survivors-like game made in Python with [pygame-ce](https://pyga.me/). Everything is drawn with code: there are no sprites or images. The arena is a Cartesian plane, and the weapons are mathematical curves (a line, a circle, a sine wave, a spiral and a rose) traced live.

`CircleBH` is a working title.

> Work in progress. Version 0.1.0 is the first playable one: a point that shoots on its own at hexagons. Version 0.2.0 is under way on `main`, with more enemies and a run shaped like a house track. The curves come later.

## Play

For now, you play from source. Builds for Windows, macOS and Linux arrive with 1.0.0. You need [uv](https://docs.astral.sh/uv/) 0.13.7:

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

## Documents

The documents are in Spanish.

- [Game design](docs/diseno-del-juego.md): what the game is and how it plays.
- [Decisions](docs/decisiones/): the ADRs for the stack, the architecture, the tests and the process.
- [Plans](docs/planes/): the tasks in progress.
- [AGENTS.md](AGENTS.md): how work is done in the repo, for people and agents.

## Development

You need [uv](https://docs.astral.sh/uv/) 0.13.7. Download the right Python and install the dependencies:

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

[MIT](LICENSE).
