from aiida.manage.configuration import load_profile
from aiida.restapi.run_api import configure_api

import os

os.environ["AIIDA_PATH"] = (
    "/home/khosra_a/development/Other_tasks/sqlite_zip_materials_cloud/.aiida"
)

load_profile("")
# load_profile('psql_dos')
# load_profile('sqlitzip-0')

api = configure_api()
application = api.app


# check this:
# http://localhost/quicksetup/api/v4
