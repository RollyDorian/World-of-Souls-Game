import pygame
import os
import sys
import math
import random
import pygame_gui
import json

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
manager.preload_fonts([{'name': 'noto_sans', 'point_size': 18, 'style': 'regular', 'antialiased': True}])
clock = pygame.time.Clock()


def clear_sprites():
    for sprite in all_sprites:
        sprite.kill()


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

        self.health = 5
        self.max_health = 5
        self.regen_speed = 0.1
        self.speed = 8
        self.exp = 0
        self.total_exp = 0
        self.next_level_exp = 50
        self.level = 1
        self.total_time = 0

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
            self.player.health -= 2 * (1 / FPS)
            diff = pygame.math.Vector2(self.rect.center) - self.player.rect.center
            if diff.magnitude() == 0:
                diff += (1, 1)
            self.velocity += diff.normalize() * 0.3
        if self.health <= 0:
            ExplosionByEnemy(self)
            self.player.exp += 10
            self.player.total_exp += 10
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
                'shots_done': 0,
                'cd_beetween_shots': 0.2,
                'timer': 0.0,
                'timer2': 0.0,
                'action': self.create_ms
            },
            'Fireball': {
                'level': 0,
                'cooldown': 2,
                'damage': 20,
                'shots_count': 1,
                'shots_done': 0,
                'cd_beetween_shots': 0.3,
                'timer': 0.0,
                'timer2': 0.0,
                'action': self.create_fb
            },
            'HeavenStrike': {
                'level': 0,
                'cooldown': 3,
                'damage': 15,
                'shots_count': 1,
                'shots_done': 0,
                'cd_beetween_shots': 0.2,
                'timer': 0.0,
                'timer2': 0.0,
                'action': self.create_hs
            }
        }

    def update(self, dt):
        for attack in self.attacks.values():
            if attack['level'] == 0:
                continue
            attack['timer'] += dt
            if attack['timer'] >= attack['cooldown'] * (0.9 ** attack['level']):
                attack['timer2'] += dt
                if attack['timer2'] >= attack['cd_beetween_shots']:
                    attack['action']()
                    attack['timer2'] = 0
                    attack['shots_done'] += 1
                if attack['shots_done'] == attack['shots_count']:
                    attack['timer'] = 0
                    attack['shots_done'] = 0

    def level_up(self):
        self.player.exp = 0
        self.player.level += 1
        self.player.next_level_exp = int(self.player.next_level_exp * 1.5) // 10 * 10
        improvments_arr = ['Level up Magic Shot', 'Level up Fireball', 'Level up Heaven Strike', 'Increase HP',
                           'Increase Regeneration speed', 'Increase Speed']
        random.shuffle(improvments_arr)
        improvments_arr = improvments_arr[:3]
        lvlup_btn1 = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((width // 2 - 150, 200), (300, 80)),
                                                  text=improvments_arr[0],
                                                  manager=manager)
        lvlup_btn2 = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((width // 2 - 150, 345), (300, 80)),
                                                  text=improvments_arr[1],
                                                  manager=manager)
        lvlup_btn3 = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((width // 2 - 150, 490), (300, 80)),
                                                  text=improvments_arr[2],
                                                  manager=manager)
        return lvlup_btn1, lvlup_btn2, lvlup_btn3

    def improve(self, improvement):
        attack = 0
        if improvement == 'Level up Magic Shot':
            attack = self.attacks['magic_shot']
        elif improvement == 'Level up Fireball':
            attack = self.attacks['Fireball']
        elif improvement == 'Level up Heaven Strike':
            attack = self.attacks['HeavenStrike']
        elif improvement == 'Increase HP':
            self.player.max_health *= 1.05
            self.player.health *= 1.05
        elif improvement == 'Increase Regeneration speed':
            self.player.regen_speed *= 1.1
        if attack:
            attack['level'] += 1
            if attack['level'] % 3 == 0:
                attack['shots_count'] += 1

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
                                pygame.math.Vector2(self.player.rect.center).distance_to(
                                    e.rect.center) < height // 2 - 50],
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


def draw_exp_bar(screen, player):
    bar_width = 300
    bar_height = 5
    fill = (player.exp / player.next_level_exp) * bar_width
    pygame.draw.rect(screen, pygame.Color('white'), (40, 20, bar_width, bar_height))
    pygame.draw.rect(screen, pygame.Color(3, 223, 252), (40, 20, fill, bar_height))


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


def terminate():
    pygame.quit()
    sys.exit()


if not os.path.exists('results.json'):
    with open('results.json', "w", encoding="utf-8") as file:
        json.dump({'results': [], 'gold': 0, 'total_exp': 0}, file, ensure_ascii=False, indent=4)


def save(player):
    level = player.level
    exp = player.total_exp
    time = player.total_time
    minutes = int(time // 60)
    sec = int(time % 60)
    time = f'{minutes}:{sec:02}'
    res = f'Уровень: {level} | Опыт: {exp} | Время: {time}'
    with open('results.json', "r", encoding="utf-8") as file:
        data = json.load(file)
    data['results'].append(res)
    data['total_exp'] += exp
    data['gold'] = int(data['total_exp'] // 100)
    with open('results.json', "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_data(filename):
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as file:
            json.dump({'results': []}, file, ensure_ascii=False, indent=4)
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


message = pygame_gui.elements.UITextBox(
    relative_rect=pygame.Rect((width // 2 - 100, height // 2 - 100), (200, 200)),
    html_text="<font face=\"fira_code\" size=5 color=\"#FF0000\">Недостаточно душ</font><br>",
    manager=manager)
continue_btn = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((width // 2 - 90, height // 2 + 65), (180, 25)),
    text='Продолжить',
    manager=manager)
message.hide()
continue_btn.hide()


def main_menu():
    gold_counter = pygame_gui.elements.UITextBox(
        html_text=f"<font size=3 color=#FFFFFF>Души: {load_data('results.json')['gold']:02}</font>",
        relative_rect=pygame.Rect((width // 2 - 365, height - 55), (75, 30)),
        manager=manager)
    play_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((width // 2 - 100, height - 65), (200, 50)),
        text='Играть',
        manager=manager)
    settings_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((width // 2 - 275, height - 60), (150, 40)),
        text='Настройки',
        manager=manager)
    records_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((width // 2 + 125, height - 60), (150, 40)),
        text='Рекорды',
        manager=manager)
    music_text = pygame_gui.elements.UITextBox(
        relative_rect=pygame.Rect((width // 2 - 115, height // 2 - 50), (230, 300)),
        html_text="<font face=\"fira_code\" size=5 color=\"#FFFFFF\">Громкость музыки</font><br>",
        manager=manager)
    slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((width // 2 - 100, height // 2), (200, 25)),
        start_value=0,
        value_range=(0, 100),
        manager=manager)
    back_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((width // 2 - 100, height // 2 + 200), (75, 25)),
        text='Назад',
        manager=manager)
    title = pygame_gui.elements.UITextBox(
        html_text="<font size=5 color=#FFFFFF>История игр</font>",
        relative_rect=pygame.Rect((width // 2 - 200, 30), (400, 50)),
        manager=manager)
    back_button2 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((width // 3, height - 80), (width // 3, 50)),
        text="Назад",
        manager=manager)
    results = load_data('results.json')['results']
    results.reverse()
    record_list = pygame_gui.elements.UISelectionList(
        relative_rect=pygame.Rect((width // 2 - 200, 70), (400, 300)),
        item_list=results,
        manager=manager)
    record_list.hide()
    record_menu = [title, back_button2, record_list]
    for x in record_menu:
        x.hide()
    slider.hide()
    music_text.hide()
    back_button.hide()
    main_btns = [play_button, settings_button, records_button, gold_counter]
    blackout = pygame.Surface((width, height), pygame.SRCALPHA)
    blackout.fill((0, 0, 0, 0))
    pygame.draw.rect(blackout, (0, 0, 0, 100), blackout.get_rect())
    running = True
    is_settings = False
    is_records = False

    while running:
        time_delta = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN:
                if pygame.K_ESCAPE:
                    if is_settings:
                        slider.hide()
                        music_text.hide()
                        back_button.hide()
                        is_settings = False
                        for btn in main_btns:
                            btn.show()
                    elif is_records:
                        for btn in record_menu:
                            btn.hide()
                        for btn in main_btns:
                            btn.show()
                        is_records = False
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == play_button:
                    for btn in main_btns:
                        btn.hide()
                    start_game()
                    gold_counter = pygame_gui.elements.UITextBox(
                        html_text=f"<font size=3 color=#FFFFFF>Души: {load_data('results.json')['gold']:02}</font>",
                        relative_rect=pygame.Rect((width // 2 - 365, height - 55), (75, 30)),
                        manager=manager)
                    main_btns = main_btns[:4]
                    main_btns.append(gold_counter)
                    for btn in main_btns:
                        btn.show()
                elif event.ui_element == settings_button:
                    for btn in main_btns:
                        btn.hide()
                    music_text.show()
                    slider.show()
                    back_button.show()
                    is_settings = True
                elif event.ui_element == back_button:
                    slider.hide()
                    music_text.hide()
                    back_button.hide()
                    is_settings = False
                    for btn in main_btns:
                        btn.show()
                elif event.ui_element == records_button:
                    for btn in main_btns:
                        btn.hide()
                    results = load_data('results.json')['results']
                    results.reverse()
                    record_list = pygame_gui.elements.UISelectionList(
                        relative_rect=pygame.Rect((width // 2 - 200, 70), (400, 300)),
                        item_list=results,
                        manager=manager)
                    record_list.hide()
                    record_menu = record_menu[:2]
                    record_menu.append(record_list)
                    for btn in record_menu:
                        btn.show()
                    is_records = True
                elif event.ui_element == back_button2:
                    for btn in record_menu:
                        btn.hide()
                    for btn in main_btns:
                        btn.show()
                    is_records = False
                elif event.ui_element == continue_btn:
                    message.hide()
                    continue_btn.hide()

            manager.process_events(event)
        manager.update(time_delta)
        screen.blit(mm_background, (0, 0))
        manager.draw_ui(screen)
        if is_settings or is_records:
            screen.blit(blackout)

        pygame.display.flip()


def start_game():
    is_paused = False
    infinity_world = InfinityWorld()
    player = Player()
    attack_system = AttackSystem(player, enemy_group)
    enemies_arr = []
    enemy_spawn_rate = 2
    enemy_spawn_count = 500
    enemy_ticks_counter = 0
    lvlup_btns = []
    red_warning = pygame.Surface((width, height), pygame.SRCALPHA)
    red_warning.fill((0, 0, 0, 0))
    pygame.draw.rect(red_warning, (150, 0, 0, 50), red_warning.get_rect())
    blackout = pygame.Surface((width, height), pygame.SRCALPHA)
    blackout.fill((0, 0, 0, 0))
    pygame.draw.rect(blackout, (0, 0, 0, 100), blackout.get_rect())
    running = True
    quit_button, revive_button, text = 0, 0, 0
    timer = 0
    while running:
        time_delta = clock.tick(60) / 1000.0
        enemy_ticks_counter += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN:
                pass
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element in lvlup_btns:
                    improvement = event.ui_element.text
                    attack_system.improve(improvement)
                    for btn in lvlup_btns:
                        btn.kill()
                    is_paused = False
                elif event.ui_element == quit_button:
                    running = False
                    quit_button.kill()
                    revive_button.kill()
                    text.kill()
                    player.total_time = timer
                    save(player)
                    clear_sprites()
                    continue
                elif event.ui_element == revive_button:
                    quit_button.kill()
                    revive_button.kill()
                    text.kill()
                    if gold >= 10:
                        player.health = player.max_health
                        is_paused = False
                    else:
                        running = False
                        player.total_time = timer
                        save(player)
                        clear_sprites()
                        message.show()
                        continue_btn.show()
                        continue

            manager.process_events(event)

        keys = pygame.key.get_pressed()
        if is_paused:
            manager.update(time_delta)

            screen.fill((0, 0, 0))
            tiles_group.draw(screen)
            enemy_group.draw(screen)
            player_group.draw(screen)
            attacks_group.draw(screen)
            effects_group.draw(screen)
            draw_health_bar(screen, player)
            screen.blit(blackout)
            manager.draw_ui(screen)

            pygame.display.flip()
            continue
        dx = keys[pygame.K_d] - keys[pygame.K_a]
        dy = keys[pygame.K_s] - keys[pygame.K_w]

        manager.update(time_delta)
        player.update(dx, dy, infinity_world)
        infinity_world.update_tiles()
        enemy_group.update()
        '''for enemy in pygame.sprite.groupcollide(enemy_group, player_group, False, False):
            enemy.health -= 0.05'''  # DISABLED
        effects_group.update()

        next_enemy = FPS // enemy_spawn_rate
        if enemy_spawn_count:
            if enemy_ticks_counter >= next_enemy:
                enemy_ticks_counter = 0
                enemy_spawn_count -= 0
                enemies_arr.append(Enemy(player, 2, 1, get_random_pos_enemy()))
                enemy_spawn_rate += 0.01
        attack_system.update(1 / FPS)
        attacks_group.update()

        screen.fill((0, 0, 0))
        tiles_group.draw(screen)
        enemy_group.draw(screen)
        player_group.draw(screen)
        attacks_group.draw(screen)
        effects_group.draw(screen)
        draw_health_bar(screen, player)
        draw_exp_bar(screen, player)
        if player.health / player.max_health <= 0.3:
            screen.blit(red_warning)
        manager.draw_ui(screen)
        if player.health <= 0:
            is_paused = True
            gold = load_data('results.json')['gold']
            text = pygame_gui.elements.UITextBox(
                relative_rect=pygame.Rect((width // 2 - 115, 200), (230, 300)),
                html_text=(
                    "<font face=\"fira_code\" size=5 color=\"#FF0000\">Вы на грани!</font><br>"
                    "<font face=\"fira_code\" size=3 color=\"#FFFFFF\">Жизнь или смерть?</font>"
                ), manager=manager)
            revive_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((width // 2 - 100, height // 2 - 65), (200, 50)),
                text='Возрождение (cost: 10 Душ)',
                manager=manager)
            quit_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((width // 2 - 100, height // 2 + 5), (200, 50)),
                text='Выход',
                manager=manager)
            continue
        if player.exp >= player.next_level_exp:
            lvlup_btns = attack_system.level_up()
            is_paused = True
            with open('results.json', "r", encoding="utf-8") as file:
                data = json.load(file)
                data['gold'] -= 10
                data['total_exp'] -= 1000
            with open('results.json', "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

        pygame.display.flip()
        timer += 1 / FPS


mm_background = load_image('MainMenu.png')
CELL_SIZE = 256
main_menu()
