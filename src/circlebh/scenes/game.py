"""La partida en pantalla: lee la entrada, avanza `world` paso a paso y lo dibuja."""

import random

import pygame
import pygame._sdl2.controller as sdl_controller
from pygame.math import Vector2

from circlebh.audio.sequencer import Sequencer
from circlebh.balance import BALANCE
from circlebh.cli import RunOptions
from circlebh.controls import (
    axis_to_unit,
    combine,
    is_restart,
    keyboard_intent,
    stick_intent,
)
from circlebh.pilot import pilot_intent
from circlebh.render.palette import DARK
from circlebh.render.plane import draw_axes, draw_letterbox
from circlebh.render.world_view import draw_world
from circlebh.scenes.death import EFFECT_STEPS, DeathScreen
from circlebh.scenes.music import MusicPlayer, music_enabled
from circlebh.scenes.scenarios import SCENARIOS, Scenario
from circlebh.seeds import next_seed
from circlebh.settings import Settings
from circlebh.viewport import Viewport, camera_center
from circlebh.world.clock import STEP
from circlebh.world.director import bar_at
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.swarm import lattice

DEMO_RESTART_STEPS = round(2.0 / STEP)
"""En la demo y las capturas, cuántos pasos se ve la muerte antes de reiniciar: 2 s."""


class Gamepads:
    """Los controles conectados. Se pueden conectar y desconectar con el juego abierto.

    Usa la API de controles de SDL, con el layout con nombre (ADR 0019). Es el único
    módulo del juego que la toca; fuera del juego, solo `tools/diagnostico_control.py`.
    Cada control se guarda con el `instance_id` de su
    joystick: el alta trae `device_index` y la baja trae `instance_id`.
    """

    def __init__(self) -> None:
        sdl_controller.init()
        self._pads: dict[int, sdl_controller.Controller] = {}

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.CONTROLLERDEVICEADDED:
            try:
                pad = sdl_controller.Controller(event.device_index)
            except pygame.error:
                # Se desconectó entre el aviso y la apertura: llega su baja y listo.
                return
            self._pads[pad.as_joystick().get_instance_id()] = pad
        elif (
            event.type == pygame.CONTROLLERDEVICEREMOVED
            and event.instance_id in self._pads
        ):
            # Hay que soltarlo: un control quitado sigue devolviendo su último valor,
            # y un stick inclinado al desconectar movería al jugador para siempre.
            self._pads.pop(event.instance_id).quit()

    def intents(self, deadzone: float) -> list[Vector2]:
        """La intención de cada control conectado: el stick izquierdo y la cruceta."""
        intents = []
        for pad in self._pads.values():
            if not pad.attached():
                continue
            x = axis_to_unit(pad.get_axis(pygame.CONTROLLER_AXIS_LEFTX))
            y = axis_to_unit(pad.get_axis(pygame.CONTROLLER_AXIS_LEFTY))
            intents.append(stick_intent(x, y, deadzone))
            intents.append(
                keyboard_intent(
                    left=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_LEFT),
                    right=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_RIGHT),
                    up=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_UP),
                    down=pad.get_button(pygame.CONTROLLER_BUTTON_DPAD_DOWN),
                )
            )
        return intents


def keys_intent() -> Vector2:
    """WASD y flechas."""
    keys = pygame.key.get_pressed()
    return keyboard_intent(
        left=keys[pygame.K_a] or keys[pygame.K_LEFT],
        right=keys[pygame.K_d] or keys[pygame.K_RIGHT],
        up=keys[pygame.K_w] or keys[pygame.K_UP],
        down=keys[pygame.K_s] or keys[pygame.K_DOWN],
    )


class GameScene:
    """La partida en pantalla, y sus reinicios. En la demo, el escenario manda.

    Al morir, `world` se detiene y la escena sigue contando pasos para el efecto de
    muerte. Cuando termina el efecto, R o X empiezan otra partida. En la demo, empieza
    sola tras `DEMO_RESTART_STEPS`.
    """

    def __init__(self, options: RunOptions, settings: Settings) -> None:
        self.options = options
        self.settings = settings
        self.demo: Scenario | None = (
            SCENARIOS[options.scenario] if options.demo else None
        )
        self.gamepads = Gamepads() if self.demo is None else None
        # ADR 0023: el fondo negro de fábrica, o su negativo si el jugador lo pide.
        self.palette = DARK.inverted() if settings.accessibility.invert_colors else DARK
        self.death_screen = DeathScreen(self.palette)
        self.music: Sequencer | None = None
        self.music_player: MusicPlayer | None = None
        if music_enabled(options, settings):
            audio = settings.audio
            player = MusicPlayer(audio.volume)
            if player.available:
                self.music_player = player
                self.music = Sequencer(
                    options.seed,
                    base_volume=audio.base_volume,
                    game_volume=audio.game_volume,
                )
        self.game = 0
        """Cuántas veces se reinició: la primera partida es la 0."""
        self.start(options.seed)

    def start(self, seed: int) -> None:
        """Empieza una partida nueva con `seed`. La semilla se imprime para repetirla."""
        print(f"semilla: {seed}")
        self.seed = seed
        demo = self.demo
        self.world = World(
            BALANCE,
            random.Random(seed),
            lethal=demo is None or demo.lethal,
            armed=demo is None or demo.armed,
        )
        if demo is not None and demo.crowd:
            spec = BALANCE.enemies[demo.crowd_enemy]
            center = Vector2(demo.crowd_center)
            self.world.enemies += [
                Enemy(spec, p) for p in lattice(center, demo.crowd, demo.crowd_spacing)
            ]
        if demo is not None and demo.guest is not None:
            guest = Enemy(BALANCE.enemies[demo.guest], Vector2(demo.guest_at))
            for k in demo.guest_wounded:
                guest.remove_edge(k)
            self.world.enemies.append(guest)
        self.dead_steps = 0
        self.section = -1
        """La última sección anotada en la consola."""
        self.log_section()
        if self.music is not None:
            self.music.start_game(seed)

    def log_section(self) -> None:
        """Anota en la consola la sección del tema cuando cambia, con su compás."""
        director = self.world.director
        if director.section_index != self.section:
            self.section = director.section_index
            bar = bar_at(self.world.steps, director.spec.bpm)
            print(f"compás {bar:.1f}: {director.section.name}")

    def restart(self) -> None:
        """Empieza la partida siguiente, con la semilla que le toca (`next_seed`)."""
        self.game += 1
        options = self.options
        self.start(
            next_seed(
                options.seed, self.game, demo=options.demo, fixed=options.seed_fixed
            )
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        # En la demo no se lee la entrada: ni controles ni reinicio.
        if self.gamepads is None:
            return
        self.gamepads.handle_event(event)
        # Solo con el texto ya a la vista: R o X a mitad de partida, o justo al morir,
        # no hacen nada. Así nadie se salta el tiempo que duró sin verlo.
        if self.dead_steps >= EFFECT_STEPS and is_restart(event):
            self.restart()

    def step(self) -> None:
        """Avanza `world` un paso con la intención de este momento, o cuenta la muerte.

        La música avanza en todos los pasos, también con el jugador muerto.
        """
        if not self.world.game_over:
            # R1 (ADR 0026): una partida nueva espera el compás de la música, para que
            # cada drop caiga en el golpe. Sin música, no espera.
            if self.music is None or not self.music.waiting_for_bar:
                self.world.update(self.intent())
                self.log_section()
        else:
            self.dead_steps += 1
            if self.demo is not None and self.dead_steps >= DEMO_RESTART_STEPS:
                self.restart()
        if self.music is not None:
            self.music.step(self.world)

    def play_music(self) -> None:
        """Pasa al canal de audio los bloques que el secuenciador dejó listos."""
        if self.music is not None and self.music_player is not None:
            self.music_player.update(self.music.ready)

    def intent(self) -> Vector2:
        if self.demo is not None:
            return pilot_intent(self.world.steps) if self.demo.pilot else Vector2()
        assert self.gamepads is not None
        deadzone = self.settings.controls.stick_deadzone
        return combine(keys_intent(), *self.gamepads.intents(deadzone))

    def viewport(self, screen: pygame.Surface) -> Viewport:
        """La cámara de este frame: el jugador, más el desplazamiento, va al centro."""
        camera = self.settings.camera
        center = camera_center(self.world.player.position, camera.offset)
        return Viewport(screen.get_size(), camera.fov, center)

    def draw(self, screen: pygame.Surface) -> None:
        viewport = self.viewport(screen)
        draw_letterbox(screen, viewport, self.palette)
        # Lo que cruza el borde del área útil, como un eje grueso o un círculo, no se
        # dibuja sobre las franjas.
        screen.set_clip(viewport.rect)
        draw_axes(screen, viewport, self.palette)
        draw_world(
            screen,
            self.world,
            viewport,
            self.palette,
            self.settings.debug.show_hitboxes,
        )
        if self.world.game_over:
            player = self.world.player
            self.death_screen.draw(
                screen,
                viewport,
                (player.position, player.radius),
                self.dead_steps,
                self.seed,
                self.world.elapsed,
                # En la demo la entrada no se lee: la ayuda para reiniciar mentiría.
                show_hint=self.demo is None,
            )
        screen.set_clip(None)
