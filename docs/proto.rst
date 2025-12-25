
Ports and Bonjour discovery
===========================

On the desktop, Task Coach listens to a port between 4096 and 8192, whichever one is the first available. The actual host/port pair is made available through Bonjour (Apple's name for mDNS); the id is registered (http://www.dns-sd.org/ServiceTypes.html) as _taskcoachsync._tcp. Once the user has browsed available services and choosen the instance of Task Coach he wants to sync with, the device initiates a TCP connection (setting TCP_NODELAY on the socket is not mandatory but strongly advised since the protocol consists of many small payload exchanges).

Basic data types
================

Data types are serialized over the TCP connection; the basic types are:

Integers
--------

All integers sent through the socket are sent as 4-bytes, network byte order integers (generally unsigned); for instance a 10 will be sent as 0x00 0x00 0x00 0x0a.

Strings
-------

Strings are sent encoded in UTF-8, in two parts; first the string's length (encoded) as an integer, then the string bytes. Soo the string "foo" will be sent as 0x00 0x00 0x00 0x03 0x66 0x6f 0x6f. The length may be 0 for an empty string.

Protocol negotiation
====================

Once the connection is established, the desktop and the device must negotiate the version of the protocol that will be used for the sync. Current version is 5 and previous ones are obsolete. In general, the desktop may support several versions to accomodate older applications on the device; but the device generally only supports the latest version it knows (this is the case for the iPhone app).

The device sends the latest version it supports (as an integer). Upon receiving this, if the desktop supports this version, it sends a non-zero integer and the authentication starts. If it does not support this version, it sends a zero. The device may cancel the sync here (and display a message warning the user that the desktop version of Task Coach is too old) or try again with a lesser protocol version, until the desktop sends a non-zero integer, or the version number drops to 0 (obviously shouldn't happen).

Authentication and basic setup
==============================

Authentication is a SHA1-based challenge/response. The desktop sends 512 random bytes. The device must then send the SHA1 hash of the concatenation of those bytes and the UTF-8 encoded password. The desktop answers either 1 (succeeded), or 0 (failed) followed by a new random buffer in case the device wants to try again.

As soon as authentication succeeds, the device must send its name as a string. This should be a human-readable string (for instance "Jerome Laheurte's iPhone). Then, the desktop will send various basic informations. For each of them, the device must answer with a non-zero integer. These informations are:

   1. The task file's GUID, as a string. This is a unique identifier that may be used to differentiate between several task files.
   2. The task file name, as a string.
   3. The day start and end hours, as integers.

Then the synchronization may actually start.

Advanced data types
===================

In addition to strings and integers, more complex data types are used during the actual synchronization; those are N-strings, lists, dates and structures.

   N-strings
      are just like strings except that a length of 0 means not an empty string but a NULL value. They are serialized just like strings.

   Lists
      are like vectors; a sequence of same-typed objects. They are serialized thus: first the list length (not in bytes, but in number of objects), then the concatenation of the objects serializations. They may be empty, in which case the length is 0 and there is payload.

   Date
      are, well, dates. They may be NULL. They are serialized as N-strings with the YYYY-MM-DD format.

   Date and time
      Same as dates with the time information (HH:MM:SS). They may be NULL. They are serialized as N-strings with the YYYY-MM-DD HH:MM:SS format.

   Structs
      Structs are like C structs or Python tuples: ordered sequences of items that may have different types. They are serialized as the concatenation of their members.

Examples
--------

   Null N-string
     Zero length: 0x00 0x00 0x00 0x00

   2010/11/20 date
      +---------------------+------+------+------+------+---------+------+------+-------+------+------+
      | Length              | 2    | 0    | 1    | 0    | minus   | 1    | 1    | minus | 2    | 0    |
      +---------------------+------+------+------+------+---------+------+------+-------+------+------+
      | 0x00 0x00 0x00 0x0a | 0x32 | 0x30 | 0x31 | 0x30 | 0x2d    | 0x31 | 0x31 | 0x2d  | 0x32 | 0x30 |
      +---------------------+------+------+------+------+---------+------+------+-------+------+------+

   2010/11/20 12:02:35 date and time
      +---------------------+------+------+------+------+---------+------+------+-------+------+------+-------+------+------+------+------+------+------+------+------+
      | Length              | 2    | 0    | 1    | 0    | minus   | 1    | 1    | minus | 2    | 0    | space | 1    | 2    | :    | 0    | 2    | :    | 3    | 5    |
      +---------------------+------+------+------+------+---------+------+------+-------+------+------+-------+------+------+------+------+------+------+------+------+
      | 0x00 0x00 0x00 0x0a | 0x32 | 0x30 | 0x31 | 0x30 | 0x2d    | 0x31 | 0x31 | 0x2d  | 0x32 | 0x30 |       | 0x31 | 0x32 | 0x3a | 0x30 | 0x32 | 0x3a | 0x33 | 0x35 |
      +---------------------+------+------+------+------+---------+------+------+-------+------+------+-------+------+------+------+------+------+------+------+------+

   Struct with an integer and two strings, for values 42, 'foo' and 'spam'
      +---------------------+------------------------------------+-----------------------------------------+
      | 42                  | foo                                | spam                                    |
      +---------------------+------------------------------------+-----------------------------------------+
      | 0x00 0x00 0x00 0x2a | 0x00 0x00 0x00 0x03 0x66 0x6f 0x6f | 0x00 0x00 0x00 0x04 0x73 0x70 0x61 0x6d |
      +---------------------+------------------------------------+-----------------------------------------+

   List of 2 structs (42, 'foo', 'spam') (13, 'eggs', 'bacon')
      +---------------------+---------------------+------------------------------------+-----------------------------------------+---------------------+-----------------------------------------+----------------------------------------------+
      | List length         | 42                  | foo                                | spam                                    | 13                  | eggs                                    | bacon                                        |
      +---------------------+---------------------+------------------------------------+-----------------------------------------+---------------------+-----------------------------------------+----------------------------------------------+
      | 0x00 0x00 0x00 0x02 | 0x00 0x00 0x00 0x2a | 0x00 0x00 0x00 0x03 0x66 0x6f 0x6f | 0x00 0x00 0x00 0x04 0x73 0x70 0x61 0x6d | 0x00 0x00 0x00 0x0d | 0x00 0x00 0x00 0x04 0x65 0x67 0x67 0x73 | 0x00 0x00 0x00 0x05 0x62 0x61 0x63 0x6f 0x6e |
      +---------------------+---------------------+------------------------------------+-----------------------------------------+---------------------+-----------------------------------------+----------------------------------------------+  
 
Synchronization start
=====================

Each Task Coach object has a unique ID which is an arbitrary string. Furthermore, each object also probably has a unique ID on the device (for instance a database primary key). Objects created on the device don't have a Task Coach ID at first; they are assigned one during the synchronization. When such an object is uploaded to the desktop, a Task Coach ID is created and sent back to the device, which must store it. It will be used later to identify a modified or deleted object. This has two consequences:

   1. For created objects on the device, parent objects must be sent first to that they have a Task Coach ID when their children are created on the desktop side.

   2. Objects that are deleted on the device but don't have a Task Coach ID (never been synchronized) may be completely discarded, they don't need to be synchronized.

Device to desktop
-----------------

In this first phase, the device will send all its local modifications to the desktop.

Object counts
~~~~~~~~~~~~~

The device must send the following integers in that order:

   * Number of new categories
   * Number of new tasks
   * Number of deleted tasks
   * Number of modified tasks
   * Number of deleted categories
   * Number of modified categories
   * Number of new efforts
   * Number of modified efforts
   * Number of deleted efforts

Here "modified", "new" and "deleted" are from the device's point of view.

The following states happen in the order described.

New categories
~~~~~~~~~~~~~~

Each new category is sent as a struct (Category name: string, Category parent ID: N-string). For each of them, the desktop answers with the Task Coach unique ID for this newly created category.

Deleted categories
~~~~~~~~~~~~~~~~~~

The device must send the Task Coach ID of each deleted category; they may then be discarded from the database. The desktop answers with a string that may be safely ignored (actually the ID itself).

Modified categories
~~~~~~~~~~~~~~~~~~~

The device sends each modified category as a struct (Category name: string, category Task Coach ID: string). The desktop answers with a string that may be safely discarded.

New tasks
~~~~~~~~~

The device sends each new task as a struct with the following members, in that order:

   * Subject: string
   * Description: string
   * Start date: date and time
   * Due date: date and time
   * Completion date: date and time
   * Reminder date: date and time
   * Priority: integer
   * Recurrence: integer. Actually a boolean; 0 means the task has no recurrence set and 1 means it has.
   * Recurrence period: integer; number of periods for the recurrence
   * Recurrence repeat: integer; max number of times the recurrence may occur
   * Same week day: integer; 1 if the recurrence must happen on the same weekday, 0 otherwise.
   * Parent ID: N-string; the Task Coach ID of the task's parent, or NULL if it's toplevel.
   * Categories: List of strings (may be empty). This is the list of the Task Coach IDs of the category the task belongs to.

The desktop answers with the Task Coach ID for the newly created task.

Deleted tasks
~~~~~~~~~~~~~

The device sends the Task Coach ID of each deleted task. The desktop answers with a string that may be safely discarded.

Modified tasks
~~~~~~~~~~~~~~

The device sends each modified task as a struct with the following members, in that order:

   * Subject: string
   * ID: string; the Task Coach ID of the task
   * Description: string
   * Start date: date and time
   * Due date: date and time
   * Completion date: date and time
   * Reminder date: date and time
   * Priority: integer
   * Recurrence: integer. Actually a boolean; 0 means the task has no recurrence set and 1 means it has.
   * Recurrence period: integer; number of periods for the recurrence
   * Recurrence repeat: integer; max number of times the recurrence may occur
   * Same week day: integer; 1 if the recurrence must happen on the same weekday, 0 otherwise.
   * Categories: List of strings (may be empty). This is the list of the Task Coach IDs of the category the task belongs to.

The desktop answers with a string that may be safely discarded.

Note that this structure is not the same as the one used for new tasks; new tasks don't have a Task Coach ID yet but modified tasks do. Also, the parent ID is omitted here because one can't (yet) reparent a task in the iPhone app.

New efforts
~~~~~~~~~~~

The device sends each new effort as a struct with the following members, in that order:

   * Subject: string
   * Task coach ID of the task the effort is related to: N-string
   * Effort start date: date and time
   * Effort end date: date and time, may be NULL.

The desktop answers with the Task Coach ID for the newly created effort.

Modified efforts
~~~~~~~~~~~~~~~~

The device sends each modified effort as a struct with the following members, in that order:

   * Task Coach ID of the effort: string
   * Subject: string
   * Start date: date and time
   * End date: date and time, may be NULL.

The desktop answers with a string that may be safely discarded.

Desktop to device
-----------------

After local modifications on the device have been uploaded to the desktop, the desktop will send the whole database to the device (no notion of modified/new/deleted here), so here the device should first completely empty its database and rebuild it with what will be send in this state.

Object counts
~~~~~~~~~~~~~

The desktop sends the following integers in that order:

   * Number of categories
   * Number of tasks
   * Number of efforts

Categories
~~~~~~~~~~

The desktop sends each category as a struct with the following members, in that order:

   * Subject: string
   * Task Coach ID: string
   * Parent Task Coach ID: N-string

The device must answer to each with a non-zero integer.

Tasks
~~~~~

The desktop sends each task as a struct with the following members, in that order:

   * Subject: string
   * Task Coach ID: string
   * Description: string
   * Start date: date and time
   * Due date: date and time
   * Completion date: date and time
   * Reminder: date and time
   * Parent Task Coach ID: N-string
   * Priority: integer
   * Recurrence: integer; 1 if the task has a recurrence setting, 0 otherwise
   * Recurrence period: integer
   * Recurrence repeat: integer
   * Recurrence same weekday: integer
   * Categories: List of Task Coach IDs of the categories this task belongs to

The device must answer to each with a non-zero integer.

Efforts
~~~~~~~

The desktop sends each effort as a struct with the following members, in that order:

   * Task Coach ID: string
   * Subject: string
   * Task Task Coach ID: N-string
   * Start date: date and time
   * End date: date and time

The device must answer to each with a non-zero integer.

The connexion is then closed, the synchronization is over.
