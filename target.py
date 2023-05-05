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
        pixels_in_cm = WINDOW_WIDTH / (1.04743*y_distance+0.334229)

        # Calc max x and z distance, so circle is initialy visable on screen after centering
        self.x_max = int((WINDOW_WIDTH / 2) / pixels_in_cm)
        self.z_max = int((WINDOW_HEIGHT / 2) / pixels_in_cm)

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


    def update(self, x_displacement, y_displacement, z_displacement, turn_degree):
        # Update relative distance from displacments (cm)
        self.distance = (self.distance[0] + x_displacement, self.distance[1] + y_displacement, self.distance[2] + z_displacement)

        # self.distance[1] is the y distance
        pixels_in_cm = WINDOW_WIDTH / (1.04743*self.distance[1]+0.334229)

        # Re-calc px radius based on new px per cm count
        self.px_radius = pixels_in_cm * self.cm_radius

        # Stop shrinking px radius if target is over 220 cm away
        if self.px_radius < 8:
            self.px_radius = 8

        # Compensate for turning:

        # Calc how far target would have moved along x-axis, for given turn degree
        turn_chord = 2*self.distance[1] * math.sin(math.radians(turn_degree)/2)
        # Calc how far target would have moved along y-axis, for given turn degree
        turn_segment_y_length = self.distance[1] - math.sqrt(self.distance[1]**2 - (turn_chord / 2)**2)

        # Update relative distance by turn-compensation
        self.distance = (self.distance[0] - turn_chord, self.distance[1] - turn_segment_y_length, self.distance[2])


        # If drone is close to target:
        # criteria - (-15<x<15) (-15<y<15) (-15<z<15)
        if (self.distance[1] > -15 and self.distance[1] < 15) and (self.distance[2] > -15 and self.distance[2] < 15) and (self.distance[0] > -15 and self.distance[0] < 15):
            # score 1 point
            self.score += 1
            # relocate target
            self.distance = (random.randint(-self.x_max, self.x_max), random.randint(self.y_min, self.y_max), random.randint(-self.z_max, self.z_max))
            # new color
            self.color = tuple(np.random.choice(range(256), size=3))


    def draw(self, surface):
        pixels_in_cm = WINDOW_WIDTH / (1.04743*self.distance[1]+0.334229)

        # Convert x & z distance to px and display relative to screen center (drone position)
        # This is because when self.distance = [0, 0, 0],
        #   ...target should be in the center of screen,
        #   ...where the drone's camera center is,
        #   ...rather than in the top left corner of the pygame window
        x_screen_point = pixels_in_cm * self.distance[0] + WINDOW_WIDTH / 2
        z_screen_point = pixels_in_cm * self.distance[2] + WINDOW_HEIGHT / 2

        # Update display_center (x, z) tuple
        self.display_center = (x_screen_point, z_screen_point)

        # Draw the target on provided surface (current frame)
        circle(surface, self.color, self.display_center, self.px_radius)
