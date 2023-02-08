from xefab.collection import XefabCollection

from . import admin, base, github, install, secrets

namespace = XefabCollection.from_module(base, "root")

install = XefabCollection.from_module(install, name="install")
namespace.add_collection(install)

secret = XefabCollection.from_module(secrets, name="secrets")
namespace.add_collection(secret)

admin = XefabCollection.from_module(admin, name="admin")
namespace.add_collection(admin)

github = XefabCollection.from_module(github, name="github")
namespace.add_collection(github)
