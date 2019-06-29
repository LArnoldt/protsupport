import numpy as np
import torch

def compute_dihedral_angle(a, b, c):
  c1 = np.cross(a, b)
  c2 = np.cross(b, c)
  b0 = b / np.linalg.norm(b)
  return np.arctan2(np.cross(c1, c2).dot(b0), c1.dot(c2))

def _assign_psea_aux(distances, dihedral, angle,
                     distance_spec, dihedral_spec, angle_spec):
  good = True
  for idx in range(3):
    target, area = distance_spec[idx]
    fits = target - area < distances[idx + 2] < target + area
    good = good and fits
  target, area = dihedral_spec
  left = ((target - area) + 180) % 360 / 180 * np.pi
  right = ((target + area) + 180) % 360 / 180 * np.pi
  good = good and left < dihedral < right
  target, area = dihedral_spec
  left = ((target - area) + 180) % 360 / 180 * np.pi
  right = ((target + area) + 180) % 360 / 180 * np.pi
  good = good and left < dihedral < right
  return good

def assign_psea(positions):
  offsets = positions[:, 1:] - positions[:, :-1]
  distances = np.linalg.norm(positions[:, :1] - positions, axis=0)
  dihedral = compute_dihedral_angle(*offsets[:-1])
  angle = vector_angle(-offsets[0], offsets[1])

  helix_angle = (89, 12)
  sheet_angle = (124, 14)

  helix_dihedral = (50, 20)
  sheet_dihedral = (-170, 45)

  helix_distances = ((5.5, 0.5), (5.3, 0.5), (6.4, 0.6))
  sheet_distances = ((6.7, 0.6), (9.9, 0.9), (12.4, 1.1))

  is_helix = _assign_psea_aux(
    distances, dihedral, angle,
    helix_distances, helix_dihedral, helix_angle
  )
  if is_helix:
    return np.array([1, 0, 0])

  is_sheet = _assign_psea_aux(
    distances, dihedral, angle,
    sheet_distances, sheet_dihedral, sheet_angle
  )
  if is_sheet:
    return np.array([0, 1, 0])
  return np.array([0, 0, 1])

def compute_rotation_matrix(axis, angle):
  axis = axis / np.linalg.norm(axis)
  matrix = np.array([
    [0, -axis[2], axis[1]],
    [0, 0, -axis[0]],
    [0, 0, 0]
  ])
  matrix = matrix - matrix.T
  rot = np.eye(3) + np.sin(angle) * matrix + (1 - np.cos(angle)) * (matrix @ matrix)
  return rot

def compute_rotation(vector, axis, angle):
  rot = compute_rotation_matrix(axis, angle)
  return rot @ vector

def vector_angle(v1, v2):
  v1 = v1 / np.linalg.norm(v1)
  v2 = v2 / np.linalg.norm(v2)
  dot = np.dot(v1, v2)
  cross = np.linalg.norm(np.cross(v1, v2))
  return np.arctan2(cross, dot)

def orientation(positions):
  u = positions[:, 1:] - positions[:, :-1]
  u = u / (np.linalg.norm(u, axis=0) + 1e-6)
  b = u[:, :-1] - u[:, 1:]
  b = b / (np.linalg.norm(b, axis=0) + 1e-6)
  n = np.cross(u[:, :-1].T, u[:, 1:].T).T
  n = n / (np.linalg.norm(n, axis=0) + 1e-6)
  bxn = np.cross(b.T, n.T).T

  b_edge = np.array([1, 0, 0]).reshape(3, 1)
  n_edge = np.array([0, 1, 0]).reshape(3, 1)
  bxn_edge = np.array([0, 0, 1]).reshape(3, 1)
  edge = np.concatenate((b_edge, n_edge, bxn_edge), axis=0)

  result = np.concatenate((b, n, bxn), axis=0)
  result = np.concatenate((edge, result, edge), axis=1)
  result = result.reshape(3, 3, -1)
  if np.isnan(result).any(): print("bad result")

  return result

def matrix_to_quaternion(matrix):
  if isinstance(matrix, torch.Tensor):
    w = torch.sqrt(1.0 + matrix[:, 0, 0] + matrix[:, 1, 1] + matrix[:, 2, 2]) / 2.0
    w4 = (4.0 * w)
    x = (matrix[:, 2, 1] - matrix[:, 1, 2]) / (w4 + 1e-6)
    y = (matrix[:, 0, 2] - matrix[:, 2, 0]) / (w4 + 1e-6)
    z = (matrix[:, 1, 0] - matrix[:, 0, 1]) / (w4 + 1e-6)
    return torch.cat([w[:, None], x[:, None], y[:, None], z[:, None]], dim=1)
  else:
    w = np.sqrt(1.0 + matrix[0, 0] + matrix[1, 1] + matrix[2, 2]) / 2.0
    w4 = (4.0 * w)
    x = (matrix[2, 1] - matrix[1, 2]) / w4
    y = (matrix[0, 2] - matrix[2, 0]) / w4
    z = (matrix[1, 0] - matrix[0, 1]) / w4
    return np.array([w, x, y, z])

def _np_relative_orientation(x, y, x_o, y_o):
  offset = y - x
  distance = np.linalg.norm(offset, axis=0)
  direction = x_o.T @ (offset / distance)
  direction[:, distance == 0.0] = 0
  rotation = matrix_to_quaternion(x_o.T @ y_o)
  return distance, direction, rotation

def _torch_neighbourhood_relative_orientation(x, y, x_o, y_o):
  offset = y - x[None]
  distance = torch.norm(offset, dim=1, keepdim=True)
  direction = (offset / (distance + 1e-6)) @ x_o
  direction[(distance == 0).view(-1)] = 0
  rotation = matrix_to_quaternion(x_o @ y_o)
  if torch.isnan(distance).any(): print("bad distance")
  if torch.isnan(direction).any(): print("bad direction")
  if torch.isnan(rotation).any(): print("bad rotation")
  return distance, direction, rotation

def _torch_batch_relative_orientation(x, y, x_o, y_o):
  offset = y - x
  distance = torch.norm(offset, dim=1, keepdim=True)
  direction = x_o @ (offset / (distance + 1e-6)).unsqueeze(-1)
  direction[(distance == 0).view(-1)] = 0
  rotation = matrix_to_quaternion(x_o @ y_o)
  return distance, direction.squeeze(), rotation

def relative_orientation(x, y, x_o, y_o):
  if isinstance(x, torch.Tensor):
    if x.dim() != y.dim():
      return _torch_neighbourhood_relative_orientation(x, y, x_o, y_o)
    return _torch_batch_relative_orientation(x, y, x_o, y_o)
  return _np_relative_orientation(x, y, x_o, y_o)
