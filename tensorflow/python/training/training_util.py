# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Utility functions for training."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import os.path

from tensorflow.python.framework import ops
from tensorflow.python.lib.io import file_io
from tensorflow.python.ops import variables
from tensorflow.python.platform import tf_logging as logging


def global_step(sess, global_step_tensor):
  """Small helper to get the global step.

  ```python
  # Creates a variable to hold the global_step.
  global_step_tensor = tf.Variable(10, trainable=False, name='global_step')
  # Creates a session.
  sess = tf.Session()
  # Initializes the variable.
  print('global_step: %s' % tf.train.global_step(sess, global_step_tensor))

  global_step: 10
  ```

  Args:
    sess: A TensorFlow `Session` object.
    global_step_tensor:  `Output` or the `name` of the operation that contains
      the global step.

  Returns:
    The global step value.
  """
  return int(sess.run(global_step_tensor))


def get_global_step(graph=None):
  """Get the global step tensor.

  The global step tensor must be an integer variable. We first try to find it
  in the collection `GLOBAL_STEP`, or by name `global_step:0`.

  Args:
    graph: The graph to find the global step in. If missing, use default graph.

  Returns:
    The global step variable, or `None` if none was found.

  Raises:
    TypeError: If the global step tensor has a non-integer type, or if it is not
      a `Variable`.
  """
  graph = ops.get_default_graph() if graph is None else graph
  global_step_tensor = None
  global_step_tensors = graph.get_collection(ops.GraphKeys.GLOBAL_STEP)
  if len(global_step_tensors) == 1:
    global_step_tensor = global_step_tensors[0]
  elif not global_step_tensors:
    try:
      global_step_tensor = graph.get_tensor_by_name('global_step:0')
    except KeyError:
      return None
  else:
    logging.error('Multiple tensors in global_step collection.')
    return None

  assert_global_step(global_step_tensor)
  return global_step_tensor


def assert_global_step(global_step_tensor):
  """Asserts `global_step_tensor` is a scalar int `Variable` or `Output`.

  Args:
    global_step_tensor: `Output` to test.
  """
  if not (isinstance(global_step_tensor, variables.Variable) or
          isinstance(global_step_tensor, ops.Tensor)):
    raise TypeError(
        'Existing "global_step" must be a Variable or Tensor: %s.' %
        global_step_tensor)

  if not global_step_tensor.dtype.base_dtype.is_integer:
    raise TypeError('Existing "global_step" does not have integer type: %s' %
                    global_step_tensor.dtype)

  if global_step_tensor.get_shape().ndims != 0:
    raise TypeError('Existing "global_step" is not scalar: %s' %
                    global_step_tensor.get_shape())


def write_graph(graph_or_graph_def, logdir, name, as_text=True):
  """Writes a graph proto to a file.

  The graph is written as a binary proto unless `as_text` is `True`.

  ```python
  v = tf.Variable(0, name='my_variable')
  sess = tf.Session()
  tf.train.write_graph(sess.graph_def, '/tmp/my-model', 'train.pbtxt')
  ```

  or

  ```python
  v = tf.Variable(0, name='my_variable')
  sess = tf.Session()
  tf.train.write_graph(sess.graph, '/tmp/my-model', 'train.pbtxt')
  ```

  Args:
    graph_or_graph_def: A `Graph` or a `GraphDef` protocol buffer.
    logdir: Directory where to write the graph. This can refer to remote
      filesystems, such as Google Cloud Storage (GCS).
    name: Filename for the graph.
    as_text: If `True`, writes the graph as an ASCII proto.
  """
  if isinstance(graph_or_graph_def, ops.Graph):
    graph_def = graph_or_graph_def.as_graph_def()
  else:
    graph_def = graph_or_graph_def

  # gcs does not have the concept of directory at the moment.
  if not file_io.file_exists(logdir) and not logdir.startswith('gs:'):
    file_io.recursive_create_dir(logdir)
  path = os.path.join(logdir, name)
  if as_text:
    file_io.atomic_write_string_to_file(path, str(graph_def))
  else:
    file_io.atomic_write_string_to_file(path, graph_def.SerializeToString())
