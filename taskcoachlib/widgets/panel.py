import wx

class PanelWithBoxSizer(wx.Panel):
    def __init__(self, *args, **kwargs):
        orientation = kwargs.pop('orientation', wx.VERTICAL)
        super(PanelWithBoxSizer, self).__init__(*args, **kwargs)
        self.__panelSizer = wx.BoxSizer(orientation)
        
    def fit(self):
        ''' Call this method after all controls have been added (via Add()). '''
        self.SetSizerAndFit(self.__panelSizer)
        
    def add(self, *args, **kwargs):
        defaultKwArgs = dict(flag=wx.EXPAND|wx.ALL, proportion=1)
        defaultKwArgs.update(kwargs)
        self.__panelSizer.Add(*args, **defaultKwArgs)
        
        
class BoxWithFlexGridSizer(wx.Panel):
    ''' A panel that is boxed and has a FlexGridSizer inside it. '''
    def __init__(self, parent, label, cols, gap=10, vgap=0, hgap=0, 
            growableRow=-1, growableCol=-1, *args, **kwargs):
        super(BoxWithFlexGridSizer, self).__init__(parent, *args, **kwargs)
        box = wx.StaticBox(self, label=label)
        self.__boxSizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        self.__entriesSizer = wx.FlexGridSizer(cols=cols, vgap=gap or vgap, 
            hgap=gap or hgap)
        if growableRow > -1:
            self.__entriesSizer.AddGrowableRow(growableRow, proportion=1)
        if growableCol > -1:
            self.__entriesSizer.AddGrowableCol(growableCol, proportion=1)
        self.__boxSizer.Add(self.__entriesSizer, proportion=1, 
            flag=wx.EXPAND|wx.ALL, border=10)
        
    def fit(self):
        ''' Call this method after all controls have been added (via add()). '''
        self.SetSizerAndFit(self.__boxSizer)
        
    def add(self, control, *args, **kwargs):
        ''' Add controls to the FlexGridSizer. '''
        if type(control) in (type(''), type(u'')):
            control = wx.StaticText(self, label=control)
            if 'flag' not in kwargs:
                kwargs['flag'] = wx.ALIGN_RIGHT
        self.__entriesSizer.Add(control, *args, **kwargs)
        
