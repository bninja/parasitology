parasitology
============

.. image:: https://travis-ci.org/bninja/parasitology.png
   :target: https://travis-ci.org/bninja/parasitology

The parasites you love all up in your network:

- http://www3.nd.edu/~parasite/

dev
---

.. code:: bash

   $ git clone https://github.com/bninja/parasitology.git
   $ cd parasitology
   $ mkvirtualenv parasitology
   (parasitology)$ pip install -r requirements.txt
   (parasitology)$ sudo $VIRTUAL_ENV/bin/python py.test

where ``sudo`` needed for:

- `scapy <http://www.secdev.org/projects/scapy/doc/usage.html#starting-scapy>`_ and
- `ip-table rules <http://www.secdev.org/projects/scapy/doc/troubleshooting.html#my-tcp-connections-are-reset-by-scapy-or-by-my-kernel>`_

hack
----

What's going on:

.. code:: bash

   $ sudo tshark  -i lo -f "tcp port 8080"

Hosts:

.. code:: bash

   (parasitology)$ ./hosts.py 8080
   ...

Parasite:

.. code:: bash

   (parasitology)$ sudo iptables -I OUTPUT 1 -p tcp --tcp-flags RST RST -s 127.0.0.1 -d 127.0.0.1 --dport 8080 -j DROP
   (parasitology)$ ./parasite.py nsat http 8080
   (a or b) and (!b or c or !d) and (d or !e)
   ...

compat
------

Appears to work on:

- Ubuntu 14.04
- ...
