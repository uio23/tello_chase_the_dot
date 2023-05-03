from djitellopy import Tello

import pygame

import cv2

import random

import time

import os

import math

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720

#DRONE

drone = Tello()
drone.connect()
drone.streamon()
time.sleep(0.5)

cap = cv2.VideoCapture(drone.get_udp_video_address())

#END

WINDOW_SIZE = (WINDOW_WIDTH, WINDOW_HEIGHT)

clock = pygame.time.Clock()

class Circle(pygame.sprite.Sprite):
    def __init__(self, y_min, y_max):
        super().__init__()
        self.y_min = y_min
        self.y_max = y_max
        distance_y = random.randint(y_min, y_max)
        pixelsInCm = WINDOW_WIDTH/((1.04743*distance_y)+0.334229)
        self.x_max = int((WINDOW_WIDTH/2) / pixelsInCm)
        self.z_max = int((WINDOW_HEIGHT/2) / pixelsInCm)
        self.distance = (random.randint(-self.x_max, self.x_max), distance_y, random.randint(-self.z_max, self.z_max))
        self.cmRadius = 2
        self.pxRadius = 0;

    def update(self, x_velocity, y_velocity, z_velocity, degree):

        pixelsInCm = WINDOW_WIDTH/((1.04743*self.distance[1])+0.334229)
        self.pxRadius = pixelsInCm * self.cmRadius
        sector_width = 2*(self.distance[1] + y_velocity)*(math.sin(math.radians(degree)/2))
        sector_height = self.distance[1]- math.sqrt((self.distance[1]*self.distance[1])-((sector_width/2)*(sector_width/2)))
        print(sector_width)
        print(sector_height)
        self.distance = (self.distance[0] + x_velocity-sector_width, self.distance[1] + y_velocity-sector_height, self.distance[2] + z_velocity)
        if (self.distance[1] > -5 and self.distance[1] < 5) and (self.distance[2] > -10 and self.distance[2] < 10) and (self.distance[0] > -10 and self.distance[0] < 10):
            print("DONE")
            self.distance = (random.randint(-self.x_max, self.x_max), random.randint(self.y_min, self.y_max), random.randint(-self.z_max, self.z_max))
    def draw(self, surface):
        pixelsInCm = WINDOW_WIDTH/((1.04743*self.distance[1])+0.334229)
        distance_x = (pixelsInCm * self.distance[0]) + WINDOW_WIDTH/2
        distance_y = (pixelsInCm * self.distance[2]) + WINDOW_HEIGHT/2
        pygame.draw.circle(surface, (255,0,0), (distance_x, distance_y), self.pxRadius)


pygame.init()

window = pygame.display.set_mode(WINDOW_SIZE)

circle = Circle(10, 100)

while True:
    #DRONE

    success, frame = cap.read()
    if not success:
        break

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    frame = cv2.flip(frame, 1)

    img_surface = pygame.surfarray.make_surface(frame)

    #END

    velocity = [0, 0, 0, 0]
    keys = pygame.key.get_pressed()
    if keys[pygame.K_RIGHT]:
        velocity[0] = 30
    elif keys[pygame.K_LEFT]:
        velocity[0] = -30
    if keys[pygame.K_UP]:
        velocity[1] = 30
    elif keys[pygame.K_DOWN]:
        velocity[1] = -30
    if keys[pygame.K_w]:
        velocity[2] = 30
    elif keys[pygame.K_s]:
        velocity[2] = -30
    if keys[pygame.K_d]:
        velocity[3] = 60
    elif keys[pygame.K_a]:
        velocity[3] = -60
    #DRONE
    drone.send_rc_control(velocity[0], velocity[1], velocity[2], velocity[3])
    #END
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            #DRONE
            cap.release()
            drone.land()
            #END
            sys.exit()
        #DRONE
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
            elif event.key == pygame.K_i:
                print(f'\nBattery: {drone.get_battery}\n')
        #END




    circle.update(-velocity[0]/30, -velocity[1]/10, -velocity[2]/30, velocity[3]/30)



    # Clear the window
    #window.fill((255, 255, 255))
    #circle.draw(window)

    #DRONE
    window.blit(img_surface, (0, 0))
    circle.draw(window)
    # END

    # Update the display
    pygame.display.update()
    clock.tick(60)

#DRONE
drone.land()
cap.release()
#END
