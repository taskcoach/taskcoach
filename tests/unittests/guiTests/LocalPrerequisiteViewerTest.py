import unittest
from taskcoachlib.gui.dialog import editor
from taskcoachlib.gui import viewer


class LocalPrerequisiteViewerTest(unittest.TestCase):
    """Tests for the LocalPrerequisiteViewer class."""

    def test_has_snake_case_method(self):
        """Test that LocalPrerequisiteViewer has the snake_case method
        required by CheckTreeCtrl."""
        # The method should exist as a class attribute
        self.assertTrue(
            hasattr(editor.LocalPrerequisiteViewer, 'get_item_parent_has_exclusive_children'),
            "LocalPrerequisiteViewer should have get_item_parent_has_exclusive_children method"
        )

    def test_snake_case_method_is_same_as_camel_case(self):
        """Test that the snake_case method is the same as camelCase method."""
        # The method should be the same as getItemParentHasExclusiveChildren
        self.assertEqual(
            editor.LocalPrerequisiteViewer.get_item_parent_has_exclusive_children,
            viewer.CheckableTaskViewer.getItemParentHasExclusiveChildren
        )


if __name__ == '__main__':
    unittest.main()
