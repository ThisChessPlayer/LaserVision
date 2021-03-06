'''
Contains all methods for evaluating the performance of a path
'''
import sys, time, os, struct, json, fnmatch
from pathplan.geo import load_shapefile, load_altfile
from shapely.geometry import LineString, Polygon
from shapely.strtree import STRtree
from scipy.interpolate import interp1d
from scipy.integrate import quad
import numpy as np
import json
"""
Utility functions to allow for computing MSE of expected and actual waypoints
of the path when running through simulation or in real time. This file also
includes functions to add noise to waypoints to test. For example, the
default noise function over a mean of 0 and a std of 1 will give a MSE of
around 1 usually.

NOTE: This file uses Generators, Lists, Numpy Arrays interchangely, but
will do conversions from generators to lists to numpy arrays if necessary.

NOTE: This code was written using Python 3 so Python 2 will probably cause
some errors with generators in this file.
"""

from mpl_toolkits.mplot3d import Axes3D

import matplotlib.pyplot as plt
import numpy as np
import json
import pyproj
import sys
import math

import types


'''
Returns a list of LineStrings indicating the sections of the
path that intersect with the digital surface map
'''
def calculate_intersections(path, rtree, alts, buf=0):
    intersected = []
    ls = LineString(path)
    tile = rtree.query(ls)
    for pot in tile:
        inter = pot.intersection(ls)
        if not inter.is_empty:
            alt = alts[inter.wkt] + buf
            for x,y,z in inter.coords:
                if z <= alt:
                    intersected.append(inter)
                    break
    return intersected
          

def generator_to_list(array):
    if isinstance(array, types.GeneratorType):
        return list(array)
    return array

def to_np_array(array):
    if not isinstance(array, np.ndarray):
        return np.array(array)
    return array

def read_path_from_json(filepath):
    """
    Parse a json file containing data points for a path. Expects the file
    to have mappings to `longitude`, `latitude`, and `altitude`
    Returns:
        A generator containing all parsed data points (x=lon, y=lat, z=alt)
    """
    X = "longitude"
    Y = "latitude"
    Z = "altitude"

    proj      = lambda pt: utm_proj(pt[X], pt[Y])
    cartesian = lambda pt: pyproj.transform(wgs84, proj(pt), pt[X], pt[Y], pt[Z])
    xyz       = lambda pt: np.array(*[cartesian(pt)])
    points = json.load(open(filepath))
    return map(xyz, points)

def default_noise(val=0):
    return val + np.random.normal(0, 1.5)

def gen_noise_points_static(waypoints, noise=lambda x: x + np.random.normal(0, 0.00005)):
    """
    Generates a new path by adding a static noise to all points in the
    original path; which is done via generator. This is the current
    preferred way to generate noisy points from our planned path.
    Args:
        waypoints - a list of waypoints with each point a np-array
    """
    for pt in waypoints:
        yield pt + noise(0)

def gen_noise_points(waypoints, noise=default_noise):
    """ [Deprecated]
    For each point in waypoints, generate a new line perpendicular to it
    using point[i] and point[i+1] as the line. Having this line, select
    randomly one of the nonzero values on this line and add it to the 
    original point[i] to generate a new point in space.
    """
    UP = np.array([0, 0, 1]) # altitude is stored in z-coordinate
    waypoints = map(np.array, waypoints)
    past_point = next(waypoints)

    for pt in waypoints:
        line = pt - past_point
        perpendicular = np.cross(line, UP)
        noise_line = perpendicular * noise()
        yield noise_line + past_point
        past_point = pt

    yield past_point


def norm(vec):
    return np.linalg.norm(vec)

def get_dist_between_points(points, scale=1):
    prev = None
    for pt in points:
        if prev is not None:
            yield norm(pt - prev) * scale
        prev = pt

def total_dist(path):
    return sum(get_dist_between_points(path))

def get_nearest_point_from(pt, list_of_points, set):
    # NOTE: Replace with octree/kd-tree for better performance in future:
    minlen = sys.float_info.max
    minval = None
    for other in list_of_points:
        if tuple(other) in set:
            continue

        length = norm(pt - other)
        if length < minlen:
            minlen = length
            minval = other

    return minval

def gen_path_via_nearest_points(planned, flown):
    used_pts = set()
    for pt in planned:
        found_pt = get_nearest_point_from(pt, flown, used_pts)
        used_pts.add(tuple(found_pt))
        yield found_pt


from pathplan.viz import build_distance_lists
def area_between_curves(first, second, max_dist=None):
    fx, fy = build_distance_lists(first)
    sx, sy = build_distance_lists(second)

    if max_dist == None:
        max_dist = min(fx[-1], sx[-1])

    f1 = interp1d(fx, fy)
    f2 = interp1d(sx, sy)

    farea, ferror = quad(f1, 0, max_dist)
    sarea, serror = quad(f2, 0, max_dist)

    return abs(farea - sarea)

    
    

def linear_interpolation(xs, ys):
    y_interp = interp1d(xs, ys)

    new_xs = np.arange(xs[0], xs[-1], abs(xs[0]-xs[-1]) / 1000)
    fake_ys = [y_interp(x) for x in new_xs]

    return new_xs, fake_ys
def mse(expected, actual):
    """
    Mean squared error of expected and actual waypoints.
    Args:
        expected - A list/generator/np-array of planned waypoints.
        actual - The list/generator/np-array of points that we flew to.
    Returns:
        The mean squared error
    """

    fx, fy = build_distance_lists(expected)
    sx, sy = build_distance_lists(actual)

    exp_interp = np.array(linear_interpolation(fx,fy))
    act_interp = np.array(linear_interpolation(sx,sy))

    return ((exp_interp - act_interp)**2).sum(axis=1) # avg along columns

def calc_errors_with_gen_noise(filepath, metric=mse):
    waypoints = list(read_path_from_json(filepath))
    noise_pts = list(gen_noise_points(waypoints))
    return metric(expected=waypoints, actual=noise_pts)

def get_individual_stats(name, path):
    return "len({0}) = {1}\n{0} total distance: {2}".format(name, len(path), total_dist(np.array(path)))

def get_comparison_stats(p1, p2, name1, name2, metrics=[("Area", area_between_curves), ("SSE", mse)]):
    vals = []
    for name, metric in metrics:
        val = metric(p1, p2)
        vals.append('{0} between {1} and {2} = {3}'.format(name, name1, name2,val))

    return '\n'.join(vals)
          
        

def print_comparison_info(planned, flown, name1="planned", name2="flown", metrics=[("Area", area_between_curves)]):
    planned = list(map(to_np_array, planned))
    flown = list(map(to_np_array, flown))
    print("Path Debug")
    print("  len({0}) = {1}".format(name1, len(planned)))
    print("  len({0}) = {1}".format(name2, len(flown)))
    print("  {0} Path Total distance: {1}".format(name1, total_dist(planned)))
    print("  {0} Path Total distance:   {1}".format(name2, total_dist(flown)))
    for name, metric in metrics:
        print("  Error based on {0} = {1}".format(name, metric(planned, flown)))

#def display_two_paths(one, two):
#    """
#    Args:
#        path_one - List of waypoints in format [(x, y, z), (x, y, z), ...]
#        path_two - List of waypoints in format [(x, y, z), (x, y, z), ...]
#    """
#    fig = plt.figure()
#    ax = fig.add_subplot(111, projection='3d')
#    ax.plot(*np.array(one).T, 'k-', color='b', linewidth=1.0)
#    ax.plot(*np.array(two).T, 'k-', color='r', linewidth=1.0)
#    plt.show()

def display_gen_noise_path_with_file(filepath):
    waypoints = list(read_path_from_json(filepath))
    noise_pts = list(gen_noise_points(waypoints))
    display_two_paths(waypoints, noise_pts)


def display_surface_with_file(filepath):
    """ 
    Displays a graph of the error surface between input path and a path 
    generated by adding some noise to the input path.

    Args:
        filepath - JSON file containing the path itself
    """
    waypoints = list(read_path_from_json(filepath))
    noise_pts = list(gen_noise_points_static(waypoints))

    display_surface(waypoints, noise_pts)


def main():
    planned = list(read_path_from_json("output/path.json"))
    flown = read_path_from_json("output/min_alt_2.flight.json")
    # NOTE: altitude in output/min_alt_2.flight.json adds 584
    flown = list(map(lambda xyz: np.array([xyz[0], xyz[1], xyz[2] - 584.0]), flown))
    flown = list(gen_path_via_nearest_points(planned, flown))

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    #ax.plot(*np.array(planned).T, 'o', color='b')
    plt.show()

    # print_planned_and_flown_path_debug_info(planned, flown)
    # display_surface(planned, flown)

    # p = list(read_path_from_json("output/path.json"))
    # flown = list(read_path_from_json("output/min_alt_2.flight.json"))
    # display_two_paths(p, flown)


# Uncomment to test
# if __name__ == "__main__":
#     main()
