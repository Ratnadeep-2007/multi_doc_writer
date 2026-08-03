import os
import sys

# 1. Add application directory to the system path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# 2. Activate virtualenv (if your cPanel setup doesn't do it automatically)
# In cPanel, virtualenvs are usually placed under:
# /home/<cpanel_username>/virtualenv/<app_root>/<python_version>/lib/python<version>/site-packages
# If dependencies fail to load, you can uncomment and customize the line below:
# sys.path.insert(0, '/home/YOUR_CPANEL_USERNAME/virtualenv/autodocumentation.sspowertech.com/YOUR_PYTHON_VERSION/lib/pythonYOUR_VERSION/site-packages')

# 3. Import the Flask application object and catch errors for diagnostic log
try:
    from app import app as flask_app
except Exception as e:
    # Write traceback to a local log file inside your app folder for easy debugging
    with open(os.path.join(APP_DIR, 'passenger_error.log'), 'w') as f:
        import traceback
        traceback.print_exc(file=f)
    raise e

# 4. Middleware to handle subdirectory prefix routing (e.g. yourdomain.com/app)
# If your application is served from the root of a domain or subdomain, keep SUBDIRECTORY_PREFIX as ''
SUBDIRECTORY_PREFIX = ''  # e.g., '/my-sub-folder'

class PrefixMiddleware:
    def __init__(self, wsgi_app, prefix=''):
        self.wsgi_app = wsgi_app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith(self.prefix):
            environ['PATH_INFO'] = path_info[len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
        return self.wsgi_app(environ, start_response)

if SUBDIRECTORY_PREFIX:
    application = PrefixMiddleware(flask_app, prefix=SUBDIRECTORY_PREFIX)
else:
    application = flask_app

