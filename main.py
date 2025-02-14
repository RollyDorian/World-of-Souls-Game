import pygame
import os
import sys

all_sprites = pygame.sprite.Group()
player_group = pygame.sprite.Group()
tiles_group = pygame.sprite.Group()
enemy_group = pygame.sprite.Group()
attacks_group = pygame.sprite.Group()
pygame.init()
size = width, height = 1300, 800
screen = pygame.display.set_mode(size)
FPS = 60


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
        self.image = load_image('player.png')
        self.rect = self.image.get_rect()
        self.rect.centerx = screen.width // 2
        self.rect.centery = screen.height // 2
        self.frame_number = 0
        self.animation_type = {'standing': 1, 'running_right': 1, 'running_left': 1, 'dying': 3}
        self.abs_coords = [0, 0]

        self.health = 10
        self.max_health = 10
        self.regen_speed = 0.2
        self.speed = 15
        self.exp = 0
        self.skills = {'magic shot': {'level': 1, 'reload': 2}, 'fireball': {'level': 0, 'reload': 5}}

    def update(self, dx, dy):
        if abs(dx) + abs(dy) == 2:
            dx *= 0.7071
            dy *= 0.7071

        for sprite in all_sprites:
            if sprite != self and isinstance(sprite, (Tile, Enemy)):
                sprite.rect.x -= dx * self.speed
                sprite.rect.y -= dy * self.speed

        if self.health < self.max_health:
            self.health += 1 / FPS * self.regen_speed
            self.health = self.max_health if self.health > self.max_health else self.health

        for skill in self.skills:
            pass
            '''skill.use()'''


class Enemy(pygame.sprite.Sprite):
    def __init__(self, player):
        super().__init__(all_sprites, enemy_group)
        self.image = load_image('enemy.png')
        self.rect = self.image.get_rect()
        self.speed = 2
        self.player = player

    def update(self):
        dx = self.player.rect.x - self.rect.x
        dy = self.player.rect.y - self.rect.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        if distance != 0:
            self.rect.x += (dx / distance) * self.speed / FPS
            self.rect.y += (dy / distance) * self.speed / FPS


class MagicShot(pygame.sprite.Sprite):
    def __init__(self, start_pos, direction):
        super().__init__(all_sprites, attacks_group)
        self.image = load_image('magic_shot.png')
        self.rect = self.image.get_rect(center=start_pos)
        self.speed = 8
        self.direction = direction  # нормализованный вектор (dx, dy)

    def update(self):
        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed
        # Удалить, если выходит за экран
        if not screen.get_rect().colliderect(self.rect):
            self.kill()


def level_up_skill(self, skill_name):
    if self.exp >= 100:
        self.skills[skill_name]['level'] += 1
        self.skills[skill_name]['reload'] *= 0.9  # уменьшение перезарядки
        self.exp -= 100


def draw_health_bar(screen, player):
    bar_width = 200
    bar_height = 20
    fill = (player.health / player.max_health) * bar_width
    pygame.draw.rect(screen, (255, 0, 0), (10, 10, bar_width, bar_height))
    pygame.draw.rect(screen, (0, 255, 0), (10, 10, fill, bar_height))


class Tile(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(tiles_group, all_sprites)
        self.image = load_image('SandTile.png')
        self.rect = self.image.get_rect()


class InfinityWorld:
    def __init__(self, tile_size=128, render_distance=9):
        self.tile_size = tile_size  # размер тайла в пикселях
        self.render_distance = render_distance  # расстояние в тайлах от игрока

        num_tiles_x = width // tile_size + 4
        num_tiles_y = height // tile_size + 4

        for x in range(-2, num_tiles_x):
            for y in range(-2, num_tiles_y):
                tile = Tile()
                tile.rect.x = x * tile_size
                tile.rect.y = y * tile_size

    def update_tiles(self):
        # Границы экрана с учетом размера тайла и запаса
        left_bound = -self.tile_size * 2
        right_bound = width + self.tile_size * 2
        top_bound = -self.tile_size * 2
        bottom_bound = height + self.tile_size * 2

        for tile in tiles_group:
            # Перемещение по оси X
            if tile.rect.x < left_bound:
                tile.rect.x += (width + self.tile_size * 2)
            elif tile.rect.x > right_bound:
                tile.rect.x -= (width + self.tile_size * 2)

            # Перемещение по оси Y
            if tile.rect.y < top_bound:
                tile.rect.y += (height + self.tile_size * 2)
            elif tile.rect.y > bottom_bound:
                tile.rect.y -= (height + self.tile_size * 2)


clock = pygame.time.Clock()
running = True
player = Player()
infinity_world = InfinityWorld()

while running:
    dt = clock.tick(FPS) / 1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            pass

    keys = pygame.key.get_pressed()
    dx = keys[pygame.K_d] - keys[pygame.K_a]
    dy = keys[pygame.K_s] - keys[pygame.K_w]

    player.update(dx, dy)
    infinity_world.update_tiles()

    screen.fill((0, 0, 0))
    tiles_group.draw(screen)
    player_group.draw(screen)

    clock.tick(60)
    pygame.display.flip()
pygame.quit()
