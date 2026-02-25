#! /usr/bin/env python
import wx, wx.lib


TimeLineSelectionEvent, EVT_TIMELINE_SELECTED = wx.lib.newevent.NewEvent()
TimeLineActivationEvent, EVT_TIMELINE_ACTIVATED = wx.lib.newevent.NewEvent()


class HotMap(object):
    """Keep track of which node is where."""

    def __init__(self, parent=None):
        self.parent = parent
        self.nodes = []
        self.rects = {}
        self.children = {}
        super().__init__()

    def append(self, node, rect):
        self.nodes.append(node)
        self.rects[node] = rect
        self.children[node] = HotMap(node)

    def __getitem__(self, node):
        return self.children[node]

    def find_node_at_position(self, position, parent=None):
        """Retrieve the node at the given position."""
        for node, rect in list(self.rects.items()):
            if rect.Contains(position):
                return self[node].find_node_at_position(position, node)
        return parent

    def first_node(self):
        return self.nodes[0] if self.nodes else None

    def last_node(self, parent=None):
        if self.nodes:
            last = self.nodes[-1]
            return self[last].last_node(last)
        else:
            return parent

    def find_node(self, target):
        if target in self.nodes:
            return self
        for node in self.nodes:
            result = self[node].find_node(target)
            if result:
                return result
        return None

    def next_child(self, target):
        index = self.nodes.index(target)
        index = min(index + 1, len(self.nodes) - 1)
        return self.nodes[index]

    def previous_child(self, target):
        index = self.nodes.index(target)
        index = max(index - 1, 0)
        return self.nodes[index]

    def first_child(self, target):
        children = self[target].nodes
        if children:
            return children[0]
        else:
            return target


class TimeLine(wx.Panel):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop("model", [])
        self.padding = kwargs.pop("padding", 3)
        self.adapter = kwargs.pop("adapter", DefaultAdapter())
        self.selected_node = None
        self.background_colour = wx.WHITE
        self._buffer = wx.Bitmap(20, 20)  # Have a default buffer ready
        self.DEFAULT_PEN = wx.Pen(wx.BLACK, 1, wx.SOLID)
        self.SELECTED_PEN = wx.Pen(wx.WHITE, 2, wx.SOLID)
        kwargs["style"] = (
            wx.TAB_TRAVERSAL
            | wx.NO_BORDER
            | wx.FULL_REPAINT_ON_RESIZE
            | wx.WANTS_CHARS
        )
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEFT_UP, self.OnClickRelease)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.OnSize(None)

    def SetBackgroundColour(self, colour):
        self.background_colour = colour

    def Refresh(self):
        self.UpdateDrawing()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self._buffer)

    def OnSize(self, event):
        # The buffer is initialized in here, so that the buffer is always
        # the same size as the Window.
        width, height = self.GetClientSize()
        if width <= 0 or height <= 0:
            return
        # Make new off-screen bitmap: this bitmap will always have the
        # current drawing in it, so it can be used to save the image to
        # a file, or whatever.
        self._buffer = wx.Bitmap(width, height)
        self.UpdateDrawing()

    def OnClickRelease(self, event):
        event.Skip()
        self.SetFocus()
        point = event.GetPosition()
        node = self.hot_map.find_node_at_position(point)
        self.SetSelected(node, point)

    def OnDoubleClick(self, event):
        point = event.GetPosition()
        node = self.hot_map.find_node_at_position(point)
        if node:
            wx.PostEvent(self, TimeLineActivationEvent(node=node, point=point))

    def OnKeyUp(self, event):
        event.Skip()
        if not self.hot_map:
            return
        if event.KeyCode == wx.WXK_HOME:
            self.SetSelected(self.hot_map.first_node())
            return
        elif event.KeyCode == wx.WXK_END:
            self.SetSelected(self.hot_map.last_node())
            return
        if not self.selected_node:
            return
        if event.KeyCode == wx.WXK_RETURN:
            wx.PostEvent(self, TimeLineActivationEvent(node=self.selected_node))
            return
        hot_map = self.hot_map.find_node(self.selected_node)
        if hot_map is None:
            newSelection = self.hot_map.first_node()
        elif event.KeyCode == wx.WXK_DOWN:
            newSelection = hot_map.next_child(self.selected_node)
        elif event.KeyCode == wx.WXK_UP:
            newSelection = hot_map.previous_child(self.selected_node)
        elif event.KeyCode == wx.WXK_RIGHT:
            newSelection = hot_map.first_child(self.selected_node)
        elif event.KeyCode == wx.WXK_LEFT and hot_map.parent:
            newSelection = hot_map.parent
        else:
            newSelection = self.selected_node
        self.SetSelected(newSelection)

    def GetSelected(self):
        return self.selected_node

    def SetSelected(self, node, point=None):
        """Set the given node selected in the timeline widget"""
        if node == self.selected_node:
            return
        self.selected_node = node
        self.Refresh()
        if node:
            wx.PostEvent(self, TimeLineSelectionEvent(node=node, point=point))

    def UpdateDrawing(self):
        dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
        self.Draw(dc)

    def Draw(self, dc):
        """Draw the timeline on the device context."""
        self.hot_map = HotMap()
        brush = wx.Brush(self.background_colour)
        dc.SetBackground(brush)
        dc.Clear()
        dc.SetFont(self.font_for_labels(dc))
        if self.model:
            bounds = self.adapter.bounds(self.model)
            self.min_start = float(min(bounds))
            self.max_stop = float(max(bounds))
            if self.max_stop - self.min_start < 100:
                self.max_stop += 100
            self.length = self.max_stop - self.min_start
            self.width, self.height = dc.GetSize()
            labelHeight = (
                dc.GetTextExtent("ABC")[1] + 2
            )  # Leave room for time labels
            self.draw_parallel_children(
                dc,
                self.model,
                labelHeight,
                self.height - labelHeight,
                self.hot_map,
            )
            self.draw_now(dc)

    def font_for_labels(self, dc):
        """Return the default GUI font, scaled for printing if necessary."""
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        scale = dc.GetPPI()[0] / wx.ScreenDC().GetPPI()[0]
        font.SetPointSize(int(scale * font.GetPointSize()))
        return font

    def draw_box(
        self, dc, node, y, h, hot_map, is_sequential_node=False, depth=0
    ):
        if h < self.padding:
            return
        start, stop = self.adapter.start(node), self.adapter.stop(node)
        if start is None:
            start = self.min_start - 10
        if stop is None:
            stop = self.max_stop + 10
        start, stop = min(start, stop), max(start, stop)  # Sanitize input
        x = self.scale_x(start) + 2 * depth
        w = self.scale_width(stop - start) - 4 * depth
        hot_map.append(node, (wx.Rect(int(x), int(y), int(w), int(h))))
        self.draw_rectangle(dc, node, x, y, w, h, is_sequential_node, depth)
        if not is_sequential_node:
            self.draw_icon_and_label(dc, node, x, y, w, h, depth)
            seqHeight = min(dc.GetTextExtent("ABC")[1] + 2, h)
            self.draw_sequential_children(
                dc, node, y + 2, seqHeight - 4, hot_map[node], depth + 1
            )
            self.draw_parallel_children(
                dc,
                node,
                y + seqHeight,
                h - seqHeight,
                hot_map[node],
                depth + 1,
            )

    def draw_rectangle(self, dc, node, x, y, w, h, is_sequential_node, depth):
        dc = wx.GCDC(dc) if is_sequential_node else dc
        dc.SetClippingRegion(x, y, w, h)
        dc.SetBrush(self.brush_for_node(node, is_sequential_node, depth))
        dc.SetPen(self.pen_for_node(node, is_sequential_node, depth))
        rounding = (
            0
            if is_sequential_node
            and (h < self.padding * 4 or w < self.padding * 4)
            else self.padding * 2
        )
        dc.DrawRoundedRectangle(x, y, w, h, rounding)
        dc.DestroyClippingRegion()

    def draw_icon_and_label(self, dc, node, x, y, w, h, depth):
        """Draw the icon, if any, and the label, if any, of the node."""
        # Make sure the Icon and Label are visible:
        if x < 0:
            w -= abs(x)
            x = 0
        dc.SetClippingRegion(
            x + 1, y + 1, w - 2, h - 2
        )  # Don't draw outside the box
        wx_icon = self.adapter.get_wx_icon(node, node == self.selected_node)
        if wx_icon and h >= wx_icon.GetHeight() and w >= wx_icon.GetWidth():
            icon_width = wx_icon.GetWidth() + 2
            dc.DrawIcon(wx_icon, x + 2, y + 2)
        else:
            icon_width = 0
        if h >= dc.GetTextExtent("ABC")[1]:
            dc.SetFont(self.font_for_node(dc, node, depth))
            dc.SetTextForeground(self.text_foreground_for_node(node, depth))
            dc.DrawText(self.adapter.label(node), x + icon_width + 2, y + 2)
        dc.DestroyClippingRegion()

    def draw_parallel_children(self, dc, parent, y, h, hot_map, depth=0):
        children = self.adapter.parallel_children(parent)
        if not children:
            return
        childY = y
        h -= len(children)  # vertical space between children
        recursiveChildrenList = [
            self.adapter.parallel_children(child, recursive=True)
            for child in children
        ]
        recursiveChildrenCounts = [
            len(recursiveChildren)
            for recursiveChildren in recursiveChildrenList
        ]
        recursiveChildHeight = h // (
            len(children) + sum(recursiveChildrenCounts)
        )
        for child, numberOfRecursiveChildren in zip(
            children, recursiveChildrenCounts
        ):
            childHeight = recursiveChildHeight * (
                numberOfRecursiveChildren + 1
            )
            if childHeight >= self.padding:
                self.draw_box(
                    dc, child, childY, childHeight, hot_map, depth=depth
                )
            childY += childHeight + 1

    def draw_sequential_children(self, dc, parent, y, h, hot_map, depth=0):
        for child in self.adapter.sequential_children(parent):
            self.draw_box(
                dc, child, y, h, hot_map, is_sequential_node=True, depth=depth
            )

    def draw_now(self, dc):
        alpha_dc = wx.GCDC(dc)
        alpha_dc.SetPen(wx.Pen(wx.Colour(128, 200, 128, 128), width=3))
        now = self.scale_x(self.adapter.now())
        alpha_dc.DrawLine(now, 0, now, self.height)
        label = self.adapter.nowlabel()
        textWidth = alpha_dc.GetTextExtent(label)[0]
        alpha_dc.DrawText(label, now - (textWidth // 2), 0)

    def scale_x(self, x):
        return self.scale_width(x - self.min_start)

    def scale_width(self, width):
        return int((width / self.length) * self.width)

    def text_foreground_for_node(self, node, depth=0):
        """Determine the text foreground color to use to display the label of
        the given node"""
        if node == self.selected_node:
            fg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            fg_color = self.adapter.foreground_color(node, depth)
            if not fg_color:
                fg_color = wx.SystemSettings.GetColour(
                    wx.SYS_COLOUR_WINDOWTEXT
                )
        return fg_color

    def font_for_node(self, dc, node, depth=0):
        """Determine the font to use to display the label of the given node,
        scaled for printing if necessary."""
        font = self.adapter.font(node, depth)
        font = (
            font
            if font
            else wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        )
        scale = dc.GetPPI()[0] / wx.ScreenDC().GetPPI()[0]
        font.SetPointSize(int(scale * font.GetPointSize()))
        return font

    def brush_for_node(self, node, is_sequential_node=False, depth=0):
        """Create brush to use to display the given node"""
        if node == self.selected_node:
            color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        else:
            color = self.adapter.background_color(node)
            if color:
                # The adapter returns a 3-tuple
                color = wx.Colour(*[int(value) for value in color])
            else:
                red = (depth * 10) % 255
                green = 255 - ((depth * 10) % 255)
                blue = 200
                color = wx.Colour(red, green, blue)
        if is_sequential_node:
            color.Set(color.Red(), color.Green(), color.Blue(), 128)
        return wx.Brush(color)

    def pen_for_node(self, node, is_sequential_node=False, depth=0):
        """Determine the pen to use to display the given node"""
        pen = (
            self.SELECTED_PEN
            if node == self.selected_node
            else self.DEFAULT_PEN
        )
        # style = wx.DOT if is_sequential_node else wx.SOLID
        # pen.SetStyle(style)
        return pen


class DefaultAdapter(object):
    def parallel_children(self, node, recursive=False):
        children = node.parallel_children[:]
        if recursive:
            for child in node.parallel_children:
                children.extend(self.parallel_children(child, True))
        return children

    def sequential_children(self, node):
        return node.sequential_children

    def children(self, node):
        return self.parallel_children(node) + self.sequential_children(node)

    def bounds(self, node):
        times = [node.start, node.stop]
        for child in self.children(node):
            times.extend(self.bounds(child))
        return min(times), max(times)

    def start(self, node, recursive=False):
        starts = [node.start]
        if recursive:
            starts.extend(
                [self.start(child, True) for child in self.children(node)]
            )
        return float(min(starts))

    def stop(self, node, recursive=False):
        stops = [node.stop]
        if recursive:
            stops.extend(
                [self.stop(child, True) for child in self.children(node)]
            )
        return float(max(stops))

    def label(self, node):
        return node.path

    def background_color(self, node):
        return None

    def foreground_color(self, node, depth):
        return None

    def get_wx_icon(self, node):
        return None

    def now(self):
        return 0

    def nowlabel(self):
        return "Now"


class TestApp(wx.App):
    """Basic application for holding the viewing Frame"""

    def __init__(self, size):
        self.size = size
        super().__init__(0)

    def OnInit(self):
        """Initialise the application."""
        wx.InitAllImageHandlers()
        self.frame = wx.Frame(None)
        self.frame.CreateStatusBar()
        model = self.get_model(self.size)
        self.timeline = TimeLine(self.frame, model=model)
        self.frame.Show(True)
        return True

    def get_model(self, size):
        parallel_children, sequential_children = [], []
        if size > 0:
            parallel_children = [self.get_model(size - 1) for i in range(size)]
        sequential_children = [
            Node("Seq 1", 30 + 10 * size, 40 + 10 * size, [], []),
            Node("Seq 2", 80 - 10 * size, 90 - 10 * size, [], []),
        ]
        return Node(
            "Node %d" % size,
            0 + 5 * size,
            100 - 5 * size,
            parallel_children,
            sequential_children,
        )


class Node(object):
    def __init__(self, path, start, stop, subnodes, events):
        self.path = path
        self.start = start
        self.stop = stop
        self.parallel_children = subnodes
        self.sequential_children = events

    def __repr__(self):
        return "%s(%r, %r, %r, %r, %r)" % (
            self.__class__.__name__,
            self.path,
            self.start,
            self.stop,
            self.parallel_children,
            self.sequential_children,
        )


usage = "timeline.py [size]"


def main():
    """Mainloop for the application"""
    import sys

    size = 3
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(usage)
        else:
            try:
                size = int(sys.argv[1])
            except ValueError:
                print(usage)
    else:
        app = TestApp(size)
        app.MainLoop()


if __name__ == "__main__":
    main()
