import numpy as np
from scipy.spatial.transform import Rotation as R

def generate_grid(base, grid_x, grid_y, offset_x, offset_y, num_layers=1, layer_height=0):
    coords = []
    for layer in range(num_layers):
        z = base[2] + layer * layer_height
        for i in range(grid_y):
            for j in range(grid_x):
                x = base[0] + j * offset_x
                y = base[1] + i * offset_y
                coords.append([x, y, z])
    return coords

def retractionPick(pick_pos, pick_rot, dz_offset, seq='xyz'):
    pos = np.array(pick_pos)
    rotation = R.from_euler(seq, pick_rot, degrees=True)
    local_move_vector = np.array([0, 0, -dz_offset])
    global_move_vector = rotation.apply(local_move_vector)
    retract_pos = pos + global_move_vector
    return retract_pos.tolist()
