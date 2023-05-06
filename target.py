# Import necessary pygame class & method
from pygame.sprite import Sprite
from pygame.draw import circle

import numpy as np

import random

import math

# Re-defining project constants to avoid circular-imports
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720


class Target(Sprite):
    def __init__(self, y_min, y_max):
        # Inherit Sprite class
        super().__init__()

        # Give target random color
        self.color = tuple(np.random.choice(range(256), size=3))

        # Save min/max distance from drone's front
        self.y_min = y_min
        self.y_max = y_max

        # Pick y distance first, to establish x & z max
        y_distance = random.randint(self.y_min, self.y_max)

        # Calc px per cm at the y distance
        px_in_cm = self.get_px_in_cm(y_distance)

        # Calc max x and z distance, so circle is initialy visable on screen after centering
        self.x_max = int((WINDOW_WIDTH / 2) / px_in_cm)
        self.z_max = int((WINDOW_HEIGHT / 2) / px_in_cm)

        # Target distance (cm) is relative to drone
        self.distance = (random.randint(-self.x_max, self.x_max), y_distance, random.randint(-self.z_max, self.z_max))

        # The target is a circle, with a 2cm radius
        self.cm_radius = 2

        # Calculated when necessary

        # Radius in px, derived from y distance
        self.px_radius =  0

        # An on screen (x, z) location coordinate, in px
        self.display_center = (0, 0)

        # Game score
        self.score = 0

        # Use for visual adjustment with yaw rotation
        self.yaw_x_visual_adjustment = 0


    def get_px_in_cm(self, y_distance):
        # Formula for distance scaling derived experimentally
        return WINDOW_WIDTH / (1.04743 * y_distance + 0.334229)


    def update(self, x_displacement, y_displacement, z_displacement):
        # Update relative distance from displacments (cm)
        self.distance = (self.distance[0] + x_displacement, self.distance[1] + y_displacement, self.distance[2] + z_displacement)

        # self.distance[1] is the y distance
        px_in_cm = self.get_px_in_cm(self.distance[1])

        # Re-calc px radius based on new px per cm value
        self.px_radius = px_in_cm * self.cm_radius

        # If drone is close to target:
        # criteria (-15<x<15) (-15<y<15) (-15<z<15)
        if (self.distance[1] > -15 and self.distance[1] < 15) and (self.distance[2] > -15 and self.distance[2] < 15) and (self.distance[0] > -15 and self.distance[0] < 15):
            # score 1 point
            self.score += 1
            # relocate target
            self.distance = (random.randint(-self.x_max, self.x_max), random.randint(self.y_min, self.y_max), random.randint(-self.z_max, self.z_max))
            # set target new color
            self.color = tuple(np.random.choice(range(256), size=3))


    def draw(self, surface, turn_degree):
        px_in_cm = self.get_px_in_cm(self.distance[1])

        # Preform visual adjustment on yaw rotation
        if turn_degree != 0:
            self.yaw_x_visual_adjustment += self.distance[1] * px_in_cm * math.cos(math.radians(turn_degree)) - self.distance[1] * px_in_cm

        # Convert x & z distance to px and display relative to screen center (drone position)
        # This is because when self.distance = [0, 0, 0],
        #   ...target should be in the center of screen,
        #   ...where the drone's camera center is,
        #   ...rather than in the top left corner of the pygame window

        x_screen_point = px_in_cm * self.distance[0] + self.yaw_x_visual_adjustment + WINDOW_WIDTH / 2
        z_screen_point = px_in_cm * self.distance[2] + WINDOW_HEIGHT / 2

        # Update display_center (x, z) tuple
        self.display_center = (x_screen_point, z_screen_point)

        # Draw the target on provided surface (current frame)
        circle(surface, self.color, self.display_center, self.px_radius)
