import os
import time
import random

import pygame
from pygame.locals import *


def load_image(file_name: str, convert_alpha=False) -> pygame.Surface:
	image = pygame.image.load(f'images/{file_name}')
	if convert_alpha:
		image.set_colorkey(image.get_at((0, 0)))
		image.convert_alpha()

	return image


class Game:
	width: int = 960
	height: int = 1010

	fps: int = 60

	top_padding: int = 100
	width_padding: int = 10
	wall_padding: int = 50
	bottom_padding: int = 150

	wall_bottom_padding: int = 100

	def __init__(self):
		self.frame = 0
		self.score = 0
		self._init_pygame()
		self.font = pygame.font.Font('space_invaders.ttf', 30)
		self.display = pygame.display.set_mode((self.width, self.height))
		self.clock = pygame.time.Clock()

		self.tank = Tank()
		self.tank.left_top = (
			self.wall_padding, 
			self.height - self.bottom_padding,
		)

		self.walls = [Wall() for _ in range(4)]
		wall_width_padding = (
			(self.width - self.wall_padding * 4 - self.walls[0].rect[2]) // 3
		)
		for iteration, wall in enumerate(self.walls):
			wall.left_top = (
				int(self.wall_padding * 2) + iteration * wall_width_padding, 
				self.height - self.bottom_padding - self.wall_bottom_padding,
			)

		self.enemies = Enemies(self)
		self.explosions = []

		self.keys_pressed = []

	def _init_pygame(self):
		os.environ['SDL_VIDEO_WINDOW_POS'] = '960,30'
		pygame.init()

	def update(self):
		self.display.fill((0, 0, 0))

		for event in pygame.event.get():
			if event.type == QUIT:
				pygame.quit()
				exit()
			elif event.type == pygame.KEYDOWN:
				self.keys_pressed.append(event.key)
			elif event.type == pygame.KEYUP:
				self.keys_pressed.remove(event.key)

		if self.enemies:
			self._update_tank()
			self._update_walls()
			self._update_enemies()
			self._draw_score()

		for idx, explosion in enumerate(reversed(self.explosions)):
			if explosion.frames == 0:
				self.explosions.pop(~idx)
			else:
				explosion.draw(self.display)

		pygame.display.update()
		self.clock.tick(self.fps)
		self.frame += 1

	def _update_tank(self):
		if self.tank.dead_frames is not None:
			self.tank.draw(self.display)
			return

		for key in self.keys_pressed:
			if key == K_d:
				if self.tank.right < self.width - self.width_padding:
					self.tank.rect.move_ip(5, 0)
			elif key == K_a:
				if self.tank.left > self.width_padding:
					self.tank.rect.move_ip(-5, 0)
			elif key == K_SPACE:
				if self.tank.bullet is None and self.tank.bullet_freeze == 0:
					self.tank.bullet = TankBullet()
					self.tank.bullet.left_top = (
						self.tank.rect.center[0] - self.tank.bullet.width // 2,
						self.tank.rect.center[1] - self.tank.rect[3],
					)

		if self.tank.bullet is not None:
			self.tank.bullet.rect.move_ip(0, -15)

			for (row, col), enemy in self.enemies:
				if enemy.does_collide(self.tank.bullet):
					if row == 0:
						self.score += 30
					elif row in {1, 2}:
						self.score += 20
					else:
						self.score += 10
					enemy.kill()
					self.tank.bullet = None
					self.tank.bullet_freeze = enemy.death_frames
					break

			if self.tank.bullet:
				for idx, enemy_bullet in enumerate(reversed(self.enemies.bullets)):
					if enemy_bullet.does_collide(self.tank.bullet):
						self.explosions.append(Explosion(30, enemy_bullet.rect.center))
						self.tank.bullet = None
						self.tank.bullet_freeze = 30
						self.enemies.bullets.pop(~idx)
						break

			if self.tank.bullet:
				if self.tank.bullet.top < self.top_padding:
					self.tank.bullet = None
				else:
					for wall in self.walls:
						cord = wall.does_collide(self.tank.bullet)
						if cord:
							wall.damage(cord, by=self.tank.bullet)
							self.tank.bullet = None
							self.tank.bullet_freeze = 20
							break

		if self.tank.bullet_freeze > 0:
			self.tank.bullet_freeze -= 1

		self.tank.draw(self.display)

	def _update_walls(self):
		for wall in self.walls:
			wall.draw(self.display)

	def _update_enemies(self):
		if (
				self.enemies.last_shot is None 
				or self.enemies.last_shot + self.shot_cooldown < time.time()
				and self.tank.dead_frames is None
		):
			enemies_per_col = {}
			for (row, col), enemy in self.enemies:
				if col not in enemies_per_col or row > enemies_per_col[col][0]:
					enemies_per_col[col] = row, enemy
			_, enemy = random.choice(list(enemies_per_col.values()))
			self.enemies.bullets.append(enemy.shot())
			self.enemies.last_shot = time.time()

		for idx, bullet in enumerate(reversed(self.enemies.bullets)):
			bullet.rect.move_ip((0, 5))
			if bullet.does_collide(self.tank):
				self.tank.explode()
				self.enemies.bullets.pop(~idx)
				break
			for wall in self.walls:
				cord = wall.does_collide(bullet)
				if cord:
					wall.damage(cord, bullet)
					self.enemies.bullets.pop(~idx)
					break
			else:
				bullet.draw(self.display)

		for _, enemy in self.enemies:
			for wall in self.walls:
				if (cord := wall.does_collide(enemy)):
					wall.damage(cord, enemy)
			if enemy.does_collide(self.tank) or enemy.bottom > self.height:
				self.tank.explode()

		if self.frame > (self.enemies.count_alive() + 5) // 2:
			if self.tank.dead_frames is None:
				self.enemies.move()
			self.frame = 0
		self.enemies.draw(self.display)

	@property
	def shot_cooldown(self):
		return 0.5 + self.enemies.count_alive() / 55 / 2

	def _draw_score(self):
		image = self.font.render(f'score < {self.score} >', True, (255, 255, 255))
		self.display.blit(image, (40, 30))


class SpriteMixin:

	def draw(self, surface):
		surface.blit(self.image, self.rect)

	@property
	def left(self):
		return self.rect[0]

	@property
	def top(self):
		return self.rect[1]

	@property
	def right(self):
		return self.rect[0] + self.rect[2]

	@property
	def bottom(self):
		return self.rect[1] + self.rect[3]

	@property
	def left_top(self):
		return self.left, self.top

	@left_top.setter
	def left_top(self, value: tuple):
		self.rect.center = (
			value[0] + self.rect[2] // 2,
			value[1] + self.rect[3] // 2,
		)

	def does_collide(self, sprite):
		return pygame.sprite.collide_mask(self, sprite)


class Tank(pygame.sprite.Sprite, SpriteMixin):

	def __init__(self):
		self.image = load_image('tank.png', True)
		self.rect = self.image.get_rect()
		self.dead_frames = None
		self.dead_image = load_image('tank_explosion.png', True)

		self.bullet = None
		self.bullet_freeze = 0

	def explode(self):
		self.image = self.dead_image
		self.dead_frames = 30

	def draw(self, surface):
		if self.dead_frames is not None:
			self.dead_frames -= 1
			self.image = self.dead_image
			if self.dead_frames <= 0:
				return
		super().draw(surface)
		if self.bullet is not None:
			self.bullet.draw(surface)


class TankBullet(pygame.sprite.Sprite, SpriteMixin):
	width = 4
	height = 30

	def __init__(self):
		self.image = pygame.Surface((self.width, self.height))
		self.image.convert_alpha()
		self.image.fill((0, 255, 0))
		self.rect = self.image.get_rect()


class Wall(pygame.sprite.Sprite, SpriteMixin):

	def __init__(self):
		self.image = load_image('wall.png', True)
		self.rect = self.image.get_rect()
		self.damage_mask = load_image('shield_explosion.png', True)
		self.damage_rect = self.damage_mask.get_rect()

	def damage(self, cord: tuple, by: pygame.sprite.Sprite):
		cord = list(cord)
		cord[0] -= self.damage_rect[2] // 2
		cord[0] -= cord[0] % 10
		if isinstance(by, TankBullet):
			cord[1] -= self.damage_rect[3] // 2
		else:
			cord[1] -= 10
		cord[1] -= cord[1] % 10

		for y in range(self.damage_rect[2]):
			for x in range(self.damage_rect[3]):
				color = self.damage_mask.get_at((y, x))
				if color == (0, 0, 0):
					wall_cord = (cord[0] + y, cord[1] + x)
					if wall_cord[0] < self.rect[2] and wall_cord[1] < self.rect[3]:
						self.image.set_at(wall_cord, (0, 0, 0))


class Enemies:
	columns = 11
	rows = 5
	width_spacing = 20
	height_spacing = 40

	def __init__(self, game: Game):
		self.game = game

		self.entities = self._create_entities()
		self._place_entities()
		self.width_speed = 10
		self.height_speed = 40
		self.velocity = (self.width_speed, 0)  # to right
		self.last_shot = None
		self.bullets = []

	def _create_entities(self):
		return [
			[Enemy('enemy_3.png', self, (0, col)) for col in range(self.columns)],
			[Enemy('enemy_2.png', self, (1, col)) for col in range(self.columns)],
			[Enemy('enemy_2.png', self, (2, col)) for col in range(self.columns)],
			[Enemy('enemy_1.png', self, (3, col)) for col in range(self.columns)],
			[Enemy('enemy_1.png', self, (4, col)) for col in range(self.columns)],
		]

	def _place_entities(self):
		current_height = self.game.top_padding
		for entities_row in self.entities:
			for col, entity in enumerate(entities_row):
				entity.left_top = (
					self.game.width_padding 
					+ col * (entity.max_width + self.width_spacing)
					+ entity.extra_padding,
					current_height,
				)
			current_height += entities_row[0].rect[3] + self.height_spacing

	def count_alive(self):
		return sum(bool(entity) for row in self.entities for entity in row)

	def suicide(self, entity):
		self.entities[entity.cord[0]][entity.cord[1]] = None

	def move(self):
		min_left, max_right = float('inf'), 0
		for entities_row in self.entities:
			for entity in entities_row:
				if entity is None:
					continue
				entity.rect.move_ip(*self.velocity)
				entity.image_idx += 1
				min_left = min(min_left, entity.left)
				max_right = max(max_right, entity.right)

		if self.velocity[1] == 0:
			if (
				(
					self.velocity[0] > 0 and  # to right
					max_right > self.game.width - self.game.width_padding
				) or (
					self.velocity[0] < 0 and  # to left
					min_left < self.game.width_padding
				)
			):
				self.velocity = (0, self.height_speed)
		else:
			if min_left < self.game.width_padding:
				self.velocity = self.width_speed, 0
			else:
			 	self.velocity = -self.width_speed, 0

	def draw(self, surface):
		for row, entities_row in enumerate(self.entities):
			for col, entity in enumerate(entities_row):
				if entity is not None:
					entity.draw(surface)

	def __iter__(self):
		for row, enemies_row in enumerate(self.entities):
			for col, enemy in enumerate(enemies_row):
				if enemy is not None:
					yield (row, col), enemy


class Enemy(pygame.sprite.Sprite, SpriteMixin):
	max_width = 60
	max_height = 40
	death_frames = 30

	def __init__(self, file_name: str, parent: Enemies, cord: tuple):
		self.parent = parent
		self.cord = cord

		raw_images = load_image(file_name, True)
		*_, width, height = raw_images.get_rect()
		self.images = [
			raw_images.subsurface(0, 0, width // 2, height),
			raw_images.subsurface(width // 2, 0, width // 2, height),
		]
		self.dead_image = load_image('explosion.png', True)
		self.kill_after = None
		self.image_idx = 0
		self.rect = self.image.get_rect()

		self.extra_padding = self.max_width // 2 - self.rect[2] // 2

	@property
	def image(self):
		if self.kill_after:
			self.kill_after -= 1
			if self.kill_after == 0:
				self.parent.suicide(self)
			return self.dead_image

		if self.image_idx == len(self.images):
			self.image_idx = 0
		return self.images[self.image_idx]

	def kill(self):
		self.kill_after = self.death_frames

	def shot(self):
		bullet = EnemyBullet()
		bullet.left_top = (self.rect.center[0], self.bottom)
		return bullet


class EnemyBullet(pygame.sprite.Sprite, SpriteMixin):

	def __init__(self):
		raw_images = load_image('bullet.png', True)
		*_, width, height = raw_images.get_rect()
		self.images = [
			raw_images.subsurface(0, 0, width // 2, height),
			raw_images.subsurface(width // 2, 0, width // 2, height),
		]
		self.frame_idx = 0
		self.image_idx = 0
		self.rect = self.image.get_rect()

	@property
	def image(self):
		self.frame_idx += 1
		if self.frame_idx == 30:
			self.frame_idx = 0
			self.image_idx += 1
		if self.image_idx == len(self.images):
			self.image_idx = 0
		return self.images[self.image_idx]


class Explosion(pygame.sprite.Sprite, SpriteMixin):

	def __init__(self, frames, cord):
		self.image = load_image('explosion.png', True)
		self.rect = self.image.get_rect()
		self.rect.center = cord
		self.frames = frames

	def draw(self, surface):
		self.frames -= 1
		super().draw(surface)


if __name__ == '__main__':
	game = Game()

	while True:
		game.update()
