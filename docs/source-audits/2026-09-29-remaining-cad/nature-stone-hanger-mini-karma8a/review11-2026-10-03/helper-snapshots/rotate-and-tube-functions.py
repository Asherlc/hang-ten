def rotate(q, points):
    # Retained inverse helper with conjugate gives body -> world conversion.
    inverse = [-q[0], -q[1], -q[2], q[3]]
    return rotate_inverse(inverse, np.asarray(points))

def tube_triangles(path, radius):
    triangles = []
    for start, end in zip(path[:-1], path[1:]):
        direction = end - start
        length = np.linalg.norm(direction)
        if length <= 1e-12:
            raise ValueError("adjacent route points coincide")
        direction /= length
        seed = np.eye(3)[np.argmin(np.abs(direction))]
        first = np.cross(direction, seed)
        first /= np.linalg.norm(first)
        second = np.cross(direction, first)
        angles = np.arange(12) * (2 * np.pi / 12)
        offsets = radius * (np.cos(angles)[:, None] * first + np.sin(angles)[:, None] * second)
        a, b = start + offsets, end + offsets
        for i in range(12):
            n = (i + 1) % 12
            triangles.extend([[a[i], a[n], b[i]], [a[n], b[n], b[i]]])
    return np.asarray(triangles)
