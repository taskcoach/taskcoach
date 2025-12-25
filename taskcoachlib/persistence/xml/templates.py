# -*- coding: UTF-8 -*-

from taskcoachlib.i18n import _

def getDefaultTemplates():
    templates = []
    templates.append(('dueToday', b'<?xml version="1.0" ?><?taskcoach release="1.1.0" tskversion="30"?><tasks><task duedatetmpl="Now().endOfDay()" startdatetmpl="Now()" status="2" subject="New task due today"/></tasks>\n'))
    _(b'New task due today')
    templates.append(('dueTomorrow', b'<?xml version="1.0" ?><?taskcoach release="1.1.0" tskversion="30"?><tasks><task duedatetmpl="Now().endOfDay() + oneDay" startdatetmpl="Now()" status="2" subject="New task due tomorrow"/></tasks>\n'))
    _(b'New task due tomorrow')

    return templates
