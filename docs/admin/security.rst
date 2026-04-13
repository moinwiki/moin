
Security Guide
==============

This guide lists the **essential steps** to securely deploy a public Moin2 wiki instance.
It helps wiki admins and server admins review the security of their Moin2 installation.

Ensure these settings are in place before exposing your wiki to the internet.


Use Encrypted Transport (HTTPS)
-------------------------------

- Serve the wiki **only via HTTPS**
- Redirect all HTTP traffic to HTTPS
- Use a valid TLS certificate

See: :ref:`transmission-security`


Configure Secure Authentication
-------------------------------

- Ensure authentication is only used over HTTPS
- Avoid insecure authentication mechanisms

See: :ref:`authentication`


Enable Authorization (ACLs)
---------------------------

- Configure Access Control Lists (ACLs)
- Use a **deny-by-default** strategy
- Restrict editing to authenticated users where possible

Typical baseline:

- Anonymous users: read-only
- Authenticated users: limited write access
- Admin group: full access

See: :ref:`authorization`


Use Groups for Permissions
--------------------------

- Define groups for admins and editors
- Assign permissions to groups instead of individual users

See: :ref:`groups`


Configure Cryptographic Secrets
-------------------------------

- Set a strong, random ``SECRET_KEY``
- Do not reuse secrets across environments
- Keep secrets out of version control

See: :ref:`framework-configuration`


Enforce Strong Password Policies
--------------------------------

- Enable password strength checking
- Require sufficient length and complexity

See: :ref:`password-strength`


Use Secure Password Storage
---------------------------

- Ensure password hashing is properly configured
- MoinMoin uses modern hashing (Argon2id) by default

See: :ref:`password-storage`


Configure Content Security Policy (CSP)
---------------------------------------

- Enable CSP headers
- Start with report-only mode, then enforce

See: :ref:`configure-csp`


Use a Production-Ready Web Server
---------------------------------

- Do **not** use the built-in development server
- Deploy using a WSGI server (e.g. gunicorn, uWSGI)
- Place behind a reverse proxy (e.g. nginx, Apache)
- Disable debug mode

See: :ref:`requirements-servers`


Keep the System Updated
-----------------------

- Regularly update MoinMoin and dependencies
- Apply security fixes promptly

See: :doc:`/admin/install`


Verify Software Integrity
-------------------------

- Verify downloads using GPG signatures when available

See: :ref:`signed-releases`


Perform Regular Backups
-----------------------

- Backup data before upgrades or major configuration changes

See: :doc:`/admin/backup`


Enable Logging and Monitoring
-----------------------------

- Configure logging
- Monitor authentication attempts and errors

See: :ref:`logging-configuration`


Handle Migration Securely
-------------------------

- Remove unsupported password hashes
- Force password resets if needed

See: :doc:`/admin/upgrade`


Validate Host Headers (TRUSTED_HOSTS)
-------------------------------------

- Configure ``TRUSTED_HOSTS`` in ``wikiconfig.py``
- Allow only known domain names
- Enforce validation at proxy or WSGI level

See: :ref:`framework-configuration`

Further Considerations
----------------------

- Fine-tune CSP policies
- Use a reverse proxy (nginx or Apache) with HTTPS
- Apply rate limiting and firewall rules where appropriate
- Monitor logs regularly and review user permissions
- Test backups and recovery procedures
- Keep the operating system and dependencies updated
- Use a dedicated user account for running the wiki
- Run the wiki with the least privileges required
- Ensure configuration files are not writable by the web server user
