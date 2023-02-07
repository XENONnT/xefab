from xefab.collection import XefabCollection

from . import install, secrets, admin, utils
namespace = XefabCollection.from_module(utils , 'utils')

install = XefabCollection.from_module(install, name='install')
namespace.add_collection(install)

secret = XefabCollection.from_module(secrets, name='secrets')
namespace.add_collection(secret)

admin = XefabCollection.from_module(admin, name='admin')
namespace.add_collection(admin)