from absl import logging
import tensorflow as tf


def vectorized_iou(clusters, detection):
  """Calculates the ious for box with each element of clusters."""
  x11, y11, x12, y12 = tf.split(clusters[:, 1:5], 4, axis=1)
  x21, y21, x22, y22 = tf.split(detection[1:5], 4)

  xA = tf.maximum(x11, x21)
  yA = tf.maximum(y11, y21)
  xB = tf.minimum(x12, x22)
  yB = tf.minimum(y12, y22)

  interArea = tf.maximum((xB - xA), 0) * tf.maximum((yB - yA), 0)

  boxAArea = (x12 - x11) * (y12 - y11)
  boxBArea = (x22 - x21) * (y22 - y21)

  iou = interArea / (boxAArea + boxBArea - interArea)

  return iou


def find_matching_cluster(clusters, detection):
  """Returns the index of the highest iou matching cluster for detection.  Returns -1 if no iou is higher than 0.55."""
  ious = vectorized_iou(tf.stack(clusters), detection)
  ious = tf.reshape(ious, [len(clusters)])
  if tf.math.reduce_max(ious) < 0.55:
    return -1
  return tf.argmax(ious)


def average_detections(detections):
  """Takes a list of detections and returns the average, both in box co-ordinates and confidence."""
  detections = tf.stack(detections)
  return [
      detections[0][0],
      tf.math.reduce_mean(detections[:, 1]),
      tf.math.reduce_mean(detections[:, 2]),
      tf.math.reduce_mean(detections[:, 3]),
      tf.math.reduce_mean(detections[:, 4]),
      tf.math.reduce_mean(detections[:, 5]),
      detections[0][6],
  ]


def ensemble_detections(params, detections):
  """Ensembles a group of detections by clustering the detections and returning the average of the clusters."""
  all_clusters = []

  for cid in range(params['num_classes']):
    indices = tf.where(tf.equal(detections[:, 6], cid))
    if indices.shape[0] == 0:
      continue
    class_detections = tf.gather_nd(detections, indices)

    clusters = [[class_detections[0]]]
    cluster_averages = [class_detections[0]]
    for d in class_detections[1:]:
      cluster_index = find_matching_cluster(cluster_averages, d)
      if cluster_index == -1:
        clusters.append([d])
        cluster_averages.append(d)
      else:
        clusters[cluster_index].append(d)
        cluster_averages[cluster_index] = average_detections(
            clusters[cluster_index])

    all_clusters.extend(cluster_averages)

  all_clusters.sort(reverse=True, key=lambda d: d[5])
  return tf.stack(all_clusters)
