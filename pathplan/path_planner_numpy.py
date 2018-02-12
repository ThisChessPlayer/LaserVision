'''*-----------------------------------------------------------------------*---
                                                          Authors: Jason Ma
                                                          Date   : Feb 11, 2018
    File Name  : path_planner_numpy.py
    Description: Generates path waypoints using numpy. For all images/rasters,
                 it is important to note that this program treats axis 0 as y.
---*-----------------------------------------------------------------------*'''

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

import numpy as np
from PIL import Image
from math import hypot

'''[Config vars]------------------------------------------------------------'''
RASTER_FILE = "test.tif"
HEIGHT_TOL = 3
PATH_SPACING = 2

'''[gen_path]------------------------------------------------------------------
  Adjusts waypoints as necessary to place them over surface model in raster,
  and then interpolates values between raster.

  return - list of points in x,y,z coordinates representing waypoints
----------------------------------------------------------------------------'''
def gen_path(surface_raster, waypoints):

  #path_points = []
  x_points = []
  y_points = []
  z_points = []

  if len(waypoints) < 2:
    return path_points

  for i in range(len(waypoints) - 1):
    x, y, z = gen_segment(surface_raster, waypoints[i], waypoints[i + 1])
    x_points.extend(x)
    y_points.extend(y)
    z_points.extend(z)
    #path_points.extend(gen_segment(surface_raster, waypoints[i], waypoints[i + 1]))

  return x_points, y_points, z_points

'''[gen_segment]---------------------------------------------------------------
  Creates a segment from the x and y coordinates in the raster.

  return - list of x, y, z points interpolated between two waypoints
----------------------------------------------------------------------------'''
def gen_segment(surface_raster, wp0, wp1):
  src_x = wp0[0]
  src_y = wp0[1]

  dest_x = wp1[0]
  dest_y = wp1[1]

  delta_x = dest_x - src_x
  delta_y = dest_y - src_y
  seg_dist = hypot(delta_x, delta_y)

  # Find all points in between src and dest
  # This will be needed when smoothing based on heights!
  #cells = raster_line(wp0, wp1)

  curr_dist = 0
  x = src_x
  y = src_y

  x_points = []
  y_points = []
  z_points = []
  #points = []

  while curr_dist < seg_dist:
    # calculate avoid height (can also utilize bare earth model in future)
    avoid_height = HEIGHT_TOL

    # stay the designated height above the surface model
    x_points.append(x)
    y_points.append(y)
    z_points.append(surface_raster[int(y)][int(x)] + avoid_height)
    #points.append([x, y, surface_raster[int(y)][int(x)] + avoid_height])

    x += delta_x * PATH_SPACING / seg_dist
    y += delta_y * PATH_SPACING / seg_dist
    curr_dist += PATH_SPACING

  # calculate avoid height
  avoid_height = HEIGHT_TOL
  
  x_points.append(dest_x)
  y_points.append(dest_y)
  z_points.append(surface_raster[int(dest_y)][int(dest_x)] + avoid_height)
  #points.append([dest_x, dest_y, surface_raster[int(dest_y)][int(dest_x)] + avoid_height])

  return x_points, y_points, z_points

'''[raster_line]---------------------------------------------------------------
  Find all raster coordinates that are on path between two waypoints

  return - list of coordinates between two waypoints
----------------------------------------------------------------------------'''
def raster_line(wp0, wp1):

  # start and end coords
  src_x = wp0[0]
  src_y = wp0[1]

  dest_x = wp1[0]
  dest_y = wp1[1]

  # deltas
  dx = dest_x - src_x
  dy = dest_y - src_y

  # sign of movement
  sx = -1 if src_x > dest_x else 1
  sy = -1 if src_y > dest_y else 1

  dx = abs(dx)
  dy = abs(dy)
  
  points = []

  x = src_x
  y = src_y

  ix = 0
  iy = 0

  points.append([x, y])

  while ix < dx or iy < dy:
    # horizontal step
    if (ix + 0.5) / dx < (iy + 0.5) / dy:
      x += sx
      ix += 1
    # vertical step
    else:
      y += sy
      iy += 1
    points.append([x, y])

  return points
  

'''[read_tif]------------------------------------------------------------------
  Reads tif image into numpy array

  return - numpy array containing elevation map
----------------------------------------------------------------------------'''
def read_tif(filename):
  #image = Image.open(filename)
  #image = np.array(image)
  #image = plt.imread(filename)
  #i_w = image.shape[0]
  #i_h = image.shape[1]
  #image = image.flatten().reshape((i_w, i_h))
  image = Image.open(filename).convert('L')
  image = np.array(image)
  return image

'''[main]----------------------------------------------------------------------
  Drives program, reads image in, uses waypoints to generate path, and writes
  path to json file.
----------------------------------------------------------------------------'''
def main():
  image = read_tif(RASTER_FILE)

  waypoints = [(0, 100), (199, 199)]

  #plt.imshow(image)
  #plt.show()
  #print(image)
  #print(image.shape)
  x_points, y_points, z_points = gen_path(image, waypoints)
  
  fig = plt.figure()
  ax = fig.add_subplot(111, projection='3d')
  ax.plot(x_points, y_points, zs=z_points)
  plt.show()

  #print(raster_line([0,0], [1,7]))

if __name__ == '__main__':
  main()