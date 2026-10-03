def rotate_inverse(quaternion, vector):
    xyz = -np.asarray(quaternion[:3], dtype=float)
    turn = 2 * np.cross(xyz, vector)
    return vector + quaternion[3] * turn + np.cross(xyz, turn)
