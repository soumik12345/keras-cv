# Copyright 2022 The KerasCV Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import numpy as np
import tensorflow as tf

from keras_cv import bounding_box
from keras_cv.layers.preprocessing.base_image_augmentation_layer import (
    BaseImageAugmentationLayer,
)


class RandomAddLayer(BaseImageAugmentationLayer):
    def __init__(self, value_range=(0.0, 1.0), fixed_value=None, **kwargs):
        super().__init__(**kwargs)
        self.value_range = value_range
        self.fixed_value = fixed_value

    def get_random_transformation(self, **kwargs):
        if self.fixed_value:
            return self.fixed_value
        return self._random_generator.random_uniform(
            [], minval=self.value_range[0], maxval=self.value_range[1]
        )

    def augment_image(self, image, transformation, **kwargs):
        return image + transformation

    def augment_label(self, label, transformation, **kwargs):
        return label + transformation

    def augment_bounding_boxes(self, bounding_boxes, transformation, **kwargs):
        return {
            "boxes": bounding_boxes["boxes"] + transformation,
            "classes": bounding_boxes["classes"] + transformation,
        }

    def augment_keypoints(self, keypoints, transformation, **kwargs):
        return keypoints + transformation

    def augment_segmentation_mask(
        self, segmentation_mask, transformation, **kwargs
    ):
        return segmentation_mask + transformation


class VectorizeDisabledLayer(BaseImageAugmentationLayer):
    def __init__(self, **kwargs):
        self.auto_vectorize = False
        super().__init__(**kwargs)


class BaseImageAugmentationLayerTest(tf.test.TestCase):
    def test_augment_single_image(self):
        add_layer = RandomAddLayer(fixed_value=2.0)
        image = np.random.random(size=(8, 8, 3)).astype("float32")
        output = add_layer(image)

        self.assertAllClose(image + 2.0, output)

    def test_augment_dict_return_type(self):
        add_layer = RandomAddLayer(fixed_value=2.0)
        image = np.random.random(size=(8, 8, 3)).astype("float32")
        output = add_layer({"images": image})

        self.assertIsInstance(output, dict)

    def test_augment_casts_dtypes(self):
        add_layer = RandomAddLayer(fixed_value=2.0)
        images = tf.ones((2, 8, 8, 3), dtype="uint8")
        output = add_layer(images)

        self.assertAllClose(
            tf.ones((2, 8, 8, 3), dtype="float32") * 3.0, output
        )

    def test_augment_batch_images(self):
        add_layer = RandomAddLayer()
        images = np.random.random(size=(2, 8, 8, 3)).astype("float32")
        output = add_layer(images)

        diff = output - images
        # Make sure the first image and second image get different augmentation
        self.assertNotAllClose(diff[0], diff[1])

    def test_augment_image_and_label(self):
        add_layer = RandomAddLayer(fixed_value=2.0)
        image = np.random.random(size=(8, 8, 3)).astype("float32")
        label = np.random.random(size=(1,)).astype("float32")

        output = add_layer({"images": image, "targets": label})
        expected_output = {"images": image + 2.0, "targets": label + 2.0}
        self.assertAllClose(output, expected_output)

    def test_augment_image_and_target(self):
        add_layer = RandomAddLayer(fixed_value=2.0)
        image = np.random.random(size=(8, 8, 3)).astype("float32")
        label = np.random.random(size=(1,)).astype("float32")

        output = add_layer({"images": image, "targets": label})
        expected_output = {"images": image + 2.0, "targets": label + 2.0}
        self.assertAllClose(output, expected_output)

    def test_augment_batch_images_and_targets(self):
        add_layer = RandomAddLayer()
        images = np.random.random(size=(2, 8, 8, 3)).astype("float32")
        targets = np.random.random(size=(2, 1)).astype("float32")
        output = add_layer({"images": images, "targets": targets})

        image_diff = output["images"] - images
        label_diff = output["targets"] - targets
        # Make sure the first image and second image get different augmentation
        self.assertNotAllClose(image_diff[0], image_diff[1])
        self.assertNotAllClose(label_diff[0], label_diff[1])

    def test_augment_leaves_extra_dict_entries_unmodified(self):
        add_layer = RandomAddLayer(fixed_value=0.5)
        images = np.random.random(size=(8, 8, 3)).astype("float32")
        image_timestamp = np.array(123123123)
        inputs = {"images": images, "image_timestamp": image_timestamp}
        _ = add_layer(inputs)

    def test_augment_ragged_images(self):
        images = tf.ragged.stack(
            [
                np.random.random(size=(8, 8, 3)).astype("float32"),
                np.random.random(size=(16, 8, 3)).astype("float32"),
            ]
        )
        add_layer = RandomAddLayer(fixed_value=0.5)
        result = add_layer(images)
        self.assertAllClose(images + 0.5, result)
        # TODO(lukewood): unit test

    def test_augment_image_and_localization_data(self):
        add_layer = RandomAddLayer(fixed_value=2.0)
        images = np.random.random(size=(8, 8, 3)).astype("float32")
        bounding_boxes = {
            "boxes": np.random.random(size=(8, 3, 4)).astype("float32"),
            "classes": np.random.random(size=(8, 3)).astype("float32"),
        }
        keypoints = np.random.random(size=(8, 5, 2)).astype("float32")
        segmentation_mask = np.random.random(size=(8, 8, 1)).astype("float32")

        output = add_layer(
            {
                "images": images,
                "bounding_boxes": bounding_boxes,
                "keypoints": keypoints,
                "segmentation_masks": segmentation_mask,
            }
        )
        expected_output = {
            "images": images + 2.0,
            "bounding_boxes": bounding_box.to_dense(
                {
                    "boxes": bounding_boxes["boxes"] + 2.0,
                    "classes": bounding_boxes["classes"] + 2.0,
                }
            ),
            "keypoints": keypoints + 2.0,
            "segmentation_masks": segmentation_mask + 2.0,
        }

        output["bounding_boxes"] = bounding_box.to_dense(
            output["bounding_boxes"]
        )

        self.assertAllClose(output["images"], expected_output["images"])
        self.assertAllClose(output["keypoints"], expected_output["keypoints"])
        self.assertAllClose(
            output["bounding_boxes"]["boxes"],
            expected_output["bounding_boxes"]["boxes"],
        )
        self.assertAllClose(
            output["bounding_boxes"]["classes"],
            expected_output["bounding_boxes"]["classes"],
        )
        self.assertAllClose(
            output["segmentation_masks"], expected_output["segmentation_masks"]
        )

    def test_augment_batch_image_and_localization_data(self):
        add_layer = RandomAddLayer()
        images = np.random.random(size=(2, 8, 8, 3)).astype("float32")
        bounding_boxes = {
            "boxes": np.random.random(size=(2, 3, 4)).astype("float32"),
            "classes": np.random.random(size=(2, 3)).astype("float32"),
        }
        keypoints = np.random.random(size=(2, 3, 5, 2)).astype("float32")
        segmentation_masks = np.random.random(size=(2, 8, 8, 1)).astype(
            "float32"
        )

        output = add_layer(
            {
                "images": images,
                "bounding_boxes": bounding_boxes,
                "keypoints": keypoints,
                "segmentation_masks": segmentation_masks,
            }
        )

        bounding_boxes_diff = (
            output["bounding_boxes"]["boxes"] - bounding_boxes["boxes"]
        )
        keypoints_diff = output["keypoints"] - keypoints
        segmentation_mask_diff = (
            output["segmentation_masks"] - segmentation_masks
        )
        self.assertNotAllClose(bounding_boxes_diff[0], bounding_boxes_diff[1])
        self.assertNotAllClose(keypoints_diff[0], keypoints_diff[1])
        self.assertNotAllClose(
            segmentation_mask_diff[0], segmentation_mask_diff[1]
        )

    def test_augment_all_data_in_tf_function(self):
        add_layer = RandomAddLayer()
        images = np.random.random(size=(2, 8, 8, 3)).astype("float32")
        bounding_boxes = bounding_boxes = {
            "boxes": np.random.random(size=(2, 3, 4)).astype("float32"),
            "classes": np.random.random(size=(2, 3)).astype("float32"),
        }
        keypoints = np.random.random(size=(2, 5, 2)).astype("float32")
        segmentation_masks = np.random.random(size=(2, 8, 8, 1)).astype(
            "float32"
        )

        @tf.function
        def in_tf_function(inputs):
            return add_layer(inputs)

        output = in_tf_function(
            {
                "images": images,
                "bounding_boxes": bounding_boxes,
                "keypoints": keypoints,
                "segmentation_masks": segmentation_masks,
            }
        )

        bounding_boxes_diff = (
            output["bounding_boxes"]["boxes"] - bounding_boxes["boxes"]
        )
        keypoints_diff = output["keypoints"] - keypoints
        segmentation_mask_diff = (
            output["segmentation_masks"] - segmentation_masks
        )
        self.assertNotAllClose(bounding_boxes_diff[0], bounding_boxes_diff[1])
        self.assertNotAllClose(keypoints_diff[0], keypoints_diff[1])
        self.assertNotAllClose(
            segmentation_mask_diff[0], segmentation_mask_diff[1]
        )
