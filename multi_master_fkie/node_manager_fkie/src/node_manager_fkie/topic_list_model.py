# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Fraunhofer FKIE/US, Alexander Tiderko
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Fraunhofer nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from PySide import QtCore
from PySide import QtGui

import os
import time
import threading

import rospy
import roslib
import roslib.message
import roslib.msgs
import genpy
from master_discovery_fkie.master_info import TopicInfo
from detailed_msg_box import WarningMessageBox
from parameter_dialog import ParameterDialog, ServiceDialog


class TopicItem(QtCore.QObject, QtGui.QStandardItem):
  '''
  The topic item stored in the topic model. This class stores the topic as
  L{master_discovery_fkie.TopicInfo}. The name of the topic represented in HTML.
  '''
  
  ITEM_TYPE = QtGui.QStandardItem.UserType + 36
  COL_PUB = 1
  COL_SUB = 2
  COL_TYPE = 3


  def __init__(self, name, parent=None):
    '''
    Initialize the topic item.
    @param name: the topic name
    @type name: C{str}
    '''
    QtCore.QObject.__init__(self)
    QtGui.QStandardItem.__init__(self, self.toHTML(name))
    self.parent_item = parent
    self._topic = TopicInfo(name)
    self._first_call = True
    '''@ivar: service info as L{master_discovery_fkie.ServiceInfo}.'''
    self._publish_thread = None

#  def __del__(self):
#    print "delete TOPIC", self._topic.name

  @property
  def topic(self):
    '''
    Returns the TopicInfo instance of this topic.
    @rtype: L{master_discovery_fkie.TopicInfo}
    '''
    return self._topic

  @topic.setter
  def topic(self, topic_info):
    '''
    Sets the TopicInfo and updates the view, if needed.
    @type topic_info: L{master_discovery_fkie.TopicInfo}
    '''
    pubs_changed = False
    subs_changed = False
    type_changed = False
    if self._topic.publisherNodes != topic_info.publisherNodes:
      pubs_changed = True
      self._topic.publisherNodes = topic_info.publisherNodes
    if self._topic.subscriberNodes != topic_info.subscriberNodes:
      subs_changed = True
      self._topic.subscriberNodes = topic_info.subscriberNodes
      if not self._publish_thread is None:
        self._publish_thread._subscriber_count = len(self._topic.subscriberNodes)
    if self._topic.type != topic_info.type:
      self._topic.type = topic_info.type
      type_changed = True
    # update the tooltip and icon
#    if pubs_changed or subs_changed:
#      self._topic = topic_info.copy()
    if pubs_changed or self._first_call:
      self.updatePublisherView()
    if subs_changed or self._first_call:
      self.updateSubscriberView()
    if type_changed or self._first_call:
      self.updateTypeView()
    self._first_call = False

  def updatePublisherView(self):
    '''
    Updates the representation of the column contains the publisher state.
    '''
    if not self.parent_item is None:
      cfg_col = self.parent_item.child(self.row(), TopicItem.COL_PUB)
      if not cfg_col is None and isinstance(cfg_col, QtGui.QStandardItem):
        cfg_col.setText(str(len(self.topic.publisherNodes)))
        tooltip = ''.join(['<h4>', 'Publisher [', self.topic.name, ']:</h4><dl>'])
        for p in self.topic.publisherNodes:
          tooltip = ''.join([tooltip, '<dt>', p, '</dt>'])
        tooltip = ''.join([tooltip, '</dl>'])
        if len(self.topic.publisherNodes) > 0:
          cfg_col.setToolTip(''.join(['<div>', tooltip, '</div>']))

  def updateSubscriberView(self):
    '''
    Updates the representation of the column contains the subscriber state.
    '''
    if not self.parent_item is None:
      cfg_col = self.parent_item.child(self.row(), TopicItem.COL_SUB)
      if not cfg_col is None and isinstance(cfg_col, QtGui.QStandardItem):
        cfg_col.setText(str(len(self.topic.subscriberNodes)))
        tooltip = ''.join(['<h4>', 'Subscriber [', self.topic.name, ']:</h4><dl>'])
        for p in self.topic.subscriberNodes:
          tooltip = ''.join([tooltip, '<dt>', p, '</dt>'])
        tooltip = ''.join([tooltip, '</dl>'])
        if len(self.topic.subscriberNodes) > 0:
          cfg_col.setToolTip(''.join(['<div>', tooltip, '</div>']))

  def updateTypeView(self):
    '''
    Updates the representation of the column contains the type of the topic.
    '''
    if not self.parent_item is None:
      cfg_col = self.parent_item.child(self.row(), TopicItem.COL_TYPE)
      if not cfg_col is None and isinstance(cfg_col, QtGui.QStandardItem):
        cfg_col.setText(str(self.topic.type))
        if not self.topic.type is None and not cfg_col.toolTip():
          return
          # removed tooltip for clarity !!!
#          tooltip = ''
          try:
            mclass = roslib.message.get_message_class(self.topic.type)
#            tooltip = str(mclass)
            if not mclass is None:
#              tooltip = str(mclass.__slots__)
              for f in mclass.__slots__:
                idx = mclass.__slots__.index(f)
                idtype = mclass._slot_types[idx]
                base_type = roslib.msgs.base_msg_type(idtype)
                primitive = "unknown"
                if base_type in roslib.msgs.PRIMITIVE_TYPES:
                  primitive = "primitive"
                else:
                  try:
                    list_msg_class = roslib.message.get_message_class(base_type)
                    primitive = "class", list_msg_class.__slots__
                  except ValueError:
                    pass
#                tooltip = ''.join([tooltip, '\n\t', str(f), ': ', str(idtype), ' (', str(primitive),')'])
          except ValueError:
            pass
#          cfg_col.setToolTip(tooltip)
  
  def updateIconView(self, icon):
    if not self._publish_thread is None:
      self.setIcon(icon)
    else:
      self.setIcon(QtGui.QIcon())

  def publish(self, local_masteruri):
    try:
      if not self._publish_thread is None:
        self._publish_thread.finish()
      
      mclass = roslib.message.get_message_class(self.topic.type)
      if mclass is None:
        WarningMessageBox(QtGui.QMessageBox.Warning, "Publish error", 
                          'Error while publish to %s'%self.topic.name,
                          ''.join(['invalid message type: ', self.topic.type,'.\nIf this is a valid message type, perhaps you need to run "rosmake"'])).exec_()
        return
      slots = mclass.__slots__
      types = mclass._slot_types
      args = ServiceDialog._params_from_slots(slots, types)
      p = { '! Publish rate[Hz]' : ('int', -1) , self.topic.type : ('dict', args) }
      dia = ParameterDialog(p)
      dia.setWindowTitle(''.join(['Publish to ', self.topic.name]))
      dia.resize(450,300)

      if dia.exec_():
        params = dia.getKeywords()
        rate = params['! Publish rate[Hz]']
        self.updateIconView(QtGui.QIcon(':/icons/state_off.png'))
        self._publish_thread = PublishThread(self.topic.name, mclass, params[self.topic.type], rate, local_masteruri, len(self.topic.subscriberNodes))
        self._publish_thread.publish_msg.connect(self._on_publishing)
        self._publish_thread.wait_for_publish_msg.connect(self._on_wait_for_publishing)
        self._publish_thread.partial_publish_msg.connect(self._on_partial_publishing)
        self._publish_thread.finished.connect(self._publish_finished)
        self._publish_thread.error.connect(self.show_error_msg)
        self._publish_thread.start()
    except Exception, e:
      self._publish_thread = None
      import traceback
      print traceback.format_exc()
      raise Exception(e)
  
  def publishStop(self):
    if not self._publish_thread is None:
      self._publish_thread.finish()
  
  def _on_wait_for_publishing(self):
    self.updateIconView(QtGui.QIcon(':/icons/state_off.png'))

  def _on_partial_publishing(self):
    self.updateIconView(QtGui.QIcon(':/icons/state_part.png'))

  def _on_publishing(self):
    self.updateIconView(QtGui.QIcon(':/icons/state_run.png'))
  
  def _publish_finished(self):
    self._publish_thread = None
    self.setIcon(QtGui.QIcon())
  
  def show_error_msg(self, msg):
    WarningMessageBox(QtGui.QMessageBox.Warning, "Publish error", 
                  'Error while publish to %s'%self.topic.name,
                  str(msg)).exec_()

  @classmethod
  def toHTML(cls, topic_name):
    '''
    Creates a HTML representation of the topic name.
    @param topic_name: the topic name
    @type topic_name: C{str}
    @return: the HTML representation of the topic name
    @rtype: C{str}
    '''
    ns, sep, name = topic_name.rpartition('/')
    result = ''
    if sep:
      result = ''.join(['<div>', '<span style="color:gray;">', str(ns), sep, '</span><b>', name, '</b></div>'])
    else:
      result = name
    return result

  def type(self):
    return TopicItem.ITEM_TYPE

  @classmethod
  def getItemList(self, name, root):
    '''
    Creates the list of the items from topic. This list is used for the 
    visualization of topic data as a table row.
    @param name: the topic name
    @type name: C{str}
    @param root: The parent QStandardItem
    @type root: L{PySide.QtGui.QStandardItem}
    @return: the list for the representation as a row
    @rtype: C{[L{TopicItem} or L{PySide.QtGui.QStandardItem}, ...]}
    '''
    items = []
    item = TopicItem(name, parent=root)
    items.append(item)
    pubItem = QtGui.QStandardItem()
#    TopicItem.updatePublisherView(topic, pubItem)
    items.append(pubItem)
    subItem = QtGui.QStandardItem()
#    TopicItem.updateSubscriberView(topic, subItem)
    items.append(subItem)
    typeItem = QtGui.QStandardItem()
#    TopicItem.updateTypeView(topic, typeItem)
    items.append(typeItem)
    return items


#  def __eq__(self, item):
#    '''
#    Compares the name of topic.
#    '''
#    if isinstance(item, str) or isinstance(item, unicode):
#      return self.topic.name.lower() == item.lower()
#    elif not (item is None):
#      return self.topic.name.lower() == item.topic.name.lower()
#    return False
#
#  def __gt__(self, item):
#    '''
#    Compares the name of topic.
#    '''
#    if isinstance(item, str) or isinstance(item, unicode):
#      return self.topic.name.lower() > item.lower()
#    elif not (item is None):
#      return self.topic.name.lower() > item.topic.name.lower()
#    return False

class PublishThread(QtCore.QObject, threading.Thread):

  finished = QtCore.Signal()
  error = QtCore.Signal(str)
  publish_msg = QtCore.Signal()
  partial_publish_msg = QtCore.Signal()
  wait_for_publish_msg = QtCore.Signal()


  def __init__(self, topic_name, topic_class, args, rate, masteruri, subscriber_count):
    '''
    Create a thread to publish messages to the topic.
    @param topic_name: the name of the topic
    @type topic_name: C{str}
    @param topic_class: the class of the topic
    @type topic_class: C{Class}
    @param args: arguments to create a message
    @type args: C{str}
    @param rate: the publishing rate. -1 to publish once
    @type rate: C{int}
    @param masteruri: ROS bug workaround to unregister a publisher
    @type masteruri: C{str}

    '''
    QtCore.QObject.__init__(self)
    threading.Thread.__init__(self)
    self.setObjectName(''.join(['PablishTread - ', topic_name]))
    self._running = True
    self._topic_name = topic_name
    self._topic_class = topic_class
    self._args = args
    if type(args) != list:
      self._args = [args]
    self._rate = rate
    self._masteruri = masteruri
    self._subscriber_count = subscriber_count
    self._pub = None
    self.setDaemon(True)

  def run(self):
    self.wait_for_publish_msg.emit()
    self._pub = rospy.Publisher(self._topic_name, self._topic_class)
    max_wait_secs = 25
    secs_waited = 0
    # publish message
    while (not rospy.is_shutdown()) and self._running:
      try:
        while self._pub.get_num_connections() < self._subscriber_count and secs_waited < max_wait_secs: 
          time.sleep(1)
          secs_waited +=1
        if self._pub.get_num_connections() < self._subscriber_count:
          self.partial_publish_msg.emit()
        else:
          self.publish_msg.emit()
        msg = self._topic_class()
        #create message
        try:
          now = rospy.get_rostime() 
          import std_msgs.msg
          keys = { 'now': now, 'auto': std_msgs.msg.Header(stamp=now) }
          genpy.message.fill_message_args(msg, self._args, keys=keys)
        except (genpy.MessageException, ValueError), e:
          import traceback
          print traceback.format_exc()
          self.error.emit(''.join([str(e), "\n\nArgs are: [", str(genpy.message.get_printable_message_args(msg)), ']']))
          self._internal_finish()
          return
        self._pub.publish(msg)
        if self._rate > 0:
          r = rospy.Rate(float(self._rate))
          r.sleep()
        else:
          break
      except rospy.ROSSerializationException as e:
        import rosmsg
        # we could just print the message definition, but rosmsg is more readable
        self.error.emit(''.join(["Unable to publish message. One of the fields has an incorrect type:\n",
                                "  ", str(e), "\n\nmsg file:\n", str(rosmsg.get_msg_text(msg_class._type))]))
        self._internal_finish()
        return
    self._internal_finish()

  def finish(self):
    self._running = False

  def _internal_finish(self):
    time.sleep(2)
    if not self._pub is None:
      self._pub.unregister()
      # the unregister method is buggy @see https://code.ros.org/trac/ros/ticket/3900
      # workaround: (does not work :( )
#      import socket
#      try:
#        import xmlrpclib
#        socket.setdefaulttimeout(3)
#        master = xmlrpclib.ServerProxy(self._masteruri)
#        master.unregisterPublisher(rospy.get_name(), self._topic_name, rospy.get_node_uri())
#      except Exception, e:
#        print e
#      finally:
#        socket.setdefaulttimeout(None)
      
#    if not self._pub is None:
#      del self._pub
    self.finished.emit()


class TopicModel(QtGui.QStandardItemModel):
  '''
  The model to manage the list with topics in ROS network.
  '''
  header = [('Name', 300),
            ('Publisher', 50), 
            ('Subscriber', 50),
            ('Type', -1)]
  '''@ivar: the list with columns C{[(name, width), ...]}'''
  
  def __init__(self):
    '''
    Creates a new list model.
    '''
    QtGui.QStandardItemModel.__init__(self)
    self.setColumnCount(len(TopicModel.header))
    self.setHorizontalHeaderLabels([label for label, width in TopicModel.header])

  def flags(self, index):
    '''
    @param index: parent of the list
    @type index: L{PySide.QtCore.QModelIndex}
    @return: Flag or the requested item
    @rtype: L{PySide.QtCore.Qt.ItemFlag}
    @see: U{http://www.pyside.org/docs/pyside-1.0.1/PySide/QtCore/Qt.html}
    '''
    if not index.isValid():
      return QtCore.Qt.NoItemFlags
    return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

  def updateModelData(self, topics):
    '''
    Updates the topics model. New topic will be inserted in sorting order. Not 
    available topics removed from the model.
    @param topics: The dictionary with topics 
    @type topics: C{dict(topic name : L{master_discovery_fkie.TopicInfo}, ...)}
    '''
    topic_names = topics.keys()
    root = self.invisibleRootItem()
    updated = []
    #remove or update the existing items
    for i in reversed(range(root.rowCount())):
      topicItem = root.child(i)
      if not topicItem.topic.name in topic_names:
        root.removeRow(i)
      else:
        topicItem.topic = topics[topicItem.topic.name]
        updated.append(topicItem.topic.name)
    # insert other items in sorted order
#    cputimes = os.times()
#    cputime_init = cputimes[0] + cputimes[1]
    for (name, topic) in topics.items():
      doAddItem = True
      for i in range(root.rowCount()):
        topicItem = root.child(i)
        if not name in updated:
          res = cmp(topicItem.topic.name.lower(), topic.name.lower())
          if res > 0:
            new_item_row = TopicItem.getItemList(topic.name, root)
            root.insertRow(i, new_item_row)
            new_item_row[0].topic = topic
            doAddItem = False
            break
        else:
          doAddItem = False
          break
      if doAddItem:
        new_item_row = TopicItem.getItemList(topic.name, root)
        root.appendRow(new_item_row)
        new_item_row[0].topic = topic
#    cputimes = os.times()
#    cputime = cputimes[0] + cputimes[1] - cputime_init
#    print "      update topic ", cputime, ", topic count:", len(topics)

  def publish_topic(self, topic_name, local_masteruri):
    item = self._get_topic(topic_name)
    if not topic_name is None:
      item.publish(local_masteruri)

  def publish_stop_topic(self, topic_name):
    item = self._get_topic(topic_name)
    if not topic_name is None:
      item.publishStop()

  def _get_topic(self, topic_name):
    root = self.invisibleRootItem()
    for i in range(root.rowCount()):
      topicItem = root.child(i)
      if cmp(topicItem.topic.name.lower(), topic_name.lower()) == 0:
        return topicItem
    return None
