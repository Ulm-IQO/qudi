State machine per module with Fysom              {#modulestate}
============

States:
* deactivated
* idle
* running
* locked
* blocked

State transition functions, do not use in anything derived from Base:

* activate:   
  - deactivated -> idle
* deactivate:
  - idle -> deactivated
  - running -> deactivated
* run:
  - idle -> running
* stop:
  - running -> idle
* lock:
  - idle -> locked
  - running -> locked
* block:
  - idle -> blocked
  - running -> blocked
* locktoblock:
  - locked -> blocked
* unlock:
  - locked -> idle
* unblock:
  - blocked -> idle
* runlock:
  - locked -> running
* runblock:
  - blocked -> running

Old Stuff:
~~~~~~~~~~~~~
-1 - failed: error in the state determination
0 - idle: the object is ready for your commands
1 - running: objects is working, but can be interrupted any time
2 - locked: you can read, but not send commands or write
3 - blocked: object is busy and can not answer (come back later)
4 or higher: specific states of any class
~~~~~~~~~~~~~
