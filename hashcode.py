#!/usr/bin/python2.7
import argparse
import sys
import warnings

import numpy as np
from scipy.spatial.distance import euclidean

# global string variable for final output
SOLUTION = ""

# free functions
# write to file
def append_command(action, drone, order_ware=None, type_p=None, num_p=1):
    """
    :param action:  'L', 'D', 'W'

    """

    global SOLUTION

    if action == 'W':
        new_command ="%s %s %s\n" % (str(drone), action, str(num_p))
    else:
        new_command ="%s %s %s %s %s\n" % ( str(drone), action, str(order_ware), str(type_p), str(num_p))

    SOLUTION += new_command

def operation_cost(position1, position2):
    """
    position = [x,y]
    """
    d = euclidean(position1, position2)

    return np.ceil(d) + 1


def read_input(file_name):
    """ Read input file """

    try :
        in_file = open(file_name, "r")
    except  IOError as (errno, strerror):
        print "I/O error({0}): {1}, {2}".format(errno, strerror, file_name)
        sys.exit()

    # The first section of the file describes the parameters of the
    # simulation. This section contains a single line containing the
    # following natural numbers separated by single spaces:
    # number of rows in the area of the simulation 
    # number of columns in the area of the simulation 
    # D number of drones available
    # deadline of the simulation
    #  maximum load of a drone
    line_one = in_file.readline()

    parameters = dict()

    # TODO check min and max fields
    keys = [ "rows", "columns", "drones", "deadline", "max_load" ]
    values = line_one.split()

    # FIXME check sizes
    for k, v in zip(keys, values):
        parameters[k] = int(v)

    # section two weights of the products available for orders
    num_products = int(in_file.readline())
    weights = in_file.readline().split(' ')
    weights = [ int(x) for x in weights ]
    if (num_products != len(weights)):
        warnings.warn('Invalid sizes in product lenghts {0}, {1}'.format(num_products, weights.len()))

    # section three warehouses and availability of individual product types
    # warehouse entry format [ [pos_x, pos_y], [products ] ]
    # TODO warehouse class
    num_warehouses = int(in_file.readline())
    warehouse_list = []

    for i in range(num_warehouses):
        warehouse_list.append([ [int(x) for x in in_file.readline().split(' ') ],
            [int(x) for x in in_file.readline().rstrip().split(' ')]])

    # order entry format [ [pos_x, pos_y], num_ordered_products, [ product list ] ]
    # TODO order class
    num_orders = int(in_file.readline().rstrip())
    order_list = []
    for i in range(num_orders):
        pos = [int(x) for x in in_file.readline().rstrip().split(' ') ]
        ordered_products = int(in_file.readline().rstrip())
        product_types = [ int(x) for x in in_file.readline().rstrip().split(' ')]
        order_list.append([pos, ordered_products, product_types])

    return parameters, weights, warehouse_list, order_list

def locate_product(product_id, warehouse_list):
    """
    Find a product in a warehouse
    """
    for i, w in enumerate(warehouse_list):
        if w[1][product_id] > 0:
            return i
    # always find article
    return -1

def locate_product_with_coord(parameters, weight_current_item, product_id, warehouse_list, src_pos, dst_pos, num_items):

    best_warehouse, min_distante = -1, sys.maxint

    max_w = parameters['max_load']

    for i, w in enumerate(warehouse_list):
        if w[1][product_id] >= num_items and max_w >= num_items*weight_current_item:
            current_dist = operation_cost(src_pos, w[0]) \
                    + operation_cost(w[0], dst_pos)
            if current_dist < min_distante:
                best_warehouse = i
                
	if best_warehouse > -1 and num_items > 1:
		print("Loading %dx%d weighting %d/%d" % (num_items,\
                        product_id, num_items*weight_current_item, parameters['max_load']))

    return best_warehouse

class Drone:

    def __init__(self, id, time_max, init_pos, weight=0.0):
        self.id = id
        self.position = init_pos
        self.weight = weight
        self.time_passed = 0
        self.time_max = time_max

    def process_article(self, type_p, w_dst, c_dst, warehouse_list, client_list, num_p=1):
        feasible = False

        c1 = operation_cost(warehouse_list[w_dst][0], self.position)

        c2 = operation_cost(client_list[c_dst][0], warehouse_list[w_dst][0])

        if self.time_passed + c1 + c2 < self.time_max:
            feasible = True
            self.time_passed += c1 + c2
            #load()
            warehouse_list[w_dst][1][type_p] -= num_p
            #deliver()
            self.position = client_list[c_dst][0]
            # update solution string
            append_command('L', self.id, order_ware=w_dst, type_p = type_p, num_p=num_p)
            append_command('D', self.id, order_ware=c_dst, type_p = type_p, num_p=num_p)

        return feasible
            

def main():

    global SOLUTION

    parser = argparse.ArgumentParser(description='hash code fun :)')
    parser.add_argument('infile', help='Destination file with extension')

    args = parser.parse_args()

    parameters, weights, warehouse_list, order_list = read_input(args.infile)

    NUM_DRONES = parameters['drones']
    INIT_POS = warehouse_list[0][0]
    TIME_MAX = parameters['deadline']

    # create drone list
    drone_list = []
    for drone_id in range(NUM_DRONES):
        drone_list += [Drone(id=drone_id, time_max = TIME_MAX, init_pos=INIT_POS)]

    # list of client and product pairs
    client_product_pairs = [ [x, y] for x in range(len(order_list)) for y in order_list[x][2]]

    ordered_client_product_pairs = sorted(client_product_pairs, key=lambda x: order_list[x[0]][1])

    num_commands = 0

    i = 0
    while i < len(ordered_client_product_pairs):
        order = ordered_client_product_pairs[i]
        c_id = order[0]
        product_id = order[1]

        # sort list by time_passed
        sorted_list = sorted(drone_list, key=lambda x:x.time_passed) # increasing

        # try to send multiple
        for j in range(i+1, len(ordered_client_product_pairs)):
            next_order = ordered_client_product_pairs[j]
            if next_order[0] != order[0] or next_order[1] != order[1]:
                break

        num_items_to_check = j - i
        num_items_sent = 0

        for k in range(num_items_to_check, 0, -1):
            processed=False
            for d in sorted_list:
                # find warehouse with article
                goal_w  = locate_product_with_coord(parameters, weights[product_id],
                                                    product_id, warehouse_list, d.position,
                                                    order_list[c_id][1], num_items=k)

                if goal_w == -1:
                    break

                # check whether drone d can load the articles
                processed = d.process_article(product_id, goal_w, c_id, warehouse_list, order_list, num_p=k)

                # if yes break
                if processed:
                    num_commands += 2
                    break

            if processed:
                num_items_sent = k
                break

        i += np.max([1, num_items_sent])

    with open(args.infile + '_solution_v6.txt', 'w') as f:
        f.write( str(num_commands) + '\n' + SOLUTION )


if __name__ == "__main__":
    main()
