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
DRONE_YAW_SPEED = 40
# Derived experimentally (m/s)
DRONE_FLY_SPEED = 10
past_height = 0

# Use as ~2s buffer before starting game after take-off
CALIBRATION_DELAY = 200
delayed = 0

# target doesn't exist untill flying
target = None

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


def calculate_yaw_degree(time_interval: float) -> float:
    '''
        Use FPS avarage & tello's rotation speed to determine precise-'ish'
        rotation in degrees
    '''

    effective_yaw_degree = DRONE_YAW_SPEED * time_interval

    return effective_yaw_degree


def calculate_effective_displcment(time_interval: float) -> float:
    '''
        Use FPS avarage & tello's flight speed to determine precise-'ish'
        horizontal displacment in cm
    '''

    effective_displacment = DRONE_FLY_SPEED * time_interval

    return effective_displacment


def get_height_displcment() -> float:
    '''
        Use Tello's barometer to determine precise-'ish' vertical displacment in cm
    '''

    global past_height

    height = get_barometer()

    change_in_height = past_height - height

    past_height = height

    return change_in_height


def get_flight_control_input() -> tuple[tuple[int, int, int, int], tuple[int, int, int], int]:
    # Get list of key states
    keys = pygame.key.get_pressed()

    # Calc the time interval for these inputs to take place
    fps = clock.get_fps()
    time_interval = 1 / fps

    control_values = (0, 0, 0, 0)
    displacments = (0, 0, 0)
    yaw_degree = 0

    if keys[pygame.K_RIGHT]:
        control_values[0] = 20
        displacment[0] = calculate_effective_displcment(DRONE_FLY_SPEED, time_interval)
    elif keys[pygame.K_LEFT]:
        control_values[0] = -20
        displacment[0] = -calculate_effective_displcment(DRONE_FLY_SPEED, time_interval)

    if keys[pygame.K_UP]:
        control_values[1] = 20
        displacment[1] = calculate_effective_displcment(DRONE_FLY_SPEED, time_interval)
    elif keys[pygame.K_DOWN]:
        control_values[1] = -20
        displacment[1] = -calculate_effective_displcment(DRONE_FLY_SPEED, time_interval)

    if keys[pygame.K_w]:
        control_values[2] = 20
    elif keys[pygame.K_s]:
        control_values[2] = -20
    displacment[2] = get_height_displcment()

    if keys[pygame.K_d]:
        control_values[3] = 60
        yaw_degree = calculate_yaw_degree()
    elif keys[pygame.K_a]:
        control_values[3] = -60
        yaw_degree = -calculate_yaw_degree()

    return control_values, displacment, yaw_degree


# Game-loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            drone.land()
            cap.release()
            pygame.quit()
            sys.exit(0)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                drone.land()
            elif event.key == pygame.K_e:
                drone.takeoff()
            elif event.key == pygame.K_p:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                frame = cv2.flip(frame, 1)

                timestr = time.strftime('%d/%m/%Y-%H:%M:%S', time.localtime())

                cv2.imwrite(f'./Tello-frame:{timestr}.jpg', frame)
                pygame.image.save(screen, f'./Game-screen:{timestr}.jpg')


    success, frame = cap.read()
    if not success:
        break

    # Proccess frame for natural look
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    frame = cv2.flip(frame, 1)
    frame_surface = pygame.surfarray.make_surface(frame)

    screen.blit(frame_surface, (0, 0))

    # Execute ~2s buffer
    if drone.is_flying and delayed < CALIBRATION_DELAY:
        delayed += 1
    # The game is active
    if delayed >= CALIBRATION_DELAY:
        # If no target is present, create one
        if not target:
            target = Target(10, 60)
        control_values, displacments, yaw_degree = get_flight_control_input()
        drone.send_rc_control(control_values[0], control_values[1], control_values[2], control_values[3])
        target.update(displacments[0], displacments[1], displacments[2])

        # Render HUD
        x_distance_display = font.render(f'X - distance: {round(target.distance[0], 2)}', True, (0, 0, 250))
        y_distance_display = font.render(f'Y - distance: {round(target.distance[1], 2)}', True, (0, 0, 250))
        z_distance_display = font.render(f'Z - distance: {round(target.distance[2], 2)}', True, (0, 0, 250))
        score_display = font.render(f'Score: {target.score}', True, (0, 250, 0))

        # Blit HUD
        screen.blit(x_distance_display, dest=(10,10))
        screen.blit(y_distance_display, dest=(10,45))
        screen.blit(z_distance_display, dest=(10,75))
        screen.blit(score_display, dest=(800,10))

        # Blit target
        target.draw(screen, yaw_degree)

    # Update entire display
    pygame.display.update()
    # Limit frame-rate
    clock.tick(60)

# Back-up, if the program manages to get to here (somehow)
drone.land()
cap.release()
