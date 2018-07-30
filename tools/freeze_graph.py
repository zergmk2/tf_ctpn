"""
bazel-bin/tensorflow/tools/graph_transforms/transform_graph \
        --in_graph=/home/cwq/code/tf_ctpn/model/ctpn.pb \
        --out_graph=/home/cwq/code/tf_ctpn/model/ctpn_optimized.pb \
        --inputs='input' \
        --outputs='vgg_16_1/rpn_bbox_pred/Conv2D,vgg_16_1/rpn_cls_score_reshape' \
        --transforms='
        strip_unused_nodes(name=inputs, type_for_name=float, shape_for_name="1,-1,-1,3")
        remove_nodes(op=Identity, op=CheckNumerics)
        fold_constants(ignore_errors=true)
        fold_batch_norms
        fold_old_batch_norms'
"""

import tensorflow as tf
import argparse
import os
import sys


def main(args):
    with tf.Graph().as_default():
        with tf.Session() as sess:
            # Load the model metagraph and checkpoint
            print('Model directory: %s' % args.ckpt_dir)
            meta_file, ckpt_file = get_model_filenames(args.ckpt_dir)

            print('Metagraph file: %s' % meta_file)
            print('Checkpoint file: %s' % ckpt_file)

            saver = tf.train.import_meta_graph(meta_file, clear_devices=True)
            tf.get_default_session().run(tf.global_variables_initializer())
            tf.get_default_session().run(tf.local_variables_initializer())
            saver.restore(sess, ckpt_file)

            input_graph_def = tf.get_default_graph().as_graph_def()

            # Print all node name in graph
            # for node in input_graph_def.node:
            #     print(node.name)

            output_node_names = ['RPN/rpn_bbox_pred/Conv2D', 'RPN/rpn_cls_score_reshape']

            # We use a built-in TF helper to export variables to constants
            output_graph_def = tf.graph_util.convert_variables_to_constants(
                sess,  # The session is used to retrieve the weights
                input_graph_def,  # The graph_def is used to retrieve the nodes
                output_node_names  # The output node names are used to select the usefull nodes
            )

            # Serialize and dump the output graph to the filesystem
            with tf.gfile.GFile(args.output_file, 'wb') as f:
                f.write(output_graph_def.SerializeToString())
                pb_file_size = f.size() / 1024. / 1024.
            print("%d ops in the final graph: %s, size: %d mb" %
                  (len(output_graph_def.node), args.output_file, pb_file_size))


def get_model_filenames(model_dir):
    ckpt = tf.train.get_checkpoint_state(model_dir)
    if ckpt and ckpt.model_checkpoint_path:
        ckpt_file_basename = os.path.basename(ckpt.model_checkpoint_path)
        meta_file = os.path.join(model_dir, ckpt_file_basename + '.meta')
        return meta_file, ckpt.model_checkpoint_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--ckpt_dir', type=str, default='./checkpoint/crnn',
                        help='Directory containing the metagraph (.meta) file and the checkpoint (ckpt) file containing model parameters')

    parser.add_argument('--output_file', type=str, default='./model/ctpn.pb',
                        help='Filename for the exported graphdef protobuf (.pb)')

    args, _ = parser.parse_known_args()

    output_dir = os.path.dirname(args.output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    main(args)
