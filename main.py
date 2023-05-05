# Import 3rd party libraries
from djitellopy import Tello

import pygame

import cv2

import numpy as np

import time

from os import sys

# Import custom Target class
from target import Target


pygame.init()


# Initialize Tello drone
drone = Tello()
drone.connect()
drone.streamon()


# Pygame window parameters
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
WINDOW_SIZE = (WINDOW_WIDTH, WINDOW_HEIGHT)
WINDOW_NAME = 'Chase the Dot'

# Derived experimentally (d°/s)
DRONE_ROTATION_SPEED = 62.07

# Game score
score = 0


# Initialize cv2 objects

# Capture video from drone's udp port
cap = cv2.VideoCapture(drone.get_udp_video_address())

# ORB feature detection alg. -> speed + accuracy
orb = cv2.ORB_create()

# Define matching algorythm
bruite_force_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

dronePosition = np.zeros((3, 1))
droneRotation = np.eye(3)
prev_des = None
old_pos = [0, 0, 0, 0]

# Set up pygame variables
font = pygame.font.Font(pygame.font.get_default_font(), 36)
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption(WINDOW_NAME)
clock = pygame.time.Clock()

# target object is empty untill take-off
circle = None


def calculate_rotation_degree() -> float:
    '''
        Use FPS avarage & tello's rotation speed to determine precise
        rotation in degrees
    '''

    # Get fps avarage from clock, only works in game loop
    fps = clock.get_fps()

    # Convert second-fraction to milliseconds
    time_interval = 1/fps * 1000

    rotation_degree = ROTATION_SPEED * time_interval

    return rotation_degree


# Game-loop
while True:
    success, frame = cap.read()

    if not success:
        break

    # Proccess frame for natural look
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    frame = cv2.flip(frame, 1)

    if drone.is_flying and calibration_delay < 150:
        calibration_delay += 1

    if calibration_delay > 149:
        # If no target is present, create one
        if not circle:
            circle = Target(10, 60)

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

        # Record current frame features for comparison
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
            velocity[3] = 360
        elif keys[pygame.K_a]:
            velocity[3] = -360
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
        # (x & z) frame displacment, y velocity and calculated d
        rotation_degree = calculate_rotation_degree()
        circle.update(pos[1]/4, -velocity[1]/20, pos[0]/4, rotation_degree)

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
