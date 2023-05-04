# Import 3rd party libraries
from djitellopy import Tello

import pygame

import cv2

import numpy as np

import random

import time

import os

import math


pygame.init()


# Connect Tello drone
drone = Tello()
drone.connect()
drone.streamon()


# Set global variables
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
WINDOW_SIZE = (WINDOW_WIDTH, WINDOW_HEIGHT)

score = 0

cap = cv2.VideoCapture(drone.get_udp_video_address())
orb = cv2.ORB_create()
bruite_force_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

dronePosition = np.zeros((3, 1))
droneRotation = np.eye(3)
prev_des = None
old_pos = [0, 0, 0, 0]

font = pygame.font.Font(pygame.font.get_default_font(), 36)
screen = pygame.display.set_mode(WINDOW_SIZE)
clock = pygame.time.Clock()

circle = None



# Class of main game sprite, the target circle
class Circle(pygame.sprite.Sprite):
    def __init__(self, y_min, y_max):
        # Inherit Sprite class
        super().__init__()

        # Loading in minimum and maximum circle distance from the drone's front, (y)
        self.y_min = y_min
        self.y_max = y_max

        y_distance = random.randint(y_min, y_max)

        # Get px per cm at randomly picked y distance
        pixelsInCm = WINDOW_WIDTH/((1.04743*y_distance)+0.334229)

        # Calc max values for x and z, so circle is initialy visable on screen
        self.x_max = int((WINDOW_WIDTH/2) / pixelsInCm)
        self.z_max = int((WINDOW_HEIGHT/2) / pixelsInCm)

        # This distance is relative to drone, stored in 'kinda should be cm' units
        self.distance = (random.randint(-self.x_max, self.x_max), y_distance, random.randint(-self.z_max, self.z_max))

        self.cmRadius = 2

        # CALC at update() and/or draw()

        # Derived px radius, concidering distance-scale
        self.pxRadius =  0

        # An (x, z) point in px, to display circle on fpv frame, centered
        self.display_center = (0, 0)


    def update(self, x_velocity, y_velocity, z_velocity, degree):

        pixelsInCm = WINDOW_WIDTH/((1.04743*self.distance[1])+0.334229)
        self.pxRadius = pixelsInCm * self.cmRadius

        # Proudly Alexander Kashpir© technology
        sector_width = 2*(self.distance[1] + y_velocity)*(math.sin(math.radians(degree)/2))
        sector_height = self.distance[1]- math.sqrt((self.distance[1]*self.distance[1])-((sector_width/2)*(sector_width/2)))

        # Update to new relative distance
        self.distance = (self.distance[0] + x_velocity-sector_width, self.distance[1] + y_velocity-sector_height, self.distance[2] + z_velocity)

        # If the drone is really close to the target circle, score a point,
        # relocate target
        if (self.distance[1] > -15 and self.distance[1] < 15) and (self.distance[2] > -15 and self.distance[2] < 15) and (self.distance[0] > -15 and self.distance[0] < 15):
            global score
            score += 1
            self.distance = (random.randint(-self.x_max, self.x_max), random.randint(self.y_min, self.y_max), random.randint(-self.z_max, self.z_max))
    def draw(self, surface):
        pixelsInCm = WINDOW_WIDTH/((1.04743*self.distance[1])+0.334229)
        distance_x = (pixelsInCm * self.distance[0]) + (WINDOW_WIDTH/2) - (self.pxRadius/2)
        distance_y = (pixelsInCm * self.distance[2]) + (WINDOW_HEIGHT/2) - (self.pxRadius/2)
        self.display_center = (distance_x, distance_y)
        pygame.draw.circle(surface, (255,0,0), (distance_x, distance_y), self.pxRadius)






while True:
    success, frame = cap.read()

    if not success:
        break

    # Proccess frame for natural look
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    frame = cv2.flip(frame, 1)

    if drone.is_flying:
        # Wait a bit for the drone to stabilize
        time.sleep(2)

        # If no target is present, create one
        if not circle:
            circle = Circle(10, 60)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        kps, des = orb.detectAndCompute(gray, None)
        if prev_des is not None:
            # Find the 10% of the best description matches between the two frames
            matches = sorted(bruite_force_matcher.match(des, prev_des), key=lambda match: match.distance)
            matches = matches[:int(len(matches)*0.1)]

            dronePosition = np.zeros((3, 1))
            droneRotation = np.eye(3)
            dz = np.mean([kps[match.queryIdx].size - prev_kps[match.trainIdx].size for match in matches])
            dy = np.mean([kps[match.queryIdx].pt[1] - prev_kps[match.trainIdx].pt[1] for match in matches])



            dx = np.mean([kps[match.queryIdx].pt[0] - prev_kps[match.trainIdx].pt[0] for match in matches])
            dronePosition += droneRotation.dot(np.array([[dx], [dy], [dz]]))

            match_img = cv2.drawMatches(frame, kps, prev_frame, prev_kps, matches, None)
            img_surface = pygame.surfarray.make_surface(match_img)
        else:
            img_surface = pygame.surfarray.make_surface(frame)
            yaw = 0

        prev_kps = kps
        prev_des = des
        prev_frame = frame

        velocity = [0, 0, 0, 0]
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT]:
            velocity[0] = 20
        elif keys[pygame.K_LEFT]:
            velocity[0] = -20
        if keys[pygame.K_UP]:
            velocity[1] = 20
        elif keys[pygame.K_DOWN]:
            velocity[1] = -20
        if keys[pygame.K_w]:
            velocity[2] = 20
        elif keys[pygame.K_s]:
            velocity[2] = -20
        if keys[pygame.K_d]:
            velocity[3] = 20
        elif keys[pygame.K_a]:
            velocity[3] = -20
        drone.send_rc_control(velocity[0], velocity[1], velocity[2], velocity[3])

    else:
        img_surface = pygame.surfarray.make_surface(frame)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            cap.release()
            drone.land()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                drone.land()
            elif event.key == pygame.K_e:
                drone.takeoff()
            elif event.key == pygame.K_p:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                frame = cv2.flip(frame, 1)
                timestr = time.strftime('%H-%M', time.localtime())
                cv2.imwrite(f'./images/Tello-{timestr}.jpg', frame)
                pygame.image.save(screen, f'./images/Game-{timestr}.jepg')
            elif event.key == pygame.K_i:
                print(f'\nBattery: {drone.get_battery}\n')


    # Drone-free option
    #screen.fill((255, 255, 255))
    #circle.draw(screen)


    # Display the current frame
    screen.blit(img_surface, (0, 0))


    # If there is a circle, prepare (y & d) change values
    if circle:
        try:
            pos = [int(number/1) for number in dronePosition.flatten()]
        except:
            pass
        for i, val in enumerate(pos):
            pos[i] -= old_pos[i]


        # Update target circle's position proportional to
        # (x & z) frame displacment and (y & d) velocity
        circle.update(pos[1]/4, -velocity[1]/20, pos[0]/4, velocity[3]/20)

        # Render HUD
        x_distance_display = font.render(f'X - distance: {round(circle.distance[0], 2)}', True, (0, 0, 250))
        y_distance_display = font.render(f'Y - distance: {round(circle.distance[1], 2)}', True, (0, 0, 250))
        z_distance_display = font.render(f'Z - distance: {round((circle.distance[2]*-1), 2)}', True, (0, 0, 250))

        score_display = font.render(f'Score: {score}', True, (0, 250, 0))


        # Blit HUD
        screen.blit(x_distance_display, dest=(10,10))
        screen.blit(y_distance_display, dest=(10,45))
        screen.blit(z_distance_display, dest=(10,75))
        screen.blit(score_display, dest=(800,10))

        # Blit target circle
        circle.draw(screen)


    # Update the whole display and limit frame-rate
    pygame.display.update()
    clock.tick(60)


# Back-up, if the program manages to get to here (somehow)
drone.land()
cap.release()
