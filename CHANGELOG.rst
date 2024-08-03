=====================
Project Release Notes
=====================

.. contents:: Topics

v2.2.0
======

Release Summary
---------------

Upgrades Docker container from Python 3.11 to 3.12

Minor Changes
-------------

- Upgrades Docker container from Python 3.11 to 3.12

v2.1.0
======

Release Summary
---------------

Adds course legs with UI enhancements

Minor Changes
-------------

- Adds course legs to UI and backend
- Overhauls ``Course`` object to better manage course elements
- Refactors ``AidStation`` objects to not inherit from ``CaltopoMarker``

v2.0.1
======

Release Summary
---------------

Fixes marker deletions not working

Bugfixes
--------

- Fixes issues with marker deletions after authentication test
- Removes marker description updates

v2.0.0
======

Release Summary
---------------

Overhauls credential management and some UI improvements

Minor Changes
-------------

- Updates aid station accordions for better readbility after passing

Breaking Changes / Porting Guide
--------------------------------

- Refactors credential management with Caltopo to avoid having to use session cookies

v1.0.0
======

Release Summary
---------------

Significant refactor of application

Major Changes
-------------

- Adds application threading for improved performance
- Switches from stock Flask to uwsgi

Minor Changes
-------------

- Improves mile estimates on pings
- Updates all docstrings
- Various updates to Dockerfile

v0.1.0
======

Release Summary
---------------

Minor refactors of server logs and page render

Minor Changes
-------------

- Refactors server logging and webpage rendering

v0.0.0
======

Release Summary
---------------

Initial release

Major Changes
-------------

- Initial release
