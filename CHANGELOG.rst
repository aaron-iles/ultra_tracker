=====================
Project Release Notes
=====================

.. contents:: Topics

v4.1.0
======

Release Summary
---------------

Makes general UI improvements

Minor Changes
-------------

- Refreshes the UI for better readability

v4.0.0
======

Release Summary
---------------

Improves mile mark calculations, adds unit tests, formalizes Python package

Major Changes
-------------

- Refactors entire package structure to create formal Python package inside Docker container
- Refactors mile mark calculations significantly to better handle different situations

Minor Changes
-------------

- Adds unit test framework including whole race tests

v3.0.1
======

Release Summary
---------------

Enables dynamic runner names

Bugfixes
--------

- Uses the runner name in the race config for the elevation profile

v3.0.0
======

Release Summary
---------------

Adds ability to automatically create runner marker

Minor Changes
-------------

- Adds ability to automatically create runner marker (with estimate marker)
- Removes uwsgi threading for POST updates

Breaking Changes / Porting Guide
--------------------------------

- Enforces unique names for all Caltopo objects
- Renames config parameter from ``tracker_marker_name`` to ``runner_name``

v2.3.2
======

Release Summary
---------------

Fixes issues with hanging application after too many requests

Bugfixes
--------

- Removes ``max_workers`` from uwsgi configuration

v2.3.1
======

Release Summary
---------------

Fixes issue with navigation link not working on iPhone

Bugfixes
--------

- Adds ``uwsgi`` as dependency to requirements.txt
- Changes the Google Maps URL for navigation to conform to standard API allowing it to work with any platform

v2.3.0
======

Release Summary
---------------

Adds optional comments for aid stations, cleans up the UI

Minor Changes
-------------

- Adds a favicon
- Adds optional comments section for aid stations
- Minor cleanups in html

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
