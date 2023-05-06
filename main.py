# Import 3rd party libraries
from djitellopy import Tello

import pygame

import cv2

import numpy as np

import time

from os import sys

# Import custom Target class
from target import Target


# Pygame window parameters
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
WINDOW_SIZE = (WINDOW_WIDTH, WINDOW_HEIGHT)
WINDOW_NAME = 'Chase the Dot'

# Derived experimentally (d°/s)
DRONE_YAW_SPEED = 10.35

# Use to store x & z displacment from frame-shift
drone_x_z_change = [0, 0]

# Use as ~2s buffer before starting game after take-off
CALIBRATION_DELAY = 150
delayed = 0

# target doesn't exist untill flying
target = None
# ORB feature detection alg. for speed + accuracy

orb = cv2.ORB_create()
# To store orb description of previous frame
prev_frame_des = None
# Define matching algorythm
bruite_force_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


pygame.init()


# Initialize Tello drone
drone = Tello()
drone.connect()
drone.streamon()
# Capture video from drone's udp port
cap = cv2.VideoCapture(drone.get_udp_video_address())


# Set up pygame variables
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption(WINDOW_NAME)

font = pygame.font.Font(pygame.font.get_default_font(), 36)
clock = pygame.time.Clock()


def calculate_yaw_degree() -> float:
    '''
        Use FPS avarage & tello's rotation speed to determine precise
        rotation in degrees
    '''

    # Get fps avarage from clock, only works in game loop
    fps = clock.get_fps()

    time_interval = 1 / fps

    yaw_degree = DRONE_YAW_SPEED * time_interval

    yaw_degree = yaw_degree * 0.7

    return yaw_degree



# Game-loop
while True:
    success, frame = cap.read()
    if not success:
        break


    # Proccess frame for natural look
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    frame = cv2.flip(frame, 1)


    # Execute ~2s buffer
    if drone.is_flying and delayed < 150:
        delayed += 1
    # The game is active
    if delayed >= CALIBRATION_DELAY:
        # If no target is present, create one
        if not target:
            target = Target(10, 60)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        kps, des = orb.detectAndCompute(gray, None)
        if prev_frame_des is not None:
            # Find the 10% of the best description matches between the two frames
            matches = sorted(bruite_force_matcher.match(des, prev_frame_des), key=lambda match: match.distance)
            matches = matches[:int(len(matches)*0.1)]

            dx = np.mean([kps[match.queryIdx].pt[0] - prev_kps[match.trainIdx].pt[0] for match in matches])
            dz = np.mean([kps[match.queryIdx].pt[1] - prev_kps[match.trainIdx].pt[1] for match in matches])
            drone_x_z_change = [dx, dz]

            match_img = cv2.drawMatches(frame, kps, prev_frame, prev_kps, matches, None)
            img_surface = pygame.surfarray.make_surface(match_img)
        else:
            img_surface = pygame.surfarray.make_surface(frame)
            yaw = 0

        # Record current frame features for comparison
        prev_kps = kps
        prev_frame_des = des
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
            velocity[3] = 60
            yaw_degree = calculate_yaw_degree()
        elif keys[pygame.K_a]:
            velocity[3] = -60
            yaw_degree = calculate_yaw_degree()
        else:
            yaw_degree = 0
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
                cv2.imwrite(f'./Tello-{timestr}.jpg', frame)
                pygame.image.save(screen, f'./Game-{timestr}.jpeg')


    # Display the current frame
    screen.blit(img_surface, (0, 0))


    if target:
        # Update target target's position proportional to
        # (x & z) frame displacment, y velocity and calculated d
        target.update(drone_x_z_change[1]/4, -velocity[1]/20, drone_x_z_change[0]/4, yaw_degree)

        # Render HUD
        x_distance_display = font.render(f'X - distance: {round(target.distance[0], 2)}', True, (0, 0, 250))
        y_distance_display = font.render(f'Y - distance: {round(target.distance[1], 2)}', True, (0, 0, 250))
        z_distance_display = font.render(f'Z - distance: {round((target.distance[2]*-1), 2)}', True, (0, 0, 250))

        score_display = font.render(f'Score: {target.score}', True, (0, 250, 0))


        # Blit HUD
        screen.blit(x_distance_display, dest=(10,10))
        screen.blit(y_distance_display, dest=(10,45))
        screen.blit(z_distance_display, dest=(10,75))
        screen.blit(score_display, dest=(800,10))

        # Blit target
        target.draw(screen)


    # Update the whole display and limit frame-rate
    pygame.display.update()
    clock.tick(60)


# Back-up, if the program manages to get to here (somehow)
drone.land()
cap.release()
