|travis-badge|_

.. |travis-badge| image:: https://travis-ci.com/IBM/pycloudmessenger.svg?branch=master
.. _travis-badge: https://travis-ci.com/IBM/pycloudmessenger/

========================
## pycloudmessenger
========================

The purpose of this project is to provide sample code for interacting with various messaging based cloud platforms provided by IBM Research Ireland.


Prerequisites
---------------------------------

It is assumed that all development takes place in Python, using at least version 3.6.


Examples and Testing
---------------------------------

Unit tests are contained in the tests directory and example code for basic messaging as well as ffl and castor are contained in the examples directory.

To run the unit tests, a local RabbitMQ container is launched automatically. Settings and credentials to match the latest RabbitMQ docker image are also provided. To run the test:

.. code-block::

	creds=local.json make test 


References 
---------------------------------

* [IBM Research Blog](https://www.ibm.com/blogs/research/2018/11/forecasts-iot/)
* [Castor: Contextual IoT Time Series Data and Model Management at Scale](https://arxiv.org/abs/1811.08566) Bei Chen, Bradley Eck, Francesco Fusco, Robert Gormally, Mark Purcell, Mathieu Sinn, Seshu Tirupathi. 2018 IEEE International Conference on Data Mining (ICDM workshops).
