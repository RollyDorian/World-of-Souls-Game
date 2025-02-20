import pygame
import os
import sys
import math
import random
import pygame_gui

all_sprites = pygame.sprite.Group()
player_group = pygame.sprite.Group()
tiles_group = pygame.sprite.Group()
enemy_group = pygame.sprite.Group()
attacks_group = pygame.sprite.Group()
effects_group = pygame.sprite.Group()
pygame.init()
pygame.display.set_caption('World of Souls')
size = width, height = 1300, 800
screen = pygame.display.set_mode(size)
FPS = 60
manager = pygame_gui.UIManager((width, height))


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    # если файл не существует, то выходим
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(all_sprites, player_group)
        self.frames = {}
        self.cur_frame = 0
        self.cut_sheet(load_image('player_standing.png'), 2, 1, 'standing')
        self.cut_sheet(load_image('player_running.png'), 2, 1, 'running')
        self.cut_sheet(load_image('player_flying.png'), 2, 1, 'flying_r')
        flying_l = load_image('player_flying.png')
        flying_l = pygame.transform.flip(flying_l, True, False)
        self.cut_sheet(flying_l, 2, 1, 'flying_l')
        self.image = self.frames['standing'][self.cur_frame]
        self.ticks_counter = 0
        self.rect.centerx = screen.width // 2
        self.rect.centery = screen.height // 2
        self.mask = pygame.mask.from_surface(self.image)

        self.health = 10
        self.max_health = 10
        self.regen_speed = 0.1
        self.speed = 8
        self.exp = 0

    def update(self, dx, dy, infinity_world):
        self.ticks_counter += 1
        anim_type = 'standing'
        if abs(dx) + abs(dy) == 0:
            anim_type = 'standing'
            self.image = self.frames[anim_type][self.cur_frame]
        elif dx > 0:
            anim_type = 'flying_r'
            self.image = self.frames[anim_type][self.cur_frame]
        elif dx < 0:
            anim_type = 'flying_l'
            self.image = self.frames[anim_type][self.cur_frame]
        elif dx == 0 and dy != 0:
            anim_type = 'running'
            self.image = self.frames[anim_type][self.cur_frame]
        if anim_type != 'standing':
            if self.ticks_counter % 20 == 0:
                self.cur_frame = (self.cur_frame + 1) % len(self.frames[anim_type])
                self.image = self.frames[anim_type][self.cur_frame]
                self.ticks_counter = 0
        else:
            if self.cur_frame == 0 and self.ticks_counter == 60:
                self.cur_frame = (self.cur_frame + 1) % len(self.frames[anim_type])
                self.image = self.frames[anim_type][self.cur_frame]
                self.ticks_counter = 0
            elif self.cur_frame and self.ticks_counter == 10:
                self.cur_frame = (self.cur_frame + 1) % len(self.frames[anim_type])
                self.image = self.frames[anim_type][self.cur_frame]

        if abs(dx) + abs(dy) == 2:
            dx *= 0.7071
            dy *= 0.7071

        for sprite in all_sprites:
            if sprite != self and isinstance(sprite, (
                    Enemy, ExplosionByEnemy, ExplosionByMagicShot, ExplosionByFireball, HeavenStrike)):
                sprite.rect.x -= dx * self.speed
                sprite.rect.y -= dy * self.speed
        for sprite in attacks_group:
            if sprite != self and isinstance(sprite, (MagicShot, Fireball)):
                sprite.pos -= pygame.math.Vector2(dx, dy) * self.speed

        targ_tile = min(tiles_group, key=lambda tile: (tile.rect.x, tile.rect.y))
        infinity_world.tiles_arr.remove(targ_tile)
        targ_tile.rect.x -= dx * self.speed
        targ_tile.rect.y -= dy * self.speed
        infinity_world.tiles_arr.insert(0, targ_tile)
        for y in range(infinity_world.tiles_y):
            for x in range(infinity_world.tiles_x):
                if x + y == 0: continue
                infinity_world.tiles_arr[
                    y * infinity_world.tiles_x + x].rect.x = targ_tile.rect.x + x * infinity_world.tile_size
                infinity_world.tiles_arr[
                    y * infinity_world.tiles_x + x].rect.y = targ_tile.rect.y + y * infinity_world.tile_size

        if self.health < self.max_health:
            self.health += 1 / FPS * self.regen_speed
            self.health = self.max_health if self.health > self.max_health else self.health

    def cut_sheet(self, sheet, columns, rows, type):
        self.frames[type] = []
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames[type].append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))


class Enemy(pygame.sprite.Sprite):
    def __init__(self, player, columns, rows, coords):
        super().__init__(all_sprites, enemy_group)
        x, y = coords
        self.frames = []
        self.cut_sheet(load_image('enemy1.png'), columns, rows)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x, y)
        self.player = player
        self.mask = pygame.mask.from_surface(self.image)
        self.velocity = pygame.math.Vector2(0, 0)
        self.max_speed = 2.5
        self.acceleration = pygame.math.Vector2(0, 0)
        self.separation_radius = 40
        self.ticks_counter = 0
        self.health = 3

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def update(self):
        self.ticks_counter += 1
        if self.ticks_counter % 8 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]

        target_vec = pygame.math.Vector2(self.player.rect.center)
        current_vec = pygame.math.Vector2(self.rect.center)
        desired_vec = target_vec - current_vec
        if desired_vec.magnitude() == 0:
            desired_vec += (1, 1)

        desired_dir = desired_vec.normalize() * self.max_speed
        self.acceleration = desired_dir - self.velocity
        self.velocity += self.acceleration * 0.15

        self.apply_separation()
        self.rect.center += self.velocity

        if pygame.sprite.collide_mask(self, self.player):
            self.player.health -= 0.5 * (1 / FPS)
            diff = pygame.math.Vector2(self.rect.center) - self.player.rect.center
            if diff.magnitude() == 0:
                diff += (1, 1)
            self.velocity += diff.normalize() * 0.3
        if self.health <= 0:
            ExplosionByEnemy(self)
            self.kill()

    def apply_separation(self):
        separation_force = pygame.math.Vector2(0, 0)
        neighbors = pygame.sprite.spritecollide(
            self, enemy_group, False,
            lambda a, b: a != b and a.rect.colliderect(b.rect)
        )

        for neighbor in neighbors:
            diff = pygame.math.Vector2(self.rect.center) - neighbor.rect.center
            distance = diff.magnitude()
            if 0 < distance < self.separation_radius:
                strength = (1 - distance / self.separation_radius) * 1.2
                separation_force += diff.normalize() * strength
        self.velocity += separation_force


class ExplosionByEnemy(pygame.sprite.Sprite):
    def __init__(self, enemy):
        super().__init__(all_sprites, effects_group)
        self.frames = []
        self.cut_sheet(load_image('explosions.png'), 11, 15)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect.center = enemy.rect.center
        self.ticks_counter = 0

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                if j == 0:
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    image = sheet.subsurface(pygame.Rect(frame_location, self.rect.size))
                    self.frames.append(image)

    def update(self):
        self.ticks_counter += 1
        if self.ticks_counter % 4 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]
        if self.ticks_counter == 11 * 4:
            self.kill()


class Fireball(pygame.sprite.Sprite):
    def __init__(self, start_pos, direction, damage):
        super().__init__(all_sprites, attacks_group)
        self.speed = 8
        self.frames = []
        self.direction = pygame.math.Vector2(direction).normalize()
        self.cut_sheet(load_image('Fireball.png'), 1, 3)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.damage = damage
        self.ticks_counter = 0
        self.rect.center = start_pos
        self.mask = pygame.mask.from_surface(self.image)
        self.pos = pygame.Vector2(self.rect.center)

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
                frame_location = (self.rect.w * i, self.rect.h * j)
                image = sheet.subsurface(pygame.Rect(frame_location, self.rect.size))
                image = pygame.transform.rotate(image, angle)
                self.frames.append(image)

    def update(self):
        self.ticks_counter += 1
        if self.ticks_counter % 5 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]

        self.pos += self.direction * self.speed
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        if not (-100 < self.pos.x < width + 100 and -100 < self.pos.y < height + 100):
            self.kill()

        for enemy in enemy_group:
            if pygame.sprite.collide_mask(self, enemy):
                enemy.health -= self.damage
                self.rect.center += self.direction * 50
                ExplosionByFireball(self, self.damage)
                self.kill()


class ExplosionByFireball(pygame.sprite.Sprite):
    def __init__(self, shot, damage):
        super().__init__(all_sprites, effects_group)
        self.frames = []
        self.cut_sheet(load_image('fire_expl.png'), 10, 9)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect.center = shot.rect.center
        self.ticks_counter = 0
        self.damage = damage

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                if j == 0:
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    image = sheet.subsurface(pygame.Rect(frame_location, self.rect.size))
                    self.frames.append(image)

    def update(self):
        self.ticks_counter += 1
        if self.ticks_counter % 4 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]
        for enemy in enemy_group:
            if pygame.sprite.collide_mask(self, enemy):
                enemy.health -= self.damage
        if self.ticks_counter == 10 * 4:
            self.kill()


class MagicShot(pygame.sprite.Sprite):
    def __init__(self, start_pos, direction, damage):
        super().__init__(all_sprites, attacks_group)
        self.speed = 15
        self.frames = []
        self.direction = pygame.math.Vector2(direction).normalize()
        self.cut_sheet(load_image('magic_shot.png'), 14, 9)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.damage = damage
        self.ticks_counter = 0
        self.rect.center = start_pos
        self.mask = pygame.mask.from_surface(self.image)
        self.pos = pygame.Vector2(self.rect.center)

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                if j == 2:
                    angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    image = sheet.subsurface(pygame.Rect(frame_location, self.rect.size))
                    image = pygame.transform.rotate(image, angle)
                    self.frames.append(image)

    def update(self):
        self.ticks_counter += 1
        if self.ticks_counter % 3 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]

        self.pos += self.direction * self.speed
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        if not (-100 < self.pos.x < width + 100 and -100 < self.pos.y < height + 100):
            self.kill()

        for enemy in enemy_group:
            if pygame.sprite.collide_mask(self, enemy):
                enemy.health -= self.damage
                self.rect.center += self.direction * 30
                ExplosionByMagicShot(self)
                self.kill()


class ExplosionByMagicShot(pygame.sprite.Sprite):
    def __init__(self, shot):
        super().__init__(all_sprites, effects_group)
        self.frames = []
        self.cut_sheet(load_image('ms_expl.png'), 14, 9)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect.center = shot.rect.center
        self.ticks_counter = 0

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                if j == 2:
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    image = sheet.subsurface(pygame.Rect(frame_location, self.rect.size))
                    self.frames.append(image)

    def update(self):
        self.ticks_counter += 1
        if self.ticks_counter % 2 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]
        if self.ticks_counter == 14 * 2:
            self.kill()


class HeavenStrike(pygame.sprite.Sprite):
    def __init__(self, pos, damage):
        super().__init__(all_sprites, attacks_group)
        self.frames = []
        self.cut_sheet(load_image('HeavenStrike.png'), 6, 2)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.damage = damage
        self.ticks_counter = 0
        self.rect.center = pos
        self.rect.y -= 25
        self.mask = pygame.mask.from_surface(self.image)

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                image = sheet.subsurface(pygame.Rect(frame_location, self.rect.size))
                self.frames.append(image)

    def update(self):
        self.ticks_counter += 1
        if self.ticks_counter % 5 == 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]
            if self.cur_frame == 0:
                self.kill()

        for enemy in enemy_group:
            if pygame.sprite.collide_mask(self, enemy):
                enemy.health -= self.damage


class AttackSystem:
    def __init__(self, player, enemy_group):
        self.player = player
        self.enemy_group = enemy_group
        self.attacks = {
            'magic_shot': {
                'level': 1,
                'cooldown': 1.2,
                'damage': 10,
                'shots_count': 1,
                'timer': 0.0,
                'action': self.create_ms
            },
            'Fireball': {
                'level': 1,
                'cooldown': 2,
                'damage': 20,
                'shots_count': 1,
                'timer': 0.0,
                'action': self.create_fb
            },
            'HeavenStrike': {
                'level': 1,
                'cooldown': 3,
                'damage': 15,
                'shots_count': 1,
                'timer': 0.0,
                'action': self.create_hs
            }
        }

    def update(self, dt):
        for attack in self.attacks.values():
            attack['timer'] += dt
            if attack['timer'] >= attack['cooldown'] * (0.9 ** attack['level']):
                for _ in range(attack['shots_count']):
                    attack['action']()
                attack['timer'] = 0

    def create_ms(self):
        if enemy_group:
            nearest_enemy = min(self.enemy_group,
                                key=lambda enemy: pygame.math.Vector2(self.player.rect.center).distance_to(
                                    enemy.rect.center))
            direction = pygame.math.Vector2(nearest_enemy.rect.center) - self.player.rect.center
            if direction.magnitude() == 0:
                direction += (1, 1)
            MagicShot(self.player.rect.center, direction, self.attacks['magic_shot']['damage'])

    def create_fb(self):
        if enemy_group:
            nearest_enemy = min(self.enemy_group,
                                key=lambda enemy: pygame.math.Vector2(self.player.rect.center).distance_to(
                                    enemy.rect.center))
            direction = pygame.math.Vector2(nearest_enemy.rect.center) - self.player.rect.center
            if direction.magnitude() == 0:
                direction += (1, 1)
            Fireball(self.player.rect.center, direction, self.attacks['Fireball']['damage'])

    def create_hs(self):
        if enemy_group:
            enemy_arr = sorted([e for e in self.enemy_group if
                                pygame.math.Vector2(self.player.rect.center).distance_to(e.rect.center) < height // 2 - 50],
                               key=lambda enemy: pygame.math.Vector2(self.player.rect.center).distance_to(
                                   enemy.rect.center))
            if enemy_arr:
                targ_enemy = random.choice(enemy_arr)
                HeavenStrike(targ_enemy.rect.center, self.attacks['HeavenStrike']['damage'])


def draw_health_bar(screen, player):
    bar_width = 50
    bar_height = 2
    fill = (player.health / player.max_health) * bar_width
    pygame.draw.rect(screen, (200, 0, 0), (player.rect.x + 5, player.rect.y - 20, bar_width, bar_height))
    pygame.draw.rect(screen, (0, 150, 0), (player.rect.x + 5, player.rect.y - 20, fill, bar_height))


class Tile(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(tiles_group, all_sprites)
        self.image = load_image('SandTile.png')
        self.rect = self.image.get_rect()


class InfinityWorld:
    def __init__(self, tile_size=128, buffer=2):
        self.tile_size = tile_size
        self.buffer = buffer

        self.tiles_x = width // tile_size + 2 * buffer
        self.tiles_y = height // tile_size + 2 * buffer
        self.tiles_arr = []

        for y in range(-buffer, self.tiles_y - buffer):
            for x in range(-buffer, self.tiles_x - buffer):
                tile = Tile()
                tile.rect.x = x * tile_size
                tile.rect.y = y * tile_size
                self.tiles_arr.append(tile)

        self.left_bound = -self.tile_size * buffer
        self.right_bound = self.tiles_x * tile_size
        self.top_bound = -self.tile_size * buffer
        self.bottom_bound = self.tiles_y * tile_size

    def update_tiles(self):
        for tile in tiles_group:
            if tile.rect.x < self.left_bound:
                tile.rect.x = (self.tiles_x + self.buffer) * self.tile_size
            elif tile.rect.x + self.tile_size * self.buffer > self.right_bound:
                tile.rect.x = -self.buffer * self.tile_size

            if tile.rect.y < self.top_bound:
                tile.rect.y += (self.tiles_y + self.buffer) * self.tile_size
            elif tile.rect.y + self.tile_size * self.buffer > self.bottom_bound:
                tile.rect.y = -self.buffer * self.tile_size


def get_random_pos_enemy():
    # рандомная точка окружности, смещенной в центр экрана
    r = width ** 2 + height ** 2
    r = r ** 0.5 // 2
    x = random.randint(width // 2 - int(r), width // 2 + int(r))
    # значение функции на окружности при рандомном x
    y = height // 2 + random.choice([-1, 1]) * (r ** 2 - (x - width // 2) ** 2) ** 0.5
    return x, y


clock = pygame.time.Clock()
running = True
player = Player()
infinity_world = InfinityWorld()
enemy_spawn_rate = 2
enemy_spawn_count = 500
ticks_counter = 0
enemy_ticks_counter = 0
starting_time = pygame.time.get_ticks()
enemies_arr = []
CELL_SIZE = 256
attack_system = AttackSystem(player, enemy_group)
while running:
    time_delta = clock.tick(60) / 1000.0
    enemy_ticks_counter += 1
    current_time = pygame.time.get_ticks()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            pass
        manager.process_events(event)

    keys = pygame.key.get_pressed()
    dx = keys[pygame.K_d] - keys[pygame.K_a]
    dy = keys[pygame.K_s] - keys[pygame.K_w]

    manager.update(time_delta)
    player.update(dx, dy, infinity_world)
    infinity_world.update_tiles()

    spatial_grid = {}
    for enemy in enemy_group:
        cell = (enemy.rect.x // CELL_SIZE, enemy.rect.y // CELL_SIZE)
        if cell not in spatial_grid:
            spatial_grid[cell] = []
        spatial_grid[cell].append(enemy)
    for enemy in enemy_group:
        enemy.update()
    hits = pygame.sprite.groupcollide(enemy_group, attacks_group, False, False)
    for enemy in hits:
        player.exp += 10

    for enemy in pygame.sprite.groupcollide(enemy_group, player_group, False, False):
        enemy.health -= 0.05
    effects_group.update()

    next_enemy = FPS // enemy_spawn_rate
    if enemy_spawn_count:
        if enemy_ticks_counter == next_enemy:
            enemy_ticks_counter = 0
            enemy_spawn_count -= 1
            enemies_arr.append(Enemy(player, 2, 1, get_random_pos_enemy()))
            enemy_spawn_rate += 0.01
    attack_system.update(1 / FPS)
    for attack in attacks_group:
        attack.update()

    screen.fill((0, 0, 0))
    tiles_group.draw(screen)
    enemy_group.draw(screen)
    player_group.draw(screen)
    attacks_group.draw(screen)
    effects_group.draw(screen)
    draw_health_bar(screen, player)
    manager.draw_ui(screen)

    pygame.display.flip()
pygame.quit()
